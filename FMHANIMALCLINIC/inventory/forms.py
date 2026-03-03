"""
Forms for the inventory application.
"""
from django import forms
from .models import StockAdjustment


class StockAdjustmentForm(forms.ModelForm):
    """Form for adding new stock adjustments based on Waggyvet layout."""
    class Meta:
        model = StockAdjustment
        fields = ['branch', 'product', 'adjustment_type',
                  'reference', 'date', 'cost_per_unit', 'quantity', 'reason']
        widgets = {
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'product': forms.Select(attrs={'class': 'form-control'}),
            'adjustment_type': forms.Select(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., PO123'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'cost_per_unit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Damaged stock'}),
        }
