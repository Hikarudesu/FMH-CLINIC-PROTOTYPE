"""
Models for the inventory application.
"""
import uuid

from django.db import models
from django.conf import settings
from branches.models import Branch


class Product(models.Model):
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
        ('Purchase', 'Purchase'),
        ('Return', 'Return'),
        ('Damage', 'Damaged Stock'),
        ('Expiration', 'Expired'),
        ('Correction', 'Inventory Correction'),
        ('Sale', 'Sale'),
        ('Reservation', 'Reservation'),
    ]

    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name='stock_adjustments')
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='stock_adjustments')

    adjustment_type = models.CharField(
        max_length=20, choices=ADJUSTMENT_TYPES, default='Purchase')
    reference = models.CharField(max_length=50, help_text="e.g., PO123")
    date = models.DateField()

    quantity = models.IntegerField(
        help_text="Positive for additions, negative for subtractions")
    cost_per_unit = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)

    reason = models.CharField(
        max_length=255, blank=True, null=True, help_text="e.g., Damaged stock")

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
                'Damage', 'Expiration', 'Sale', 'Reservation'
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
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"Reservation #{self.pk} — {self.product.name} "
            f"x{self.quantity} ({self.status})"
        )
