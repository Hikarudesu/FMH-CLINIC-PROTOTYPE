import json
from datetime import date, timedelta
import calendar

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from accounts.models import User
from accounts.decorators import role_required
from branches.models import Branch
from .models import StaffMember, VetSchedule, RecurringSchedule
from .forms import StaffMemberForm, VetScheduleForm, RecurringScheduleForm


# ──────────────────────── STAFF MANAGEMENT ────────────────────────

@login_required
@role_required(User.Role.STAFF, User.Role.VETERINARIAN, User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def staff_list(request):
    """List all staff members with search/filter."""
    staff = StaffMember.objects.select_related('branch').all()

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        staff = staff.filter(
            models_Q(first_name__icontains=q) |
            models_Q(last_name__icontains=q) |
            models_Q(email__icontains=q)
        )

    # Branch filter
    branch_id = request.GET.get('branch', '')
    if branch_id:
        staff = staff.filter(branch_id=branch_id)

    # Position filter
    position = request.GET.get('position', '')
    if position:
        staff = staff.filter(position=position)

    branches = Branch.objects.filter(is_active=True)

    return render(request, 'employees/staff_list.html', {
        'staff': staff,
        'branches': branches,
        'positions': StaffMember.Position.choices,
        'q': q,
        'selected_branch': branch_id,
        'selected_position': position,
    })


def models_Q(*args, **kwargs):
    """Shortcut for Q objects."""
    from django.db.models import Q
    return Q(*args, **kwargs)


@login_required
@role_required(User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def staff_add(request):
    """Add a new staff member."""
    if request.method == 'POST':
        form = StaffMemberForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff member added successfully.')
            return redirect('employees:staff_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StaffMemberForm()

    return render(request, 'employees/staff_form.html', {
        'form': form,
        'action': 'Add',
    })


@login_required
@role_required(User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def staff_edit(request, pk):
    """Edit an existing staff member."""
    member = get_object_or_404(StaffMember, pk=pk)

    if request.method == 'POST':
        form = StaffMemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(
                request, f'{member.full_name} updated successfully.')
            return redirect('employees:staff_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StaffMemberForm(instance=member)

    return render(request, 'employees/staff_form.html', {
        'form': form,
        'action': 'Edit',
        'member': member,
    })


@login_required
@role_required(User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def staff_delete(request, pk):
    """Soft-delete a staff member — deactivate and optionally reassign appointments."""
    member = get_object_or_404(StaffMember, pk=pk)

    # Get future appointments assigned to this vet
    from appointments.models import Appointment
    future_appointments = Appointment.objects.filter(
        preferred_vet=member,
        appointment_date__gte=date.today(),
    ).exclude(status__in=['CANCELLED', 'COMPLETED'])

    # Get available vets for reassignment (same branch, excluding current)
    reassign_vets = StaffMember.objects.filter(
        position=StaffMember.Position.VETERINARIAN,
        is_active=True,
        branch=member.branch,
    ).exclude(pk=pk) if member.is_vet else StaffMember.objects.none()

    if request.method == 'POST':
        action = request.POST.get('action', 'deactivate')
        reassign_to_id = request.POST.get('reassign_to', '')

        if action == 'deactivate':
            # Reassign appointments if a vet was selected
            if reassign_to_id and future_appointments.exists():
                reassign_vet = get_object_or_404(
                    StaffMember, pk=reassign_to_id)
                count = future_appointments.update(preferred_vet=reassign_vet)
                messages.info(
                    request, f'{count} appointment(s) reassigned to {reassign_vet.full_name}.')
            elif future_appointments.exists():
                # No reassignment — set preferred_vet to None
                future_appointments.update(preferred_vet=None)
                messages.info(
                    request, f'{future_appointments.count()} appointment(s) set to "Any available vet".')

            # Soft-delete: deactivate instead of hard delete
            member.is_active = False
            member.save(update_fields=['is_active'])
            messages.success(
                request, f'{member.full_name} has been deactivated.')
        else:
            # Hard delete (only if user explicitly chose)
            name = member.full_name
            member.delete()
            messages.success(request, f'{name} has been permanently removed.')

        return redirect('employees:staff_list')

    return render(request, 'employees/staff_delete.html', {
        'member': member,
        'future_appointments': future_appointments,
        'reassign_vets': reassign_vets,
    })


# ──────────────────────── SCHEDULE CALENDAR ────────────────────────

@login_required
@role_required(User.Role.STAFF, User.Role.VETERINARIAN, User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def schedule_view(request):
    """Schedule calendar page."""
    branches = Branch.objects.filter(is_active=True)
    form = VetScheduleForm()
    recurring_form = RecurringScheduleForm()

    recurring_schedules = RecurringSchedule.objects.filter(
        is_active=True
    ).select_related('staff', 'branch')

    return render(request, 'employees/schedule.html', {
        'branches': branches,
        'form': form,
        'recurring_form': recurring_form,
        'recurring_schedules': recurring_schedules,
        'shift_types': VetSchedule.ShiftType.choices,
    })


@login_required
def schedule_api(request):
    """JSON API — returns schedule entries for a given month/branch."""
    year = int(request.GET.get('year', date.today().year))
    month = int(request.GET.get('month', date.today().month))
    branch_id = request.GET.get('branch', '')

    # Get first and last day of month
    _, last_day = calendar.monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, last_day)

    schedules = VetSchedule.objects.filter(
        date__gte=start,
        date__lte=end,
    ).select_related('staff', 'branch')

    if branch_id:
        schedules = schedules.filter(branch_id=branch_id)

    events = []
    for s in schedules:
        events.append({
            'id': s.id,
            'staffName': s.staff.full_name,
            'staffId': s.staff.id,
            'staffPosition': s.staff.get_position_display(),
            'date': s.date.isoformat(),
            'startTime': s.start_time.strftime('%H:%M'),
            'endTime': s.end_time.strftime('%H:%M'),
            'branch': s.branch.name if s.branch else '',
            'isAvailable': s.is_available,
            'shiftType': s.shift_type,
            'shiftTypeDisplay': s.get_shift_type_display(),
            'notes': s.notes,
        })

    return JsonResponse({'events': events, 'year': year, 'month': month})


@login_required
@role_required(User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def schedule_add(request):
    """Add a schedule entry or recurring template (POST only)."""
    if request.method == 'POST':
        is_recurring = request.POST.get('is_recurring') == 'on'

        if is_recurring:
            form = RecurringScheduleForm(request.POST)
            if form.is_valid():
                selected_days = form.cleaned_data['days_of_week']
                created_entries = []

                for day in selected_days:
                    entry = RecurringSchedule(
                        staff=form.cleaned_data['staff'],
                        branch=form.cleaned_data['branch'],
                        day_of_week=int(day),
                        start_time=form.cleaned_data['start_time'],
                        end_time=form.cleaned_data['end_time'],
                        shift_type=form.cleaned_data.get(
                            'shift_type', 'GENERAL'),
                        is_active=True,
                        effective_from=form.cleaned_data.get('effective_from'),
                        effective_until=form.cleaned_data.get(
                            'effective_until'),
                    )
                    entry.save()  # triggers auto-generation via save() override
                    created_entries.append(entry.get_day_of_week_display())

                day_names = ', '.join(created_entries)
                messages.success(
                    request,
                    f'Recurring template(s) added for {form.cleaned_data["staff"].full_name} '
                    f'on {day_names}. Auto-generated schedule entries for the next 30 days.'
                )
            else:
                error_details = '; '.join(
                    f'{field}: {", ".join(errs)}' for field, errs in form.errors.items()
                )
                messages.error(
                    request, f'Could not add recurring template — {error_details}')
        else:
            form = VetScheduleForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Schedule entry added.')
            else:
                messages.error(
                    request, 'Invalid schedule data. Please check the form.')
    return redirect('employees:schedule')


@login_required
@role_required(User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def schedule_edit(request, pk):
    """Edit an existing schedule entry."""
    entry = get_object_or_404(VetSchedule, pk=pk)
    if request.method == 'POST':
        entry.is_available = request.POST.get('is_available') == 'on'
        entry.shift_type = request.POST.get('shift_type', entry.shift_type)
        entry.notes = request.POST.get('notes', entry.notes)

        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        if start_time:
            entry.start_time = start_time
        if end_time:
            entry.end_time = end_time

        entry.save()
        messages.success(request, 'Schedule entry updated.')
    return redirect('employees:schedule')


@login_required
@role_required(User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def schedule_delete(request, pk):
    """Delete a schedule entry."""
    entry = get_object_or_404(VetSchedule, pk=pk)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, 'Schedule entry removed.')
    return redirect('employees:schedule')


@login_required
@role_required(User.Role.ADMIN)
def schedule_clear_all(request):
    """Delete ALL VetSchedule entries. Admin only."""
    if request.method == 'POST':
        qs = VetSchedule.objects.all()
        count = qs.count()
        qs.delete()
        messages.success(
            request, f'All {count} schedule entries have been deleted.')
    return redirect('employees:schedule')


# ──────────────────────── RECURRING SCHEDULES ────────────────────────

@login_required
@role_required(User.Role.STAFF, User.Role.VETERINARIAN, User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def recurring_list(request):
    """JSON API — returns all active recurring schedules."""
    schedules = RecurringSchedule.objects.filter(
        is_active=True
    ).select_related('staff', 'branch')

    data = []
    for rs in schedules:
        data.append({
            'id': rs.id,
            'staffName': rs.staff.full_name,
            'branch': rs.branch.name,
            'dayOfWeek': rs.get_day_of_week_display(),
            'startTime': rs.start_time.strftime('%H:%M'),
            'endTime': rs.end_time.strftime('%H:%M'),
            'shiftType': rs.get_shift_type_display(),
        })
    return JsonResponse({'schedules': data})


@login_required
@role_required(User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def recurring_add(request):
    """Add recurring schedule templates — supports multiple days at once."""
    if request.method == 'POST':
        form = RecurringScheduleForm(request.POST)
        if form.is_valid():
            # list of day ints
            selected_days = form.cleaned_data['days_of_week']
            created_entries = []

            for day in selected_days:
                entry = RecurringSchedule(
                    staff=form.cleaned_data['staff'],
                    branch=form.cleaned_data['branch'],
                    day_of_week=int(day),
                    start_time=form.cleaned_data['start_time'],
                    end_time=form.cleaned_data['end_time'],
                    shift_type=form.cleaned_data.get('shift_type', 'GENERAL'),
                    is_active=True,
                    effective_from=form.cleaned_data.get('effective_from'),
                    effective_until=form.cleaned_data.get('effective_until'),
                )
                entry.save()  # triggers auto-generation via save() override
                created_entries.append(entry.get_day_of_week_display())

            day_names = ', '.join(created_entries)
            messages.success(
                request,
                f'Recurring template(s) added for {form.cleaned_data["staff"].full_name} '
                f'on {day_names}. Auto-generated schedule entries for the next 30 days.'
            )
        else:
            error_details = '; '.join(
                f'{field}: {", ".join(errs)}' for field, errs in form.errors.items()
            )
            messages.error(
                request, f'Could not add recurring template — {error_details}')
    return redirect('employees:schedule')


@login_required
@role_required(User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def recurring_delete(request, pk):
    """Delete a recurring schedule template."""
    entry = get_object_or_404(RecurringSchedule, pk=pk)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, 'Recurring schedule template removed.')
    return redirect('employees:schedule')
