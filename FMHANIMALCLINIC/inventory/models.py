"""
Models for the inventory application.
"""
from django.db import models
from branches.models import Branch


class Product(models.Model):
    """Represents a product in the clinic's inventory."""

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Financial fields
    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name='products')
    is_available = models.BooleanField(default=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    min_stock_level = models.PositiveIntegerField(default=5)

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

    def save(self, *args, **kwargs):
        if self.stock_quantity == 0:
            self.is_available = False
        else:
            self.is_available = True
        super().save(*args, **kwargs)


class StockAdjustment(models.Model):
    """Tracks history of stock changes (purchases, returns, damages)."""

    ADJUSTMENT_TYPES = [
        ('Purchase', 'Purchase'),
        ('Return', 'Return'),
        ('Damage', 'Damaged Stock'),
        ('Expiration', 'Expired'),
        ('Correction', 'Inventory Correction'),
        ('Sale', 'Sale')
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

        # When a new adjustment is made, update the product's total stock
        # Based on Waggyvet UI, quantity inputted might always be absolute in UI,
        # but logic requires negative logic if it's a reduction.
        # We will assume UI submits correct signed integer or we handle sign in view/form.
        # But we will blindly add the signed quantity to stock here for simplicity if it's new.
        if is_new:
            # Re-fetch product to avoid race conditions slightly
            # pylint: disable=no-member
            product = Product.objects.get(pk=self.product.pk)

            # Subtractions: Damage, Expiration.
            # (Returns could be customer returns (add) or return to vendor (sub)).
            # Let's rely on the form to provide a negative number if it's a deduction,
            # or handle it strictly here based on type.
            if self.adjustment_type in ['Damage', 'Expiration']:
                if self.quantity > 0:
                    self.quantity = -self.quantity  # enforce negative
                    # save the corrected sign silently
                    super().save(update_fields=['quantity'])

            product.stock_quantity += self.quantity

            # Ensure stock doesn't go below 0
            if product.stock_quantity < 0:
                product.stock_quantity = 0

            product.save()
