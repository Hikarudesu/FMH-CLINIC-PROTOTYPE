"""Views for managing appointments, availability, and scheduling."""
import calendar as cal_mod
from datetime import date, timedelta, datetime, time

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Q

from accounts.models import User
from accounts.decorators import role_required
from branches.models import Branch
from employees.models import StaffMember, VetSchedule
from notifications.models import FollowUp, Notification
from patients.models import Pet
from .models import Appointment
from .forms import PublicAppointmentForm, PortalAppointmentForm, AdminQuickCreateForm, AppointmentEditForm


# ──────────────────────── AVAILABILITY ENGINE ────────────────────────

def get_available_slots(vet_id=None, target_date=None, branch_id=None):
    """
    Core availability engine.
    Returns a list of available time slots checking both VetSchedule and existing Appointments.

    If vet_id is provided, returns slots for that specific vet.
    If vet_id is None, returns all slots across any scheduled vet.
    """
    if not target_date:
        return []

    # Get schedule entries for this date
    filters = {
        'date': target_date,
        'is_available': True,
    }
    if vet_id:
        filters['staff_id'] = vet_id
    if branch_id:
        filters['branch_id'] = branch_id

    schedules = VetSchedule.objects.filter(
        **filters).select_related('staff', 'branch')

    # Get existing appointments for this date (optimized query)
    appt_filters = {'appointment_date': target_date}
    if branch_id:
        appt_filters['branch_id'] = branch_id

    existing_appointments = Appointment.objects.filter(
        **appt_filters
    ).exclude(
        status__in=['CANCELLED']
    ).select_related('preferred_vet')

    slots = []
    for sched in schedules:
        # Generate 30-minute slots within the schedule window
        current = datetime.combine(target_date, sched.start_time)
        end = datetime.combine(target_date, sched.end_time)
        slot_duration = timedelta(minutes=30)

        while current + slot_duration <= end:
            slot_time = current.time()
            slot_end_time = (current + slot_duration).time()

            # Skip 12:00 PM - 1:00 PM system-wide lunch block
            if time(12, 0) <= slot_time < time(13, 0) or time(12, 0) < slot_end_time <= time(13, 0):
                current += timedelta(minutes=60)
                continue

            # Check if this specific slot is already booked for this vet
            slot_booked = existing_appointments.filter(
                preferred_vet=sched.staff,
                appointment_time=slot_time,
            ).exists()

            slots.append({
                'time': slot_time.strftime('%H:%M'),
                'label': f"{slot_time.strftime('%I:%M %p')} – {slot_end_time.strftime('%I:%M %p')}",
                'start_label': slot_time.strftime('%I:%M %p'),
                'end_label': slot_end_time.strftime('%I:%M %p'),
                'vet_id': sched.staff.id,
                'vet_name': sched.staff.full_name,
                'shift_type': sched.get_shift_type_display(),
                'available': not slot_booked,
                'booked_label': 'Appointed already' if slot_booked else '',
            })

            # Gap-Tooth increment: 30 minutes for slot + 30 minutes for break = 60 minutes
            current += timedelta(minutes=60)

    # Deduplicate by time if no specific vet (any vet available)
    if not vet_id:
        time_map = {}
        for slot in slots:
            t = slot['time']
            if t not in time_map:
                time_map[t] = slot
            else:
                # If ANY vet is available at this time, mark the slot as available
                if slot['available']:
                    time_map[t] = slot
        slots = sorted(time_map.values(), key=lambda s: s['time'])
    else:
        slots = sorted(slots, key=lambda s: s['time'])

    return slots


# ──────────────────────── PUBLIC BOOKING (no login) ────────────────────────

def public_book(request):
    """Public appointment booking — no login required."""
    # Cleanup expired appointments on page load
    Appointment.cleanup_expired()

    if request.method == 'POST':
        form = PublicAppointmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Your appointment has been booked successfully! We will contact you to confirm.'
            )
            return redirect('appointments:book_success')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PublicAppointmentForm()

    branches = Branch.objects.filter(is_active=True)
    return render(request, 'appointments/book_public.html', {
        'form': form,
        'branches': branches,
    })


def book_success(request):
    """Success page after booking."""
    return render(request, 'appointments/book_success.html')


# ──────────────────────── PORTAL BOOKING (logged-in) ────────────────────────

@login_required
def portal_book(request):
    """Logged-in user appointment booking."""
    Appointment.cleanup_expired()

    if request.method == 'POST':
        form = PortalAppointmentForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(
                request, 'Your appointment has been booked successfully!')
            return redirect('appointments:my_appointments')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PortalAppointmentForm(user=request.user)

    branches = Branch.objects.filter(is_active=True)
    user_pets = request.user.pets.all() if hasattr(request.user, 'pets') else []

    return render(request, 'appointments/book_portal.html', {
        'form': form,
        'branches': branches,
        'user_pets': user_pets,
    })


@login_required
def my_appointments(request):
    """Show the logged-in user's appointments and follow-ups with tabbed data."""
    # Base query for appointments
    base_appts = Appointment.objects.filter(
        user=request.user).select_related('branch', 'preferred_vet')

    # Categorized queries
    pending_appts = base_appts.filter(status=Appointment.Status.PENDING)
    confirmed_appts = base_appts.filter(status=Appointment.Status.CONFIRMED)
    completed_appts = base_appts.filter(status=Appointment.Status.COMPLETED)
    cancelled_appts = base_appts.filter(status=Appointment.Status.CANCELLED)

    # Categorized queries
    follow_ups = FollowUp.objects.filter(
        appointment__user=request.user
    ).select_related('appointment')

    context = {
        'pending_appts': pending_appts,
        'confirmed_appts': confirmed_appts,
        'completed_appts': completed_appts,
        'cancelled_appts': cancelled_appts,
        'follow_ups': follow_ups,
    }
    return render(request, 'appointments/appointments_user.html', context)


# ──────────────────────── AJAX API ENDPOINTS ────────────────────────

@require_GET
def api_available_vets(request):
    """Return available vets for a given branch and date."""
    branch_id = request.GET.get('branch')
    appt_date = request.GET.get('date')

    if not branch_id:
        return JsonResponse({'vets': []})

    # Get all vets assigned to this branch
    vets = StaffMember.objects.filter(
        position=StaffMember.Position.VETERINARIAN,
        is_active=True,
        branch_id=branch_id,
    )

    # If a date is provided, filter to only vets who have a schedule that day
    if appt_date:
        scheduled_staff_ids = VetSchedule.objects.filter(
            branch_id=branch_id,
            date=appt_date,
            is_available=True,
        ).values_list('staff_id', flat=True)

        # Include vets that either have a schedule or are assigned to the branch
        # (if no schedules exist yet, show all branch vets)
        if scheduled_staff_ids.exists():
            vets = vets.filter(id__in=scheduled_staff_ids)

    data = [{'id': v.id, 'name': v.full_name} for v in vets]
    return JsonResponse({'vets': data})


@require_GET
def api_vet_times(request):
    """Return available time slots for a vet on a given date using the availability engine."""
    vet_id = request.GET.get('vet')
    appt_date = request.GET.get('date')
    branch_id = request.GET.get('branch')

    if not appt_date:
        return JsonResponse({'times': []})

    try:
        target_date = date.fromisoformat(appt_date)
    except ValueError:
        return JsonResponse({'times': []})

    slots = get_available_slots(
        vet_id=int(vet_id) if vet_id else None,
        target_date=target_date,
        branch_id=int(branch_id) if branch_id else None,
    )

    return JsonResponse({'times': slots})


@require_GET
def api_available_dates(request):
    """Return dates where a specific vet has schedule entries for a given month.
    Used for greying out unavailable dates in the booking calendar."""
    vet_id = request.GET.get('vet')
    year = request.GET.get('year')
    month = request.GET.get('month')
    branch_id = request.GET.get('branch')

    if not (vet_id and year and month):
        return JsonResponse({'dates': []})

    try:
        year = int(year)
        month = int(month)
    except (ValueError, TypeError):
        return JsonResponse({'dates': []})

    _, last_day = cal_mod.monthrange(year, month)

    filters = {
        'staff_id': vet_id,
        'date__gte': date(year, month, 1),
        'date__lte': date(year, month, last_day),
        'is_available': True,
    }
    if branch_id:
        filters['branch_id'] = branch_id

    available_dates = VetSchedule.objects.filter(
        **filters
    ).values_list('date', flat=True).distinct()

    return JsonResponse({
        'dates': [d.isoformat() for d in available_dates],
        'year': year,
        'month': month,
    })


# ──────────────────────── ADMIN — APPOINTMENT MANAGEMENT ────────────────────────

@login_required
@role_required(User.Role.STAFF, User.Role.VETERINARIAN, User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def admin_list(request):
    """Admin view: list all appointments with filters + calendar support."""
    Appointment.cleanup_expired()

    appointments = Appointment.objects.select_related(
        'branch', 'preferred_vet', 'user').all()

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        appointments = appointments.filter(
            Q(owner_name__icontains=q) |
            Q(pet_name__icontains=q) |
            Q(owner_email__icontains=q)
        )

    # Status filter
    status = request.GET.get('status', '')
    if status:
        appointments = appointments.filter(status=status)

    # Branch filter
    branch_id = request.GET.get('branch', '')
    if branch_id:
        appointments = appointments.filter(branch_id=branch_id)

    # Source filter
    source = request.GET.get('source', '')
    if source:
        appointments = appointments.filter(source=source)

    # Vet filter
    vet_id = request.GET.get('vet', '')
    if vet_id:
        appointments = appointments.filter(preferred_vet_id=vet_id)
    
    # View parameter (table, daily, weekly, monthly)
    current_view = request.GET.get('view', 'table')

    branches = Branch.objects.filter(is_active=True)
    vets = StaffMember.objects.filter(
        position=StaffMember.Position.VETERINARIAN,
        is_active=True,
    )
    quick_form = AdminQuickCreateForm()

    return render(request, 'appointments/admin_list.html', {
        'appointments': appointments,
        'branches': branches,
        'vets': vets,
        'statuses': Appointment.Status.choices,
        'sources': Appointment.Source.choices,
        'q': q,
        'selected_status': status,
        'selected_branch': branch_id,
        'selected_source': source,
        'selected_vet': vet_id,
        'current_view': current_view,
        'quick_form': quick_form,
    })


@login_required
@role_required(User.Role.STAFF, User.Role.VETERINARIAN, User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def admin_calendar_api(request):
    """JSON API — returns appointments for calendar rendering with filters."""
    year = int(request.GET.get('year', date.today().year))
    month = int(request.GET.get('month', date.today().month))

    _, last_day = cal_mod.monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, last_day)

    appointments = Appointment.objects.filter(
        appointment_date__gte=start,
        appointment_date__lte=end,
    ).select_related('branch', 'preferred_vet').exclude(status='CANCELLED')

    # Apply filters
    branch_id = request.GET.get('branch')
    if branch_id:
        appointments = appointments.filter(branch_id=branch_id)

    vet_id = request.GET.get('vet')
    if vet_id:
        appointments = appointments.filter(preferred_vet_id=vet_id)

    status = request.GET.get('status')
    if status:
        appointments = appointments.filter(status=status)

    events = []
    for a in appointments:
        events.append({
            'id': a.id,
            'petName': a.pet_name or '',
            'petBreed': a.pet_breed or '',
            'petSpecies': a.pet_symptoms or 'Unknown',
            'ownerName': a.owner_name or '',
            'ownerEmail': a.owner_email or '',
            'date': (
                getattr(a, 'appointment_date').isoformat()
                if getattr(a, 'appointment_date', None) else ''
            ),
            'time': (
                getattr(a, 'appointment_time').strftime('%H:%M')
                if getattr(a, 'appointment_time', None) else ''
            ),
            'timeLabel': (
                getattr(a, 'appointment_time').strftime('%I:%M %p')
                if getattr(a, 'appointment_time', None) else ''
            ),
            'branch': a.branch.name if getattr(a, 'branch', None) else '',
            'vetName': a.preferred_vet.full_name if getattr(a, 'preferred_vet', None) else 'Any',
            'vetId': a.preferred_vet.id if getattr(a, 'preferred_vet', None) else 0,
            'status': getattr(a, 'status', ''),
            'statusDisplay': (
                dict(Appointment.Status.choices).get(a.status, a.status)
                if hasattr(Appointment, 'Status') else getattr(a, 'status', '')
            ),
            'source': getattr(a, 'source', ''),
            'reason': (
                dict(Appointment.Reason.choices).get(a.reason, a.reason)
                if hasattr(Appointment, 'Reason') else getattr(a, 'reason', '')
            ),
            'notes': getattr(a, 'notes', ''),
            'createdAt': (
                a.created_at.strftime('%b %d, %Y, %I:%M %p')
                if getattr(a, 'created_at', None) else ''
            )
        })

    return JsonResponse({'events': events, 'year': year, 'month': month})


@login_required
@role_required(User.Role.STAFF, User.Role.VETERINARIAN, User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def admin_quick_create(request):
    """Admin: quickly create an appointment (walk-in / phone call)."""
    if request.method == 'POST':
        form = AdminQuickCreateForm(request.POST)
        if form.is_valid():
            appointment = form.save()
            
            # Notify user if appointment is confirmed and has a linked user
            if appointment.status == 'CONFIRMED' and appointment.user:
                Notification.objects.create(
                    user=appointment.user,
                    title=f'Appointment Confirmed for {appointment.pet_name}',
                    message=(
                        f'Great news! Your appointment for {appointment.pet_name} '
                        f'has been confirmed for {appointment.appointment_date.strftime("%B %d, %Y")} '
                        f'at {appointment.appointment_time.strftime("%I:%M %p")}. '
                        f'Location: {appointment.branch.name}.'
                    ),
                    notification_type='APPOINTMENT',
                )
            
            # Handle follow-up creation
            follow_up_enabled = request.POST.get('follow_up_enabled')
            if follow_up_enabled == 'on':
                follow_up_date = request.POST.get('follow_up_date')
                follow_up_end_date = request.POST.get('follow_up_end_date')
                follow_up_reason = request.POST.get('follow_up_reason', '')
                if follow_up_date:
                    followup = FollowUp.objects.create(
                        appointment=appointment,
                        pet_name=appointment.pet_name,
                        follow_up_date=follow_up_date,
                        follow_up_end_date=follow_up_end_date if follow_up_end_date else None,
                        reason=follow_up_reason,
                        created_by=request.user,
                    )

                    # Format date string for notification
                    date_str = str(follow_up_date)
                    if follow_up_end_date and follow_up_end_date != follow_up_date:
                        date_str = f"{follow_up_date} to {follow_up_end_date}"

                    # Create notification for the appointment owner
                    if appointment.user:
                        Notification.objects.create(
                            user=appointment.user,
                            title=f'Follow-up Scheduled for {appointment.pet_name}',
                            message=(
                                f'A follow-up visit has been scheduled for {appointment.pet_name} '
                                f'from {date_str}. Reason: {follow_up_reason or "Routine follow-up"}'
                            ),
                            notification_type='FOLLOW_UP',
                            related_follow_up=followup,
                        )
            
            messages.success(request, 'Appointment created successfully.')
        else:
            messages.error(
                request, 'Invalid appointment data. Please check the form.')
    return redirect('appointments:admin_list')


@login_required
@role_required(User.Role.STAFF, User.Role.VETERINARIAN, User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def admin_edit(request, pk):
    """Admin view: edit an appointment with follow-up support."""
    appointment = get_object_or_404(Appointment, pk=pk)

    if request.method == 'POST':
        # Capture original status before update
        original_status = appointment.status
        
        form = AppointmentEditForm(request.POST, instance=appointment)
        if form.is_valid():
            updated_appointment = form.save()
            
            # Check if status changed and notify user
            if updated_appointment.status != original_status and updated_appointment.user:
                status_notifications = {
                    'CONFIRMED': {
                        'title': f'Appointment Confirmed for {updated_appointment.pet_name}',
                        'message': (
                            f'Great news! Your appointment for {updated_appointment.pet_name} '
                            f'has been confirmed for {updated_appointment.appointment_date.strftime("%B %d, %Y")} '
                            f'at {updated_appointment.appointment_time.strftime("%I:%M %p")}. '
                            f'Location: {updated_appointment.branch.name}.'
                        ),
                    },
                    'COMPLETED': {
                        'title': f'Appointment Completed for {updated_appointment.pet_name}',
                        'message': (
                            f'The appointment for {updated_appointment.pet_name} '
                            f'on {updated_appointment.appointment_date.strftime("%B %d, %Y")} '
                            f'has been marked as completed. Thank you for visiting us!'
                        ),
                    },
                    'CANCELLED': {
                        'title': f'Appointment Cancelled for {updated_appointment.pet_name}',
                        'message': (
                            f'Your appointment for {updated_appointment.pet_name} '
                            f'scheduled on {updated_appointment.appointment_date.strftime("%B %d, %Y")} '
                            f'at {updated_appointment.appointment_time.strftime("%I:%M %p")} '
                            f'has been cancelled. Please contact us if you have any questions.'
                        ),
                    },
                }
                
                notification_data = status_notifications.get(updated_appointment.status)
                if notification_data:
                    Notification.objects.create(
                        user=updated_appointment.user,
                        title=notification_data['title'],
                        message=notification_data['message'],
                        notification_type='APPOINTMENT',
                    )

            # Handle follow-up creation
            follow_up_enabled = request.POST.get('follow_up_enabled')
            if follow_up_enabled == 'on':
                follow_up_date = request.POST.get('follow_up_date')
                follow_up_end_date = request.POST.get('follow_up_end_date')
                follow_up_reason = request.POST.get('follow_up_reason', '')
                if follow_up_date:
                    followup = FollowUp.objects.create(
                        appointment=updated_appointment,
                        pet_name=updated_appointment.pet_name,
                        follow_up_date=follow_up_date,
                        follow_up_end_date=follow_up_end_date if follow_up_end_date else None,
                        reason=follow_up_reason,
                        created_by=request.user,
                    )

                    # Format date string for notification
                    date_str = str(follow_up_date)
                    if follow_up_end_date and follow_up_end_date != follow_up_date:
                        date_str = f"{follow_up_date} to {follow_up_end_date}"

                    # Create notification for the appointment owner
                    if updated_appointment.user:
                        Notification.objects.create(
                            user=updated_appointment.user,
                            title=f'Follow-up Scheduled for {updated_appointment.pet_name}',
                            message=(
                                f'A follow-up visit has been scheduled for {updated_appointment.pet_name} '
                                f'from {date_str}. Reason: {follow_up_reason or "Routine follow-up"}'
                            ),
                            notification_type='FOLLOW_UP',
                            related_follow_up=followup,
                        )
                    messages.info(
                        request, f'Follow-up scheduled from {date_str}.')

            messages.success(
                request, f'Appointment for {updated_appointment.pet_name} updated.')
            return redirect('appointments:admin_list')
    else:
        form = AppointmentEditForm(instance=appointment)

    # Get existing follow-ups for this appointment
    follow_ups = FollowUp.objects.filter(
        appointment=appointment).order_by('-created_at')
    
    # Get user's pets if appointment has a linked user
    user_pets = []
    if appointment.user:
        user_pets = Pet.objects.filter(owner=appointment.user)

    return render(request, 'appointments/admin_edit.html', {
        'appointment': appointment,
        'form': form,
        'statuses': Appointment.Status.choices,
        'follow_ups': follow_ups,
        'user_pets': user_pets,
    })


@login_required
@role_required(User.Role.STAFF, User.Role.VETERINARIAN, User.Role.BRANCH_ADMIN, User.Role.ADMIN)
@require_POST
def admin_delete(request, pk):
    """Admin view: delete an appointment."""
    appointment = get_object_or_404(Appointment, pk=pk)
    name = appointment.pet_name
    appointment.delete()
    messages.success(request, f'Appointment for {name} has been deleted.')
    return redirect('appointments:admin_list')


@login_required
@role_required(User.Role.STAFF, User.Role.VETERINARIAN, User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def api_pet_owners(request):
    """API: return list of registered pet owners for admin dropdown."""
    from patients.models import Pet
    # Only return users who have at least one pet
    owners = User.objects.filter(
        role=User.Role.PET_OWNER,
        pets__isnull=False
    ).distinct().order_by('first_name', 'last_name', 'username')

    data = []
    for owner in owners:
        full_name = owner.get_full_name() or owner.username
        data.append({
            'id': owner.id,
            'name': full_name,
            'email': owner.email or '',
            'phone': owner.phone_number or '',
            'address': owner.address or '',
        })
    return JsonResponse({'owners': data})


@login_required
@role_required(User.Role.STAFF, User.Role.VETERINARIAN, User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def api_owner_pets(request):
    """API: return list of pets for a specific owner."""
    from patients.models import Pet
    owner_id = request.GET.get('owner_id')
    if not owner_id:
        return JsonResponse({'pets': []})

    try:
        owner = User.objects.get(pk=owner_id)
    except User.DoesNotExist:
        return JsonResponse({'pets': []})

    pets = Pet.objects.filter(owner=owner).order_by('name')
    data = []
    for pet in pets:
        # Return age as text string
        dob_text = f'{pet.age} years' if pet.age else ''
        data.append({
            'id': pet.id,
            'name': pet.name,
            'species': pet.species or '',
            'breed': pet.breed or '',
            'dob': dob_text,
            'sex': pet.sex or '',
            'color': pet.color or '',
        })
    return JsonResponse({'pets': data})
