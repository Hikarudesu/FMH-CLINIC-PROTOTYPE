"""Billing app models."""

import uuid

from django.db import models
from branches.models import Branch
from patients.models import Pet
from accounts.models import User
from inventory.models import Product


class BillableItem(models.Model):
    """Represents a billable item (product, service, or medication)."""
    ITEM_TYPE_CHOICES = [
        ('Product', 'Product'),
        ('Service', 'Service'),
        ('Medication', 'Medication'),
    ]

    name = models.CharField(max_length=200)
    type = models.CharField(
        max_length=50, choices=ITEM_TYPE_CHOICES, default='Product')
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL,
                               null=True, blank=True, related_name='billable_items')
    inventory_product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='linked_billable_items',
        help_text=("Link to an Inventory Product. Stock will "
                   "be deducted automatically when invoiced.")
    )
    category = models.CharField(max_length=100, blank=True)
    tax_rate = models.CharField(max_length=50, blank=True)
    tags = models.CharField(max_length=255, blank=True)

    track_stock = models.BooleanField(default=False)
    initial_stock = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=0)

    sku = models.CharField(max_length=100, blank=True)
    barcode = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=200, blank=True)
    duration = models.IntegerField(default=0, help_text="Duration in minutes")

    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    # NEW FEATURE: Content Section
    content = models.TextField(
        blank=True, help_text="Manage content associated with this billable record.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options."""
        ordering = ['-created_at']

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        if not self.sku:
            # Auto-generate a simple SKU if blank
            self.sku = f"AUTO-{str(uuid.uuid4())[:6].upper()}"
        super().save(*args, **kwargs)


class Invoice(models.Model):
    """Represents a billing invoice."""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Payment'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    pet = models.ForeignKey(
        Pet, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True)

    date = models.DateField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options."""
        ordering = ['-created_at']

    def __str__(self):
        return str(f"Invoice {self.invoice_number} - {self.pet}")

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f"INV-{str(uuid.uuid4())[:8].upper()}"

        # Calculate totals
        if self.pk:
            items = self.items.all()  # pylint: disable=no-member
        else:
            items = []
        self.subtotal = sum(item.total_price for item in items)
        # Simplified tax for now (could be based on BillableItem tax_rate)
        self.total_amount = self.subtotal + self.tax_amount

        super().save(*args, **kwargs)


class InvoiceItem(models.Model):
    """Represents an item within an invoice."""
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name='items')
    billable_item = models.ForeignKey(
        BillableItem, on_delete=models.SET_NULL, null=True)

    description = models.CharField(max_length=255, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        if self.billable_item and not self.unit_price:
            self.unit_price = getattr(self.billable_item, 'price', 0.00)
        if not self.description and self.billable_item:
            self.description = getattr(self.billable_item, 'name', '')

        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        # Resave invoice to update totals
        if getattr(self.invoice, 'pk', None):
            invoice_save = getattr(self.invoice, 'save', None)
            if invoice_save:
                invoice_save()
