"""Views for the billing app — Services management."""
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView

from .models import BillableItem
from .forms import BillableItemForm


class BillableItemListView(ListView):
    """View for listing all clinic services."""
    model = BillableItem
    template_name = 'billing/billable_items.html'
    context_object_name = 'items'


class BillableItemCreateView(CreateView):
    """View for creating a new clinic service."""
    model = BillableItem
    form_class = BillableItemForm
    template_name = 'billing/billable_item_form.html'
    success_url = reverse_lazy('billing:billable_items')


class BillableItemUpdateView(UpdateView):
    """View for updating an existing clinic service."""
    model = BillableItem
    form_class = BillableItemForm
    template_name = 'billing/billable_item_form.html'
    success_url = reverse_lazy('billing:billable_items')


def billable_item_delete(request, pk):
    """View for deleting a clinic service."""
    item = get_object_or_404(BillableItem, pk=pk)
    if request.method == 'POST':
        item.delete()
    return redirect('billing:billable_items')
