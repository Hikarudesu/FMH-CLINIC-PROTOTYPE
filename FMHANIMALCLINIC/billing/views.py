"""Views for the billing app."""
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView
from django.db import transaction

from .models import BillableItem, Invoice
from .forms import BillableItemForm, InvoiceForm, InvoiceItemFormSet


def statement_list(request):
    """Render a placeholder for the statement of account list."""
    return render(request, 'billing/statement_list.html')


class BillableItemListView(ListView):
    model = BillableItem
    template_name = 'billing/billable_items.html'
    context_object_name = 'items'


class BillableItemCreateView(CreateView):
    model = BillableItem
    form_class = BillableItemForm
    template_name = 'billing/billable_item_form.html'
    success_url = reverse_lazy('billing:billable_items')


class BillableItemUpdateView(UpdateView):
    model = BillableItem
    form_class = BillableItemForm
    template_name = 'billing/billable_item_form.html'
    success_url = reverse_lazy('billing:billable_items')


def billable_item_delete(request, pk):
    item = get_object_or_404(BillableItem, pk=pk)
    if request.method == 'POST':
        item.delete()
    return redirect('billing:billable_items')


class InvoiceListView(ListView):
    model = Invoice
    template_name = 'billing/invoice_list.html'
    context_object_name = 'invoices'


class InvoiceCreateView(CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'billing/invoice_form.html'
    success_url = reverse_lazy('billing:bills_and_payment')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['items'] = InvoiceItemFormSet(self.request.POST)
        else:
            data['items'] = InvoiceItemFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items = context['items']
        with transaction.atomic():
            form.instance.created_by = self.request.user if self.request.user.is_authenticated else None
            self.object = form.save()
            if items.is_valid():
                items.instance = self.object
                items.save()
        return super().form_valid(form)


class InvoiceUpdateView(UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'billing/invoice_form.html'
    success_url = reverse_lazy('billing:bills_and_payment')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['items'] = InvoiceItemFormSet(
                self.request.POST, instance=self.object)
        else:
            data['items'] = InvoiceItemFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items = context['items']
        with transaction.atomic():
            self.object = form.save()
            if items.is_valid():
                items.instance = self.object
                items.save()
        return super().form_valid(form)


def invoice_delete(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        invoice.delete()
    return redirect('billing:bills_and_payment')
