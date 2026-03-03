from django import forms
from .models import Pet


class PetForm(forms.ModelForm):
    """Form for creating and editing a pet."""

    class Meta:
        model = Pet
        fields = ['name', 'species', 'breed', 'age', 'sex', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'pf-input', 'placeholder': ' ',
            }),
            'species': forms.TextInput(attrs={
                'class': 'pf-input', 'placeholder': ' ',
            }),
            'breed': forms.TextInput(attrs={
                'class': 'pf-input', 'placeholder': ' ',
            }),
            'age': forms.NumberInput(attrs={
                'class': 'pf-input', 'placeholder': ' ', 'min': 0,
            }),
            'sex': forms.Select(attrs={
                'class': 'pf-input',
            }),
            'color': forms.TextInput(attrs={
                'class': 'pf-input', 'placeholder': ' ',
            }),
        }


class AdminPetForm(forms.ModelForm):
    """Form for creating and editing a pet as an Admin, including owner selection."""

    class Meta:
        model = Pet
        fields = ['owner', 'name', 'species', 'breed', 'age', 'sex', 'color']
        widgets = {
            'owner': forms.Select(attrs={
                'class': 'pf-input',
            }),
            'name': forms.TextInput(attrs={
                'class': 'pf-input', 'placeholder': ' ',
            }),
            'species': forms.TextInput(attrs={
                'class': 'pf-input', 'placeholder': ' ',
            }),
            'breed': forms.TextInput(attrs={
                'class': 'pf-input', 'placeholder': ' ',
            }),
            'age': forms.NumberInput(attrs={
                'class': 'pf-input', 'placeholder': ' ', 'min': 0,
            }),
            'sex': forms.Select(attrs={
                'class': 'pf-input',
            }),
            'color': forms.TextInput(attrs={
                'class': 'pf-input', 'placeholder': ' ',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize the label for the owner dropdown
        self.fields['owner'].label_from_instance = lambda obj: f"{obj.get_full_name()} ({obj.username})" if obj.get_full_name(
        ).strip() else obj.username
