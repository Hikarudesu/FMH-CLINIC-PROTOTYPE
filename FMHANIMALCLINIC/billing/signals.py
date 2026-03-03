from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Invoice
from inventory.models import StockAdjustment
from django.utils import timezone


@receiver(pre_save, sender=Invoice)
def process_invoice_stock_reduction(sender, instance, **kwargs):
    """
    When an invoice status changes to PAID from any other state,
    we automatically trigger a StockAdjustment for each InvoiceItem
    that has an associated inventory_product.
    """
    if not instance.pk:
        # It's a brand new Invoice. If it's being created directly as PAID, process it.
        # But wait, we can't process items because they aren't added yet!
        # Invoices should ideally be Draft/Pending first, then items added, then PAID.
        return

    try:
        old_instance = Invoice.objects.get(pk=instance.pk)
    except Invoice.DoesNotExist:
        return

    # Check if the status is transitioning to 'PAID'
    if old_instance.status != 'PAID' and instance.status == 'PAID':

        # Loop over all items in the invoice
        for item in instance.items.all():
            billable_item = item.billable_item

            # If the billable item is linked to an inventory product and tracks stock
            if billable_item and billable_item.inventory_product and billable_item.track_stock:
                product = billable_item.inventory_product

                # Check if branch matches or fallback to invoice branch
                branch = product.branch
                if not branch:
                    branch = instance.branch

                if not branch:
                    continue  # We need a branch for StockAdjustment

                # Create a StockAdjustment to reduce the inventory
                # The inventory StockAdjustment model saves the quantity negatively for 'Purchase' if we do it manually,
                # Wait, looking at inventory/models.py, 'Purchase' normally ADDS stock.
                # Let's use 'Correction' or 'Damage' or 'Sale' if available.
                # StockAdjustment model types: 'Purchase', 'Return', 'Damage', 'Expiration', 'Correction'.
                # Let's use 'Correction' with a negative quantity.

                StockAdjustment.objects.create(
                    branch=branch,
                    product=product,
                    adjustment_type='Correction',
                    reference=instance.invoice_number,
                    date=timezone.now().date(),
                    quantity=-item.quantity,  # Negative for subtraction
                    cost_per_unit=product.price,
                    reason=f"Auto-deducted from Invoice {instance.invoice_number}"
                )
