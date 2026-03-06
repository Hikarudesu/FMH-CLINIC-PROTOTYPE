"""
Views for managing patient (pet) profiles and displaying their data.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from records.models import MedicalRecord
from .models import Pet
from .forms import PetForm, AdminPetForm


@login_required
def admin_list_view(request):
    """Admin view to see all registered patients in the system."""
    # pylint: disable=no-member
    if not (request.user.is_superuser or request.user.is_staff or hasattr(request.user, 'staffmember')):
        # Redirect standard users attempting to access the admin patient list
        return redirect('user_dashboard')

    query = request.GET.get('q', '')
    if query:
        from django.db.models import Q
        pets = Pet.objects.filter(
            Q(name__icontains=query) |
            Q(owner__first_name__icontains=query) |
            Q(owner__last_name__icontains=query) |
            Q(owner__username__icontains=query)
        ).select_related('owner')
    else:
        pets = Pet.objects.select_related('owner').all().order_by('-id')

    return render(request, 'patients/admin_list.html', {
        'pets': pets,
        'search_query': query
    })


@login_required
def my_pets_view(request):
    """List all pets belonging to the logged-in user, along with their medical records."""
    # pylint: disable=no-member
    pets = Pet.objects.filter(owner=request.user)
    medical_records = MedicalRecord.objects.filter(
        pet__owner=request.user
    ).order_by('-date_recorded')
    return render(
        request,
        'patients/my_pets.html',
        {'pets': pets, 'medical_records': medical_records}
    )


@login_required
def add_pet_view(request):
    """Add a new pet for the logged-in user."""
    if request.method == 'POST':
        form = PetForm(request.POST)
        if form.is_valid():
            pet = form.save(commit=False)
            pet.owner = request.user
            pet.save()
            messages.success(request, f'{pet.name} has been registered!')
            return redirect('patients:my_pets')
    else:
        form = PetForm()
    return render(request, 'patients/pet_form.html', {'form': form, 'action': 'Register'})


@login_required
def admin_add_pet_view(request):
    """Add a new pet for any user from the Admin portal."""
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('user_dashboard')

    if request.method == 'POST':
        form = AdminPetForm(request.POST)
        if form.is_valid():
            pet = form.save()
            messages.success(
                request, f'{pet.name} has been registered to {pet.owner}!')
            return redirect('patients:admin_list')
    else:
        form = AdminPetForm()
    return render(request, 'patients/admin_pet_form.html', {'form': form, 'action': 'Register'})


@login_required
def edit_pet_view(request, pk):
    """Edit an existing pet (user portal)."""
    pet = get_object_or_404(Pet, pk=pk, owner=request.user)

    if request.method == 'POST':
        form = PetForm(request.POST, instance=pet)
        if form.is_valid():
            form.save()
            messages.success(request, f'{pet.name} has been updated!')
            return redirect('patients:my_pets')
    else:
        form = PetForm(instance=pet)
    return render(request, 'patients/pet_form.html', {'form': form, 'action': 'Update', 'pet': pet})


@login_required
def admin_edit_pet_view(request, pk):
    """Edit an existing pet from the Admin portal."""
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('user_dashboard')

    pet = get_object_or_404(Pet, pk=pk)

    if request.method == 'POST':
        form = AdminPetForm(request.POST, instance=pet)
        if form.is_valid():
            form.save()
            messages.success(request, f'{pet.name} has been updated!')
            return redirect('patients:admin_list')
    else:
        form = AdminPetForm(instance=pet)
    return render(request, 'patients/admin_pet_edit_form.html', {'form': form, 'pet': pet})


@login_required
def delete_pet_view(request, pk):
    """Delete a pet (user portal)."""
    pet = get_object_or_404(Pet, pk=pk, owner=request.user)

    if request.method == 'POST':
        name = pet.name
        pet.delete()
        messages.success(request, f'{name} has been removed.')
        return redirect('patients:my_pets')
    return render(request, 'patients/pet_confirm_delete.html', {'pet': pet})


@login_required
def admin_delete_pet_view(request, pk):
    """Delete a pet from the Admin portal."""
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('user_dashboard')

    pet = get_object_or_404(Pet, pk=pk)

    if request.method == 'POST':
        name = pet.name
        pet.delete()
        messages.success(request, f'{name} has been removed.')
        return redirect('patients:admin_list')
    return render(request, 'patients/admin_pet_confirm_delete.html', {'pet': pet})
