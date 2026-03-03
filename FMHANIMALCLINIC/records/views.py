"""
Views for handling specific actions within Medical Records.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden

from django.utils import timezone
import json
import re
from .models import MedicalRecord
from .forms import MedicalRecordForm


@login_required
def print_record_view(request, pk):
    """View to display a printer-friendly version of a medical record."""
    record = get_object_or_404(MedicalRecord, pk=pk)

    # Optional security: Only allow pet's owner or staff to view the record
    if not request.user.is_staff and record.pet.owner != request.user:
        return HttpResponseForbidden("You do not have permission to view this record.")

    return render(request, 'records/print_record.html', {'record': record})


@login_required
def admin_records_list(request):
    """View to list all medical records for admin/staff in the portal."""
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("You do not have permission to view this page.")

    query = request.GET.get('q', '')
    records = MedicalRecord.objects.all().select_related('pet', 'vet')

    if query:
        records = records.filter(
            Q(pet__name__icontains=query) |
            Q(pet__owner__first_name__icontains=query) |
            Q(pet__owner__last_name__icontains=query) |
            Q(history_clinical_signs__icontains=query) |
            Q(diagnosis__icontains=query) |
            Q(treatment__icontains=query)
        ).distinct()

    context = {
        'records': records,
        'search_query': query
    }
    return render(request, 'records/admin_list.html', context)


@login_required
def admin_record_create(request):
    """View to create a new medical record matching the physical card structure."""
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("You do not have permission to view this page.")

    if request.method == 'POST':
        form = MedicalRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            if hasattr(request.user, 'staffmember'):
                record.vet = request.user.staffmember

            # --- Dynamic Owner Resolution or Creation ---
            from django.contrib.auth import get_user_model
            User = get_user_model()
            owner_name_str = request.POST.get('owner_name', '').strip()
            owner = None
            if owner_name_str:
                parts = owner_name_str.split(' ', 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ''
                owner_qs = User.objects.filter(
                    first_name=first_name, last_name=last_name, role=User.Role.PET_OWNER)
                if owner_qs.exists():
                    owner = owner_qs.first()
                    # Update contact/address if changed
                    if 'owner_contact' in request.POST:
                        owner.phone_number = request.POST.get('owner_contact')
                    if 'owner_address' in request.POST:
                        owner.address = request.POST.get('owner_address')
                    owner.save()
                else:
                    # Create new Owner profile
                    username = f"{first_name.lower()}{last_name.lower()}_{User.objects.count()}"
                    owner = User.objects.create_user(
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        role=User.Role.PET_OWNER,
                        address=request.POST.get('owner_address', ''),
                        phone_number=request.POST.get('owner_contact', '')
                    )

            # --- Dynamic Pet Resolution or Creation ---
            from patients.models import Pet
            pet_name_str = request.POST.get('pet_name', '').strip()
            pet = None
            if pet_name_str and owner:
                pet_qs = Pet.objects.filter(
                    name__iexact=pet_name_str, owner=owner)
                if pet_qs.exists():
                    pet = pet_qs.first()
                else:
                    pet = Pet(name=pet_name_str, owner=owner)

                # Update attributes
                if 'pet_color' in request.POST:
                    pet.color = request.POST.get('pet_color')
                if 'pet_breed' in request.POST:
                    pet.breed = request.POST.get('pet_breed')
                if 'pet_species' in request.POST:
                    pet.species = request.POST.get('pet_species')

                pet_age_str = request.POST.get('pet_age', '')
                digits = re.findall(r'\d+', pet_age_str)
                if digits:
                    pet.age = int(digits[0])
                else:
                    pet.age = getattr(pet, 'age', 0) or 0

                pet_sex_str = request.POST.get('pet_sex', '').upper()
                if pet_sex_str in dict(Pet.Sex.choices).keys() or pet_sex_str in ['MALE', 'FEMALE']:
                    pet.sex = "MALE" if "MALE" in pet_sex_str else "FEMALE" if "FEMALE" in pet_sex_str else pet_sex_str

                pet.save()

            if pet:
                record.pet = pet
                record.save()
                return redirect('records:admin_list')
            else:
                form.add_error(
                    None, "Could not resolve or create patient profile. Ensure Owner and Pet names are provided.")
    else:
        # Pre-select pet if passed in URL (optional enhancement)
        initial_data = {'date_recorded': timezone.now().date()}
        pet_id = request.GET.get('pet')
        if pet_id:
            initial_data['pet'] = pet_id
        form = MedicalRecordForm(initial=initial_data)

    # Build pet details JSON & Data for dynamic form population
    from patients.models import Pet
    pets = Pet.objects.select_related('owner').all()
    pets_data = {}
    for p in pets:
        pets_data[p.name] = {  # Map by name for JS datalist lookup
            'owner_name': p.owner.get_full_name() or p.owner.username,
            'owner_address': p.owner.address,
            'owner_contact': p.owner.phone_number,
            'pet_age': p.age,
            'pet_color': p.color,
            'pet_species': p.species,
            'pet_breed': p.breed,
            'pet_sex': p.get_sex_display(),
        }

    context = {
        'form': form,
        'pets_data': pets_data,
        'pets_json': json.dumps(pets_data),
    }
    return render(request, 'records/admin_form.html', context)


@login_required
def admin_record_edit(request, pk):
    """View to edit an existing medical record."""
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("You do not have permission to view this page.")

    record = get_object_or_404(MedicalRecord, pk=pk)

    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, instance=record)
        if form.is_valid():
            updated_record = form.save(commit=False)

            # --- Update Owner details if provided ---
            from django.contrib.auth import get_user_model
            User = get_user_model()
            owner_name_str = request.POST.get('owner_name', '').strip()
            if owner_name_str:
                parts = owner_name_str.split(' ', 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ''
                owner_qs = User.objects.filter(
                    first_name=first_name, last_name=last_name, role=User.Role.PET_OWNER)
                if owner_qs.exists():
                    owner = owner_qs.first()
                    if 'owner_contact' in request.POST:
                        owner.phone_number = request.POST.get('owner_contact')
                    if 'owner_address' in request.POST:
                        owner.address = request.POST.get('owner_address')
                    owner.save()

            # --- Update Pet details if provided ---
            from patients.models import Pet
            pet = record.pet
            if 'pet_color' in request.POST:
                pet.color = request.POST.get('pet_color')
            if 'pet_breed' in request.POST:
                pet.breed = request.POST.get('pet_breed')
            if 'pet_species' in request.POST:
                pet.species = request.POST.get('pet_species')

            pet_age_str = request.POST.get('pet_age', '')
            digits = re.findall(r'\d+', pet_age_str)
            if digits:
                pet.age = int(digits[0])

            pet_sex_str = request.POST.get('pet_sex', '').upper()
            if pet_sex_str in ['MALE', 'FEMALE']:
                pet.sex = pet_sex_str

            pet.save()
            updated_record.save()
            messages.success(request, f'Record for {record.pet.name} has been updated!')
            return redirect('records:admin_list')
    else:
        form = MedicalRecordForm(instance=record)

    # Build pet details JSON for dynamic form population
    from patients.models import Pet
    pets = Pet.objects.select_related('owner').all()
    pets_data = {}
    for p in pets:
        pets_data[p.name] = {
            'owner_name': p.owner.get_full_name() or p.owner.username,
            'owner_address': p.owner.address,
            'owner_contact': p.owner.phone_number,
            'pet_age': p.age,
            'pet_color': p.color,
            'pet_species': p.species,
            'pet_breed': p.breed,
            'pet_sex': p.get_sex_display(),
        }

    context = {
        'form': form,
        'record': record,
        'pets_data': pets_data,
        'pets_json': json.dumps(pets_data),
    }
    return render(request, 'records/admin_edit_form.html', context)


@login_required
def admin_record_delete(request, pk):
    """View to delete a medical record."""
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("You do not have permission to view this page.")

    record = get_object_or_404(MedicalRecord, pk=pk)

    if request.method == 'POST':
        pet_name = record.pet.name
        record.delete()
        messages.success(request, f'Medical record for {pet_name} has been deleted.')
        return redirect('records:admin_list')

    return render(request, 'records/admin_confirm_delete.html', {'record': record})
