"""Signals for the billing application."""

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from inventory.models import StockAdjustment
from .models import Invoice


@receiver(pre_save, sender=Invoice)
def process_invoice_stock_reduction(sender, instance, **kwargs):  # pylint: disable=unused-argument
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
        # pylint: disable=no-member
        old_instance = Invoice.objects.get(pk=instance.pk)
    except Invoice.DoesNotExist:  # pylint: disable=no-member
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
                # The inventory StockAdjustment model saves the quantity negatively for
                # reductions. Let's use 'Correction' with a negative quantity.

                StockAdjustment.objects.create(  # pylint: disable=no-member
                    branch=branch,
                    product=product,
                    adjustment_type='Sale',
                    reference=instance.invoice_number,
                    date=timezone.now().date(),
                    quantity=-item.quantity,  # Negative for subtraction
                    cost_per_unit=product.price,
                    reason=f"Auto-deducted from Invoice {instance.invoice_number}"
                )
