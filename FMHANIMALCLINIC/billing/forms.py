"""
Forms for the billing app including billable items, invoices, and invoice items.
"""
from django import forms
from django.forms import inlineformset_factory
from .models import BillableItem, Invoice, InvoiceItem


class BillableItemForm(forms.ModelForm):
    """Form for creating and updating billable items."""
    class Meta:
        """Meta configuration for BillableItemForm."""
        model = BillableItem
        fields = '__all__'
        exclude = ('created_at', 'updated_at')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter item name'
            }),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Select category'
            }),
            'tax_rate': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Select tax rate'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Add tags (press Enter)'
            }),
            'track_stock': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            }),
            'initial_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Auto-generated if blank'
            }),
            'barcode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter barcode'
            }),
            'manufacturer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter manufacturer'
            }),
            'duration': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter description'
            }),
            'active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Enter rich content or instructions for this billable item...'
            }),
        }


class InvoiceForm(forms.ModelForm):
    """Form for creating and updating invoices."""
    class Meta:
        """Meta configuration for InvoiceForm."""
        model = Invoice
        fields = ['pet', 'branch', 'due_date',
                  'status', 'tax_amount', 'notes']
        widgets = {
            'pet': forms.Select(attrs={'class': 'form-select'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional internal notes...'
            }),
        }


class InvoiceItemForm(forms.ModelForm):
    """Form for adding items to an invoice."""
    class Meta:
        """Meta configuration for InvoiceItemForm."""
        model = InvoiceItem
        fields = ['billable_item', 'quantity', 'unit_price', 'description']
        widgets = {
            'billable_item': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Auto-filled if empty'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional override'
            }),
        }


InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=1,
    can_delete=True
)
