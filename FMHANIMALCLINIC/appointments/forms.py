"""
Forms for the appointments app.
"""
# pylint: disable=no-member


from datetime import time
from django import forms
from django.core.exceptions import ValidationError

from branches.models import Branch
from employees.models import StaffMember, VetSchedule

from .models import Appointment
from .forms_pylint import *  # pylint: disable=wildcard-import,unused-wildcard-import


def _check_double_booking(cleaned_data):
    """Shared validation: reject if the vet+date+time slot is already booked."""
    vet = cleaned_data.get('preferred_vet')
    appt_date = cleaned_data.get('appointment_date')
    appt_time = cleaned_data.get('appointment_time')
    branch = cleaned_data.get('branch')

    if not appt_date or not appt_time or not branch:
        return  # other validators will catch missing required fields

    if time(12, 0) <= appt_time < time(13, 0):
        raise ValidationError(
            'Appointments cannot be scheduled between 12:00 PM and 1:00 PM (Lunch Break).'
        )

    if vet:
        # Specific vet selected — check if that vet is already booked
        conflict = Appointment.objects.filter(
            preferred_vet=vet,
            appointment_date=appt_date,
            appointment_time=appt_time,
        ).exclude(status='CANCELLED').exists()

        if conflict:
            raise ValidationError(
                'This time slot is already booked for this veterinarian. '
                'Please select a different time.'
            )
    else:
        # No vet selected ("any available") — check if ALL scheduled vets
        # at this branch+date+time are booked
        scheduled_vet_ids = VetSchedule.objects.filter(
            branch=branch,
            date=appt_date,
            is_available=True,
        ).values_list('staff_id', flat=True).distinct()

        if scheduled_vet_ids:
            booked_vet_ids = Appointment.objects.filter(
                appointment_date=appt_date,
                appointment_time=appt_time,
                preferred_vet_id__in=scheduled_vet_ids,
            ).exclude(status='CANCELLED').values_list(
                'preferred_vet_id', flat=True
            )

            if set(scheduled_vet_ids) == set(booked_vet_ids):
                raise ValidationError(
                    'All veterinarians are fully booked at this time. '
                    'Please select a different time slot.'
                )


class PublicAppointmentForm(forms.ModelForm):
    """Booking form for public visitors (no login required)."""

    class Meta:
        """Form metadata."""
        model = Appointment
        fields = [
            'owner_name', 'owner_email', 'owner_phone', 'owner_address',
            'pet_name', 'pet_species', 'pet_breed', 'pet_dob', 'pet_sex', 'pet_color',
            'pet_symptoms',
            'reason', 'branch', 'preferred_vet',
            'appointment_date', 'appointment_time',
        ]
        widgets = {
            'owner_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Your full name',
            }),
            'owner_email': forms.EmailInput(attrs={
                'class': 'form-control', 'placeholder': 'email@example.com',
            }),
            'owner_phone': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': '09XX XXX XXXX',
            }),
            'owner_address': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Your full address',
            }),
            'pet_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': "Your pet's name",
            }),
            'pet_species': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Dog, Cat, Bird',
            }),
            'pet_breed': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Golden Retriever',
            }),
            'pet_dob': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. 2020-01-15 or 3 years',
            }),
            'pet_sex': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('', '---'),
                ('MALE', 'Male'),
                ('FEMALE', 'Female'),
            ]),
            'pet_color': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Brown, White',
            }),
            'pet_symptoms': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Please describe any symptoms or reasons for visit',
            }),
            'reason': forms.Select(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'preferred_vet': forms.Select(attrs={'class': 'form-control'}),
            'appointment_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
            }),
            'appointment_time': forms.TimeInput(attrs={
                'class': 'form-control', 'type': 'time', 'readonly': 'readonly',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['branch'].queryset = Branch.objects.filter(is_active=True)
        self.fields['preferred_vet'].queryset = StaffMember.objects.none()
        self.fields['preferred_vet'].required = False
        self.fields['pet_species'].required = False
        self.fields['pet_breed'].required = False
        self.fields['pet_dob'].required = False
        self.fields['pet_sex'].required = False
        self.fields['pet_color'].required = False
        self.fields['pet_symptoms'].required = False
        self.fields['owner_email'].required = False
        self.fields['owner_phone'].required = False
        self.fields['owner_address'].required = False

        if 'branch' in self.data:
            try:
                branch_id = int(self.data.get('branch'))
                self.fields['preferred_vet'].queryset = StaffMember.objects.filter(
                    position=StaffMember.Position.VETERINARIAN,
                    is_active=True,
                    branch_id=branch_id,
                )
            except (ValueError, TypeError):
                pass

    def clean(self):
        cleaned_data = super().clean()
        _check_double_booking(cleaned_data)
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.source = Appointment.Source.WALKIN
        # Check if the user selected 'yes' on the special returning client radio buttons in HTML
        is_returning = self.data.get('is_returning') == 'yes'
        instance.is_returning_customer = is_returning

        if commit:
            instance.save()
        return instance


class PortalAppointmentForm(forms.ModelForm):
    """Booking form for logged-in portal users."""

    # Hidden field for selected pet ID
    selected_pet_id = forms.IntegerField(required=False, widget=forms.HiddenInput())

    class Meta:
        """Form metadata."""
        model = Appointment
        fields = [
            'owner_name', 'owner_phone',
            'pet_name', 'pet_species', 'pet_breed', 'pet_dob', 'pet_sex', 'pet_color',
            'pet_symptoms',
            'reason', 'branch', 'preferred_vet',
            'appointment_date', 'appointment_time',
            'notes',
        ]
        widgets = {
            'owner_name': forms.TextInput(attrs={
                'class': 'form-control book-input', 'placeholder': ' ',
            }),
            'owner_phone': forms.TextInput(attrs={
                'class': 'form-control book-input', 'placeholder': ' ',
            }),
            'pet_name': forms.TextInput(attrs={
                'class': 'form-control book-input', 'placeholder': ' ', 'list': 'petNames',
            }),
            'pet_species': forms.TextInput(attrs={
                'class': 'form-control book-input', 'placeholder': ' ',
            }),
            'pet_breed': forms.TextInput(attrs={
                'class': 'form-control book-input', 'placeholder': ' ',
            }),
            'pet_dob': forms.TextInput(attrs={
                'class': 'form-control book-input', 'placeholder': ' ',
            }),
            'pet_sex': forms.Select(attrs={'class': 'form-control book-input'}, choices=[
                ('', '---'),
                ('MALE', 'Male'),
                ('FEMALE', 'Female'),
            ]),
            'pet_color': forms.TextInput(attrs={
                'class': 'form-control book-input', 'placeholder': ' ',
            }),
            'pet_symptoms': forms.Textarea(attrs={
                'class': 'form-control book-input', 'rows': 2,
                'placeholder': ' ',
            }),
            'reason': forms.Select(attrs={'class': 'form-control book-input'}),
            'branch': forms.Select(attrs={'class': 'form-control book-input'}),
            'preferred_vet': forms.Select(attrs={'class': 'form-control book-input'}),
            'appointment_date': forms.DateInput(attrs={
                'class': 'form-control book-input', 'type': 'date',
            }),
            'appointment_time': forms.TimeInput(attrs={
                'class': 'form-control book-input', 'type': 'time', 'readonly': 'readonly',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control book-input', 'rows': 2,
                'placeholder': ' ',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['branch'].queryset = Branch.objects.filter(is_active=True)
        self.fields['preferred_vet'].queryset = StaffMember.objects.none()
        self.fields['preferred_vet'].required = False
        self.fields['pet_species'].required = False
        self.fields['pet_breed'].required = False
        self.fields['pet_dob'].required = False
        self.fields['pet_sex'].required = False
        self.fields['pet_color'].required = False
        self.fields['pet_symptoms'].required = False
        self.fields['owner_phone'].required = False
        self.fields['notes'].required = False

        if self.user:
            self.fields['owner_name'].initial = self.user.get_full_name(
            ) or self.user.username

        if 'branch' in self.data:
            try:
                branch_id = int(self.data.get('branch'))
                self.fields['preferred_vet'].queryset = StaffMember.objects.filter(
                    position=StaffMember.Position.VETERINARIAN,
                    is_active=True,
                    branch_id=branch_id,
                )
            except (ValueError, TypeError):
                pass

    def clean(self):
        cleaned_data = super().clean()
        _check_double_booking(cleaned_data)
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.source = Appointment.Source.PORTAL
        instance.is_returning_customer = True  # Always True for logged-in users
        if self.user:
            instance.user = self.user
            instance.owner_email = self.user.email

            if instance.pet_name:
                from patients.models import Pet
                pet_name_clean = instance.pet_name.strip()
                existing_pet = Pet.objects.filter(
                    owner=self.user, name__iexact=pet_name_clean).first()
                if not existing_pet:
                    # Try to parse age from pet_dob text
                    pet_age = 0
                    if instance.pet_dob:
                        dob_text = instance.pet_dob.strip()
                        # Try to extract numeric age
                        import re
                        age_match = re.search(r'(\d+)', dob_text)
                        if age_match:
                            pet_age = int(age_match.group(1))
                    Pet.objects.create(
                        owner=self.user,
                        name=pet_name_clean,
                        species=instance.pet_species.strip() if instance.pet_species else 'Unknown',
                        breed=instance.pet_breed.strip() if instance.pet_breed else '',
                        age=pet_age,
                        sex=instance.pet_sex or Pet.Sex.MALE,
                        color=instance.pet_color.strip() if instance.pet_color else '',
                    )

        if commit:
            instance.save()
        return instance


class AdminQuickCreateForm(forms.ModelForm):
    """Quick create form for admins — bypasses user restrictions."""

    # Hidden field for selected user ID (for portal bookings)
    selected_user_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    selected_pet_id = forms.IntegerField(required=False, widget=forms.HiddenInput())

    class Meta:
        """Form metadata."""
        model = Appointment
        fields = [
            'owner_name', 'owner_email', 'owner_phone', 'owner_address',
            'pet_name', 'pet_species', 'pet_breed', 'pet_dob', 'pet_sex', 'pet_color',
            'reason', 'branch', 'preferred_vet',
            'appointment_date', 'appointment_time',
            'status', 'source', 'notes',
        ]
        widgets = {
            'owner_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Owner name',
            }),
            'owner_email': forms.EmailInput(attrs={
                'class': 'form-control', 'placeholder': 'email@example.com',
            }),
            'owner_phone': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': '09XX XXX XXXX',
            }),
            'owner_address': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Full address',
            }),
            'pet_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': "Pet's name",
            }),
            'pet_species': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Dog, Cat',
            }),
            'pet_breed': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Poodle',
            }),
            'pet_dob': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. 2020-05-10 or 2 years',
            }),
            'pet_sex': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('', '---'),
                ('MALE', 'Male'),
                ('FEMALE', 'Female'),
            ]),
            'pet_color': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Brown',
            }),
            'reason': forms.Select(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'preferred_vet': forms.Select(attrs={'class': 'form-control'}),
            'appointment_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
            }),
            'appointment_time': forms.TimeInput(attrs={
                'class': 'form-control', 'type': 'time',
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'source': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Walk-in / phone call notes...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['branch'].queryset = Branch.objects.filter(is_active=True)
        self.fields['preferred_vet'].queryset = StaffMember.objects.filter(
            position=StaffMember.Position.VETERINARIAN,
            is_active=True,
        )
        self.fields['preferred_vet'].required = False
        self.fields['owner_email'].required = False
        self.fields['owner_phone'].required = False
        self.fields['owner_address'].required = False
        self.fields['pet_species'].required = False
        self.fields['pet_breed'].required = False
        self.fields['pet_dob'].required = False
        self.fields['pet_sex'].required = False
        self.fields['pet_color'].required = False
        self.fields['notes'].required = False

    def clean(self):
        cleaned_data = super().clean()
        _check_double_booking(cleaned_data)
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Link user if portal source and user_id provided
        user_id = self.cleaned_data.get('selected_user_id')
        if user_id:
            from accounts.models import User
            try:
                instance.user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                pass
        if commit:
            instance.save()
        return instance


class AppointmentEditForm(forms.ModelForm):
    """Form for editing existing appointments in admin portal."""

    class Meta:
        """Form metadata."""
        model = Appointment
        fields = [
            'owner_name', 'owner_email', 'owner_phone', 'owner_address',
            'pet_name', 'pet_species', 'pet_breed', 'pet_dob', 'pet_sex', 'pet_color',
            'pet_symptoms',
            'reason', 'branch', 'preferred_vet',
            'appointment_date', 'appointment_time',
            'status', 'source', 'notes',
        ]
        widgets = {
            'owner_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Owner name',
            }),
            'owner_email': forms.EmailInput(attrs={
                'class': 'form-control', 'placeholder': 'email@example.com',
            }),
            'owner_phone': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': '09XX XXX XXXX',
            }),
            'owner_address': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Full address',
            }),
            'pet_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': "Pet's name",
            }),
            'pet_species': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Dog, Cat',
            }),
            'pet_breed': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Poodle',
            }),
            'pet_dob': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. 2020-05-10 or 2 years',
            }),
            'pet_sex': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('', '---'),
                ('MALE', 'Male'),
                ('FEMALE', 'Female'),
            ]),
            'pet_color': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Brown',
            }),
            'pet_symptoms': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Current symptoms',
            }),
            'reason': forms.Select(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'preferred_vet': forms.Select(attrs={'class': 'form-control'}),
            'appointment_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
            }),
            'appointment_time': forms.TimeInput(attrs={
                'class': 'form-control', 'type': 'time',
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'source': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Additional notes...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['branch'].queryset = Branch.objects.filter(is_active=True)
        self.fields['preferred_vet'].queryset = StaffMember.objects.filter(
            position=StaffMember.Position.VETERINARIAN,
            is_active=True,
        )
        self.fields['preferred_vet'].required = False
        self.fields['owner_email'].required = False
        self.fields['owner_phone'].required = False
        self.fields['owner_address'].required = False
        self.fields['pet_species'].required = False
        self.fields['pet_breed'].required = False
        self.fields['pet_dob'].required = False
        self.fields['pet_sex'].required = False
        self.fields['pet_color'].required = False
        self.fields['pet_symptoms'].required = False
        self.fields['notes'].required = False