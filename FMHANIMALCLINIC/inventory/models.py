"""
Models for the inventory application.
"""
import uuid

from django.db import models
from django.conf import settings
from django.utils import timezone
from branches.models import Branch
from utils.models import SoftDeleteModel


class Product(SoftDeleteModel):
    """Represents a product or medication in the clinic's inventory."""

    ITEM_TYPE_CHOICES = [
        ('Product', 'Product'),
        ('Medication', 'Medication'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    item_type = models.CharField(
        max_length=20, choices=ITEM_TYPE_CHOICES, default='Product')

    # Identification
    sku = models.CharField(
        max_length=100, blank=True,
        help_text="Stock Keeping Unit (auto-generated if blank)")
    barcode = models.CharField(
        max_length=100, blank=True,
        help_text="Barcode / UPC number")
    manufacturer = models.CharField(max_length=200, blank=True)

    # Financial fields
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name='products')
    is_available = models.BooleanField(default=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    min_stock_level = models.PositiveIntegerField(default=5)

    # Safety
    expiration_date = models.DateField(
        null=True, blank=True,
        help_text="For medications or perishable items")

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for the Product model."""
        ordering = ['-created_at']

    def __str__(self):
        return str(self.name)

    @property
    def status(self):
        """Returns the current stock status."""
        if self.stock_quantity <= 0:
            return 'Out of Stock'
        if self.stock_quantity <= self.min_stock_level:
            return 'Low Stock'
        return 'In Stock'

    @property
    def inventory_value(self):
        """Total valuation of this item in stock based on cost."""
        return self.stock_quantity * self.unit_cost

    @property
    def profit_margin(self):
        """Profit margin percentage per unit."""
        if self.price and self.price > 0:
            return round(
                ((self.price - self.unit_cost) / self.price) * 100, 1
            )
        return 0

    def save(self, *args, **kwargs):
        """Override save to auto-generate SKU and verify availability."""
        if self.stock_quantity == 0:
            self.is_available = False
        else:
            self.is_available = True

        # Auto-generate SKU if blank
        if not self.sku:

            prefix = 'MED' if self.item_type == 'Medication' else 'PRD'
            self.sku = f"{prefix}-{str(uuid.uuid4())[:6].upper()}"

        super().save(*args, **kwargs)


class StockAdjustment(models.Model):
    """Tracks history of stock changes (purchases, returns, damages)."""

    ADJUSTMENT_TYPES = [
        ('Purchase', 'Add Stock (New Purchase / Delivery)'),
        ('Return', 'Add Stock (Customer Return)'),
        ('Transfer In', 'Add Stock (Received from another branch)'),
        ('Damage', 'Remove Stock (Damaged / Broken)'),
        ('Expiration', 'Remove Stock (Expired)'),
        ('Sale', 'Remove Stock (Sold offline / manual)'),
        ('Reservation', 'Remove Stock (Reserved)'),
        ('Transfer Out', 'Remove Stock (Sent to another branch)'),
        ('Correction', 'Inventory Update (Manual Count Correction)'),
    ]

    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name='stock_adjustments')
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='stock_adjustments')

    adjustment_type = models.CharField(
        max_length=20, choices=ADJUSTMENT_TYPES, default='Purchase')
    reference = models.CharField(
        max_length=50, help_text="e.g., Receipt #, Invoice ID, or N/A")
    date = models.DateField()

    quantity = models.IntegerField(
        help_text="Enter the number of items. Removals are calculated automatically.")
    cost_per_unit = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)

    reason = models.CharField(
        max_length=255, blank=True, null=True, help_text="e.g., Damaged, Expired, Returned")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta options for StockAdjustment."""
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.reference} - {self.product.name} ({self.adjustment_type})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            # Re-fetch product to avoid race conditions
            # pylint: disable=no-member
            product = Product.objects.get(pk=self.product.pk)

            # Enforce negative sign for deduction types
            if self.adjustment_type in [
                'Damage', 'Expiration', 'Sale', 'Reservation', 'Transfer Out'
            ]:
                if self.quantity > 0:
                    self.quantity = -self.quantity
                    super().save(update_fields=['quantity'])

            product.stock_quantity += self.quantity

            # Ensure stock doesn't go below 0
            if product.stock_quantity < 0:
                product.stock_quantity = 0

            product.save()


class Reservation(models.Model):
    """A product reservation made by a user from the digital catalog."""

    class Status(models.TextChoices):
        """Status choices for a Reservation."""
        PENDING = 'Pending', 'Pending'
        CONFIRMED = 'Confirmed', 'Confirmed'
        CANCELLED = 'Cancelled', 'Cancelled'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservations',
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='reservations')
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for Reservation."""
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"Reservation #{self.pk} — {self.product.name} "
            f"x{self.quantity} ({self.status})"
        )


class StockTransfer(models.Model):
    """Tracks inventory transfers between branches."""

    class Status(models.TextChoices):
        """Status choices for a StockTransfer."""
        PENDING = 'Pending', 'Pending'
        APPROVED = 'Approved', 'Approved'
        REJECTED = 'Rejected', 'Rejected'
        COMPLETED = 'Completed', 'Completed'

    source_product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='outgoing_transfers')
    destination_branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name='incoming_transfers')

    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING)

    notes = models.TextField(
        blank=True, help_text="Reason for transfer or special instructions")

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='requested_transfers'
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='processed_transfers'
    )

    class Meta:
        """Meta options for StockTransfer."""
        ordering = ['-created_at']

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"Transfer {self.quantity}x {self.source_product.name} "
            f"to {self.destination_branch.name}"
        )

    def complete_transfer(self, user):
        """Executes the transfer of stock if status changes to COMPLETED."""
        if self.status not in (self.Status.PENDING, self.Status.APPROVED):
            raise ValueError(
                "Transfer must be pending or approved to complete.")

        # Deduct from source branch
        # pylint: disable=no-member
        if self.source_product.stock_quantity < self.quantity:
            raise ValueError("Insufficient stock in source branch.")

        self.source_product.stock_quantity -= self.quantity
        self.source_product.save()

        # Add a stock adjustment for source
        StockAdjustment.objects.create(
            branch=self.source_product.branch,
            product=self.source_product,
            adjustment_type='Transfer Out',
            reference=f"TRF-OUT-{self.pk}",
            date=timezone.now().date(),
            quantity=self.quantity * -1,
            reason=f"Transfer to {self.destination_branch.name}",
            cost_per_unit=self.source_product.unit_cost
        )

        # Add to destination branch
        dest_product, _created = Product.objects.get_or_create(
            sku=self.source_product.sku,
            branch=self.destination_branch,
            defaults={
                'name': self.source_product.name,
                'description': self.source_product.description,
                'item_type': self.source_product.item_type,
                'barcode': self.source_product.barcode,
                'manufacturer': self.source_product.manufacturer,
                'unit_cost': self.source_product.unit_cost,
                'price': self.source_product.price,
                'min_stock_level': self.source_product.min_stock_level,
                'expiration_date': self.source_product.expiration_date,
            }
        )

        dest_product.stock_quantity += self.quantity
        dest_product.save()

        # Add a stock adjustment for destination
        StockAdjustment.objects.create(
            branch=self.destination_branch,
            product=dest_product,
            adjustment_type='Transfer In',
            reference=f"TRF-IN-{self.pk}",
            date=timezone.now().date(),
            quantity=self.quantity,
            reason=f"Transfer from {self.source_product.branch.name}",
            cost_per_unit=dest_product.unit_cost
        )

        self.status = self.Status.COMPLETED
        self.processed_by = user
        self.save()
