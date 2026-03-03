"""
Forms for the records application.
"""
from django import forms
from .models import MedicalRecord


class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = [
            'date_recorded', 'weight', 'temperature',
            'history_clinical_signs', 'treatment', 'rx', 'ff_up'
        ]
        widgets = {
            'date_recorded': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Wt (kg)'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Temp (°C)'}),
            'history_clinical_signs': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'treatment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'rx': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ff_up': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
