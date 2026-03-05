"""
Forms for the billing app — clinic services only.
"""
from django import forms
from .models import BillableItem


class BillableItemForm(forms.ModelForm):
    """Form for creating and updating clinic services."""
    class Meta:
        """Meta configuration for BillableItemForm."""
        model = BillableItem
        fields = [
            'name', 'cost', 'price', 'branch', 'category',
            'tax_rate', 'duration', 'description', 'active', 'content'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., General Consultation'
            }),
            'cost': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01'
            }),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Consultation, Surgery, Grooming'
            }),
            'tax_rate': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., VAT 12%'
            }),
            'duration': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Minutes'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the service...'
            }),
            'active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Instructions, notes, or content...'
            }),
        }
