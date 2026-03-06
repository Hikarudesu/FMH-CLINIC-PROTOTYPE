"""
Forms for the inventory application.
"""
from django import forms
from .models import StockAdjustment, Product, StockTransfer


class ProductForm(forms.ModelForm):
    """Form for managing Product / Medication details."""
    class Meta:
        """Meta options for ProductForm."""
        model = Product
        fields = [
            'branch', 'item_type', 'name', 'description',
            'sku', 'barcode', 'manufacturer', 'unit_cost', 'price',
            'stock_quantity', 'min_stock_level',
            'expiration_date', 'is_available'
        ]
        widgets = {
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'item_type': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Item name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3
            }),
            'sku': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Auto-generated if blank'
            }),
            'barcode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Scan or enter barcode'
            }),
            'manufacturer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Zoetis, Pfizer'
            }),
            'unit_cost': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
                'id': 'id_unit_cost'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01',
                'id': 'id_price'
            }),
            'stock_quantity': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'min_stock_level': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'expiration_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date'
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class StockAdjustmentForm(forms.ModelForm):
    """Form for adding new stock adjustments based on Waggyvet layout."""
    class Meta:
        """Meta options for StockAdjustmentForm."""
        model = StockAdjustment
        fields = ['branch', 'product', 'adjustment_type',
                  'reference', 'date', 'cost_per_unit', 'quantity', 'reason']
        widgets = {
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'product': forms.Select(attrs={'class': 'form-control'}),
            'adjustment_type': forms.Select(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., Receipt #, Invoice ID, or N/A'
            }),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'cost_per_unit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'reason': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g., Dropped and broken by staff'
            }),
        }


class StockTransferRequestForm(forms.ModelForm):
    """Form to request inventory from another branch."""
    class Meta:
        model = StockTransfer
        fields = ['source_product', 'destination_branch', 'quantity', 'notes']
        widgets = {
            'source_product': forms.Select(attrs={'class': 'form-control'}),
            'destination_branch': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Reason for transfer...'
            }),
        }

    def __init__(self, *args, **kwargs):
        user_branch = kwargs.pop('user_branch', None)
        super().__init__(*args, **kwargs)
        if user_branch:
            # Only allow requesting TO the user's branch
            self.fields['destination_branch'].initial = user_branch
            self.fields['destination_branch'].disabled = True

            # Show products not in the user's branch
            self.fields['source_product'].queryset = Product.objects.exclude(
                branch=user_branch).filter(is_available=True)
