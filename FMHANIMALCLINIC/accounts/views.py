"""Views for the accounts app."""
# pylint: disable=no-member,import-outside-toplevel

from datetime import date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from branches.models import Branch
from .models import User
from .decorators import role_required
from .forms import PetOwnerRegistrationForm


def login_view(request):
    """Login page — redirects to correct portal after login."""
    next_url = request.GET.get('next') or request.POST.get('next')

    if request.user.is_authenticated:
        if next_url:
            return redirect(next_url)
        if request.user.is_clinic_staff():
            return redirect('admin_dashboard')
        return redirect('user_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, 'Successfully logged in.')

            if next_url:
                return redirect(next_url)
            if user.is_clinic_staff():
                return redirect('admin_dashboard')
            return redirect('user_dashboard')
        else:
            messages.error(request, 'Invalid username or password')

    return render(request, 'accounts/login.html')


def register_view(request):
    """Register page view for Pet Owner registration"""
    if request.method == 'POST':
        form = PetOwnerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Auto-login after registration
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('select_branch')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PetOwnerRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def select_branch_view(request):
    """Branch selection page — shown after pet owner registration."""
    branches = Branch.objects.filter(is_active=True)

    if request.method == 'POST':
        branch_id = request.POST.get('branch_id')
        if branch_id:
            branch = get_object_or_404(Branch, id=branch_id, is_active=True)
            request.user.branch = branch
            request.user.save(update_fields=['branch'])
            messages.success(
                request, f'Welcome! You are now registered at {branch.name}.')
        return redirect('user_dashboard')

    return render(request, 'accounts/select_branch.html', {'branches': branches})


def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('landing_page')


@login_required
@role_required(User.Role.PET_OWNER)
def user_dashboard_view(request):
    """User portal dashboard with follow-ups, appointments, and notifications."""
    from notifications.models import FollowUp, Notification
    from appointments.models import Appointment

    today = date.today()

    # Pet count
    pet_count = request.user.pets.count()

    # Upcoming appointments (next 7 days)
    upcoming_appointments = Appointment.objects.filter(
        user=request.user,
        appointment_date__gte=today,
        appointment_date__lte=today + timedelta(days=7),
    ).exclude(status='CANCELLED').select_related(
        'branch', 'preferred_vet'
    ).order_by('appointment_date', 'appointment_time')
    upcoming_count = upcoming_appointments.count()

    # Follow-ups for this user's appointments
    follow_ups = FollowUp.objects.filter(
        appointment__user=request.user,
        is_completed=False,
        follow_up_date__gte=today,
    ).order_by('follow_up_date')
    follow_up_count = follow_ups.count()

    # Unread notifications
    unread_notif_count = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()

    # Recent activities (UserActivity)
    from accounts.models import UserActivity
    recent_activities = UserActivity.objects.filter(user=request.user)[:10]

    return render(request, 'accounts/user_dashboard.html', {
        'pet_count': pet_count,
        'upcoming_appointments': upcoming_appointments[:5],
        'upcoming_count': upcoming_count,
        'follow_ups': follow_ups,
        'follow_up_count': follow_up_count,
        'unread_notif_count': unread_notif_count,
        'recent_activities': recent_activities,
    })


@login_required
def profile_view(request):
    """User profile page."""
    from .forms import UserProfileUpdateForm
    if request.method == 'POST':
        form = UserProfileUpdateForm(
            request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile was successfully updated.')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserProfileUpdateForm(instance=request.user)

    if request.user.is_clinic_staff():
        template_name = 'accounts/profile_admin.html'
    else:
        template_name = 'accounts/profile.html'

    return render(request, template_name, {
        'user': request.user,
        'form': form,
    })


@login_required
@role_required(User.Role.STAFF, User.Role.VETERINARIAN, User.Role.BRANCH_ADMIN, User.Role.ADMIN)
def admin_dashboard_view(request):
    """Admin portal dashboard — restricted to clinic staff roles."""
    from appointments.models import Appointment
    from patients.models import Pet
    from employees.models import StaffMember
    from notifications.models import Notification

    today = date.today()

    # ── Today's appointments ──
    todays_appointments = Appointment.objects.filter(
        appointment_date=today,
    ).select_related('branch', 'preferred_vet').order_by('appointment_time')

    today_count = todays_appointments.count()
    today_confirmed = todays_appointments.filter(status='CONFIRMED').count()
    today_pending = todays_appointments.filter(status='PENDING').count()

    # ── Active patients ──
    patient_count = Pet.objects.count()

    # ── Staff ──
    total_staff = StaffMember.objects.count()
    active_staff = StaffMember.objects.filter(is_active=True).count()

    # ── Branches ──
    branches = Branch.objects.filter(is_active=True)

    # ── Recent appointments (activity) ──
    recent_appointments = Appointment.objects.select_related(
        'branch', 'preferred_vet'
    ).order_by('-created_at')[:5]

    # ── Unread notifications ──
    unread_notif_count = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()

    return render(request, 'accounts/admin_dashboard.html', {
        'today_count': today_count,
        'today_confirmed': today_confirmed,
        'today_pending': today_pending,
        'patient_count': patient_count,
        'total_staff': total_staff,
        'active_staff': active_staff,
        'branches': branches,
        'todays_appointments': todays_appointments[:10],
        'recent_appointments': recent_appointments,
        'unread_notif_count': unread_notif_count,
    })
