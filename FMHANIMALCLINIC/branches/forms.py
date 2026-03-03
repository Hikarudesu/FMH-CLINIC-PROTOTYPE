from django import forms
from .models import Branch


class BranchForm(forms.ModelForm):
    """Form for creating and updating Branch instances."""

    class Meta:
        model = Branch
        fields = [
            'name', 'branch_code',
            'phone_number', 'email',
            'address', 'city', 'state', 'zip_code',
            'operating_hours', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Downtown Clinic'}),
            'branch_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. DWTN'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street Address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State/Province'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Zip/Postal Code'}),
            'operating_hours': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'e.g. Mon-Fri: 8am-6pm, Sat: 9am-2pm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
