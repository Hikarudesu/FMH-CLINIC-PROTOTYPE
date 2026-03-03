"""
Forms for the accounts application.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class PetOwnerRegistrationForm(UserCreationForm):
    """Registration form specifically for Pet Owners"""

    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'First name',
            'class': 'form-control',
        })
    )

    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Last name',
            'class': 'form-control',
        })
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email',
            'class': 'form-control',
        })
    )

    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': '+63 9XX XXX XXXX',
            'class': 'form-control',
        })
    )

    address = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Enter your complete address',
            'class': 'form-control',
            'rows': 3,
        }),
        required=True,
        help_text=(
            'Please provide your complete address including '
            'street, barangay, city, and province'
        )
    )

    terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        label='I agree to the Terms of Service and Privacy Policy'
    )

    class Meta:
        """Meta options for PetOwnerRegistrationForm."""
        model = User
        fields = ('username', 'first_name', 'last_name', 'email',
                  'phone_number', 'address', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Customize username field
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Create a username',
            'class': 'form-control',
        })

        # Customize password fields
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'Create a password',
            'class': 'form-control',
        })

        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Confirm your password',
            'class': 'form-control',
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone_number = self.cleaned_data['phone_number']
        user.address = self.cleaned_data['address']
        user.role = User.Role.PET_OWNER  # Ensure this registration is for pet owners only

        if commit:
            user.save()
        return user

    def clean_email(self):
        """Ensure the email is unique."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "A user with this email already exists.")
        return email


class UserProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile details."""

    class Meta:
        """Meta options for UserProfileUpdateForm."""
        model = User
        fields = ('first_name', 'last_name',
                  'email', 'phone_number', 'address', 'branch', 'profile_picture')
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': ' '
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': ' '
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control', 'placeholder': ' '
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': ' '
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': ' '
            }),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }
