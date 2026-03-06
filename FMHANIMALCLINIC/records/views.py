"""
Views for handling specific actions within Medical Records.
"""
# pylint: disable=no-member
import base64
import hashlib
import io
import json
import re

import qrcode
from xhtml2pdf import pisa

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from patients.models import Pet  # pylint: disable=no-member
from branches.models import Branch
from .models import MedicalRecord, RecordEntry
from .forms import MedicalRecordForm, RecordEntryForm

User = get_user_model()


@login_required
def admin_records_list(request):
    """View to list all medical records for admin/staff in the portal."""
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("You do not have permission to view this page.")

    query = request.GET.get('q', '')
    records = MedicalRecord.objects.all().select_related('pet', 'vet', 'branch')

    if query:
        records = records.filter(
            Q(pet__name__icontains=query) |
            Q(pet__owner__first_name__icontains=query) |
            Q(pet__owner__last_name__icontains=query) |
            Q(pet__species__icontains=query) |
            Q(pet__breed__icontains=query) |
            Q(entries__history_clinical_signs__icontains=query) |
            Q(entries__treatment__icontains=query) |
            Q(entries__rx__icontains=query) |
            Q(branch__name__icontains=query)
        ).distinct()

    # Branch filter
    branch_id = request.GET.get('branch', '')
    if branch_id:
        records = records.filter(branch_id=branch_id)

    branches = Branch.objects.filter(
        is_active=True)  # pylint: disable=no-member

    context = {
        'records': records,
        'search_query': query,
        'branches': branches,
        'selected_branch': branch_id,
    }
    return render(request, 'records/admin_list.html', context)


@login_required
def admin_record_create(request):
    """View to create a new visit entry, reusing the pet's existing record card if one exists."""
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("You do not have permission to view this page.")

    if request.method == 'POST':
        entry_form = RecordEntryForm(request.POST)
        if entry_form.is_valid():

            # --- Dynamic Owner Resolution or Creation ---
            owner_name_str = request.POST.get('owner_name', '').strip()
            owner = None
            if owner_name_str:
                parts = owner_name_str.split(' ', 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ''
                owner_qs = User.objects.filter(
                    first_name=first_name,
                    last_name=last_name,
                    role=User.Role.PET_OWNER,
                )
                if owner_qs.exists():
                    owner = owner_qs.first()
                    if 'owner_contact' in request.POST:
                        owner.phone_number = request.POST.get('owner_contact')
                    if 'owner_address' in request.POST:
                        owner.address = request.POST.get('owner_address')
                    owner.save()
                else:
                    username = (
                        f"{first_name.lower()}{last_name.lower()}"
                        f"_{User.objects.count()}"
                    )
                    owner = User.objects.create_user(
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        role=User.Role.PET_OWNER,
                        address=request.POST.get('owner_address', ''),
                        phone_number=request.POST.get('owner_contact', ''),
                    )

            # --- Dynamic Pet Resolution or Creation ---
            pet_name_str = request.POST.get('pet_name', '').strip()
            pet = None
            if pet_name_str and owner:
                pet_qs = Pet.objects.filter(  # pylint: disable=no-member
                    name__iexact=pet_name_str, owner=owner)
                if pet_qs.exists():
                    pet = pet_qs.first()
                else:
                    pet = Pet(name=pet_name_str, owner=owner)

                if 'pet_color' in request.POST:
                    pet.color = request.POST.get('pet_color')
                if 'pet_breed' in request.POST:
                    pet.breed = request.POST.get('pet_breed')
                if 'pet_species' in request.POST:
                    pet.species = request.POST.get('pet_species')

                pet_age_str = request.POST.get('pet_age', '')
                if pet_age_str:
                    pet.dob_or_age = pet_age_str.strip()

                pet_sex_str = request.POST.get('pet_sex', '').upper()
                if "MALE" in pet_sex_str:
                    pet.sex = "MALE"
                elif "FEMALE" in pet_sex_str:
                    pet.sex = "FEMALE"

                pet.save()

            if pet:
                # Get the most recent existing record card for this pet,
                # or create a brand-new one — no duplicate cards.
                branch_id = request.POST.get('branch')
                record = MedicalRecord.objects.filter(pet=pet).order_by('-created_at').first()
                if not record:
                    record = MedicalRecord(
                        pet=pet,
                        date_recorded=entry_form.cleaned_data['date_recorded'],
                        treatment=entry_form.cleaned_data.get('treatment') or '',
                    )
                    if hasattr(request.user, 'staffmember'):
                        record.vet = request.user.staffmember
                    if branch_id:
                        try:
                            from branches.models import Branch as BranchModel
                            record.branch = BranchModel.objects.get(pk=branch_id)
                        except Exception:  # pylint: disable=broad-except
                            pass
                    record.save()
                else:
                    # Update branch on the card if provided
                    if branch_id:
                        try:
                            from branches.models import Branch as BranchModel
                            record.branch = BranchModel.objects.get(pk=branch_id)
                            record.save(update_fields=['branch'])
                        except Exception:  # pylint: disable=broad-except
                            pass

                # Always create a new entry (visit row) on the record card
                entry = entry_form.save(commit=False)
                entry.record = record
                if hasattr(request.user, 'staffmember'):
                    entry.vet = request.user.staffmember
                entry.save()

                messages.success(
                    request,
                    f'Visit entry added to {pet.name}\'s medical record.'
                )
                return redirect('records:admin_detail', pk=record.pk)
            else:
                entry_form.add_error(
                    None,
                    "Could not resolve or create patient profile. "
                    "Ensure Owner and Pet names are provided.",
                )
    else:
        initial_data = {'date_recorded': timezone.now().date()}
        entry_form = RecordEntryForm(initial=initial_data)

    # Build pet details JSON for dynamic form population
    pets = Pet.objects.select_related('owner').all()  # pylint: disable=no-member
    pets_data = {}
    for p in pets:
        last_record = p.medical_records.filter(
            branch__isnull=False
        ).order_by('-date_recorded').first()
        pets_data[p.name] = {
            'owner_name': p.owner.get_full_name() or p.owner.username,
            'owner_address': p.owner.address,
            'owner_contact': p.owner.phone_number,
            'pet_age': p.dob_or_age,
            'pet_color': p.color,
            'pet_species': p.species,
            'pet_breed': p.breed,
            'pet_sex': p.get_sex_display(),
            'branch_id': p.owner.branch_id or (last_record.branch_id if last_record else ''),
        }

    branches = Branch.objects.filter(is_active=True)  # pylint: disable=no-member
    context = {
        'form': entry_form,
        'pets_data': pets_data,
        'pets_json': json.dumps(pets_data),
        'branches': branches,
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
            owner_name_str = request.POST.get('owner_name', '').strip()
            if owner_name_str:
                parts = owner_name_str.split(' ', 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ''
                owner_qs = User.objects.filter(
                    first_name=first_name,
                    last_name=last_name,
                    role=User.Role.PET_OWNER,
                )
                if owner_qs.exists():
                    owner = owner_qs.first()
                    if 'owner_contact' in request.POST:
                        owner.phone_number = request.POST.get('owner_contact')
                    if 'owner_address' in request.POST:
                        owner.address = request.POST.get('owner_address')
                    owner.save()

            # --- Update Pet details if provided ---
            pet = record.pet
            if 'pet_color' in request.POST:
                pet.color = request.POST.get('pet_color')
            if 'pet_breed' in request.POST:
                pet.breed = request.POST.get('pet_breed')
            if 'pet_species' in request.POST:
                pet.species = request.POST.get('pet_species')

            pet_age_str = request.POST.get('pet_age', '')
            if pet_age_str:
                pet.dob_or_age = pet_age_str.strip()

            pet_sex_str = request.POST.get('pet_sex', '').upper()
            if "MALE" in pet_sex_str:
                pet.sex = "MALE"
            elif "FEMALE" in pet_sex_str:
                pet.sex = "FEMALE"

            pet.save()
            updated_record.save()
            messages.success(
                request, f'Record for {record.pet.name} has been updated!')
            return redirect('records:admin_detail', pk=record.pk)
    else:
        form = MedicalRecordForm(instance=record)

    # Build pet details JSON for dynamic form population
    pets = Pet.objects.select_related(
        'owner').all()  # pylint: disable=no-member
    pets_data = {}
    for p in pets:
        last_record = p.medical_records.filter(
            branch__isnull=False
        ).order_by('-date_recorded').first()
        pets_data[p.name] = {
            'owner_name': p.owner.get_full_name() or p.owner.username,
            'owner_address': p.owner.address,
            'owner_contact': p.owner.phone_number,
            'pet_age': p.dob_or_age,
            'pet_color': p.color,
            'pet_species': p.species,
            'pet_breed': p.breed,
            'pet_sex': p.get_sex_display(),
            'branch_id': p.owner.branch_id or (last_record.branch_id if last_record else ''),
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
        messages.success(
            request, f'Medical record for {pet_name} has been deleted.')
        return redirect('records:admin_list')

    return render(request, 'records/admin_confirm_delete.html', {'record': record})


@login_required
def admin_record_detail(request, pk):
    """View to display a medical record card with all its visit entries."""
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("You do not have permission to view this page.")

    record = get_object_or_404(MedicalRecord, pk=pk)
    entries = record.entries.order_by('date_recorded', 'created_at')
    verification_hash = generate_verification_hash(record)
    verify_path = reverse('records:verify', args=[record.pk, verification_hash])
    verify_url = request.build_absolute_uri(verify_path)
    qr_code_base64 = generate_qr_code_base64(verify_url)

    return render(request, 'records/admin_detail.html', {
        'record': record,
        'entries': entries,
        'qr_code_base64': qr_code_base64,
        'verification_hash': verification_hash,
        'generated_date': timezone.now(),
    })


@login_required
def admin_add_entry(request, pk):
    """Add a new visit entry to an existing medical record card."""
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("You do not have permission to view this page.")

    record = get_object_or_404(MedicalRecord, pk=pk)

    if request.method == 'POST':
        form = RecordEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.record = record
            if hasattr(request.user, 'staffmember'):
                entry.vet = request.user.staffmember
            entry.save()
            # Touch the parent record so updated_at changes
            record.save()
            messages.success(
                request, f'New visit entry added to {record.pet.name}\'s record.')
            return redirect('records:admin_detail', pk=record.pk)
    else:
        form = RecordEntryForm(initial={'date_recorded': timezone.now().date()})

    return render(request, 'records/admin_add_entry.html', {
        'form': form,
        'record': record,
    })


@login_required
def admin_entry_edit(request, entry_pk):
    """Edit a specific visit entry."""
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("You do not have permission to view this page.")

    entry = get_object_or_404(RecordEntry, pk=entry_pk)
    record = entry.record

    if request.method == 'POST':
        form = RecordEntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            # Touch the parent record so updated_at changes
            record.save()
            messages.success(request, 'Visit entry updated.')
            return redirect('records:admin_detail', pk=record.pk)
    else:
        form = RecordEntryForm(instance=entry)

    return render(request, 'records/admin_entry_edit.html', {
        'form': form,
        'entry': entry,
        'record': record,
    })


@login_required
def admin_entry_delete(request, entry_pk):
    """Delete a specific visit entry."""
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("You do not have permission to view this page.")

    entry = get_object_or_404(RecordEntry, pk=entry_pk)
    record = entry.record

    if request.method == 'POST':
        entry.delete()
        # Touch the parent record so updated_at changes
        record.save()
        messages.success(request, 'Visit entry deleted.')
        return redirect('records:admin_detail', pk=record.pk)

    return render(request, 'records/admin_entry_confirm_delete.html', {
        'entry': entry,
        'record': record,
    })


def generate_verification_hash(record):
    """
    Generate a unique verification hash for the medical record.
    This can be used to verify authenticity of printed PDFs.
    """
    data = f"{record.pk}-{record.pet.name}-{record.date_recorded}-{record.created_at}"
    return hashlib.sha256(data.encode()).hexdigest()[:12].upper()


def _pdf_link_callback(uri, rel):
    """
    Resolve static file URIs to absolute filesystem paths so xhtml2pdf
    can load CSS/image assets during PDF generation.
    """
    static_url = settings.STATIC_URL  # e.g. 'static/'
    if uri.startswith(static_url):
        relative = uri[len(static_url):]
        path = finders.find(relative)
        if path:
            return path
    return uri


def generate_qr_code_base64(data):
    """
    Generate a QR code image and return as base64 encoded string.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


@login_required
def download_pdf_view(request, pk):
    """
    Generate and download a PDF version of the medical record with QR code.
    """
    record = get_object_or_404(MedicalRecord, pk=pk)

    # Security: Only allow pet's owner or staff to download
    if not request.user.is_staff and record.pet.owner != request.user:
        return HttpResponseForbidden("You do not have permission to download this record.")

    # Generate verification hash and QR code
    verification_hash = generate_verification_hash(record)
    verify_path = reverse('records:verify', args=[record.pk, verification_hash])
    verify_url = request.build_absolute_uri(verify_path)
    qr_code_base64 = generate_qr_code_base64(verify_url)

    # Render HTML template
    html_content = render_to_string('records/pdf_record.html', {
        'record': record,
        'entries': record.entries.order_by('date_recorded', 'created_at'),
        'qr_code_base64': qr_code_base64,
        'verification_hash': verification_hash,
        'generated_date': timezone.now(),
    })

    # Generate PDF using xhtml2pdf
    result = io.BytesIO()
    pdf = pisa.pisaDocument(
        io.BytesIO(html_content.encode('UTF-8')),
        result,
        link_callback=_pdf_link_callback,
    )
    
    if pdf.err:
        return HttpResponse('Error generating PDF', status=500)

    # Create response
    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    filename = f"medical_record_{record.pet.name}_{record.date_recorded}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
def user_record_detail(request, pk):
    """
    User-facing detail view for a single medical record.
    Only accessible by the pet's owner.
    """
    record = get_object_or_404(MedicalRecord, pk=pk)

    if record.pet.owner != request.user:
        return HttpResponseForbidden("You do not have permission to view this record.")

    verification_hash = generate_verification_hash(record)
    verify_path = reverse('records:verify', args=[record.pk, verification_hash])
    verify_url = request.build_absolute_uri(verify_path)
    qr_code_base64 = generate_qr_code_base64(verify_url)

    return render(request, 'records/user_detail.html', {
        'record': record,
        'entries': record.entries.order_by('date_recorded', 'created_at'),
        'qr_code_base64': qr_code_base64,
        'verification_hash': verification_hash,
        'generated_date': timezone.now(),
    })


def verify_record(request, pk, hash):
    """
    Public verification page — no login required.
    Accessed by scanning the QR code on a printed/downloaded record.
    """
    record = get_object_or_404(MedicalRecord, pk=pk)
    expected_hash = generate_verification_hash(record)
    is_valid = (hash.upper() == expected_hash.upper())

    return render(request, 'records/verify.html', {
        'record': record,
        'is_valid': is_valid,
        'hash': hash.upper(),
        'expected_hash': expected_hash,
        'verified_at': timezone.now(),
    })
