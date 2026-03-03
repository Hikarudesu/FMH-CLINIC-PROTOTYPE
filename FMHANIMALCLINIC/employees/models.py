from datetime import timedelta

from django.db import models
from django.utils import timezone
from branches.models import Branch

# Default lookahead for auto-generation (days)
SCHEDULE_LOOKAHEAD_DAYS = 30


class StaffMember(models.Model):
    """Represents a staff member at the clinic."""

    class Position(models.TextChoices):
        VETERINARIAN = 'VETERINARIAN', 'Veterinarian'
        VET_ASSISTANT = 'VET_ASSISTANT', 'Vet Assistant'
        RECEPTIONIST = 'RECEPTIONIST', 'Receptionist'
        ADMIN = 'ADMIN', 'Admin'
        OJT = 'OJT', 'OJT'

    # Personal Info
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    # Employment
    position = models.CharField(max_length=20, choices=Position.choices)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_members',
    )
    date_hired = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # License (for Vets)
    license_number = models.CharField(
        max_length=100, blank=True, help_text='PRC license number (for vets)')
    license_expiry = models.DateField(
        null=True, blank=True, help_text='License expiration date')

    # Link to login account (optional)
    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_profile',
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.first_name} {self.last_name} — {self.get_position_display()}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def is_vet(self):
        return self.position == self.Position.VETERINARIAN

    @property
    def license_expired(self):
        if self.license_expiry:
            from django.utils import timezone
            return self.license_expiry < timezone.now().date()
        return False


class VetSchedule(models.Model):
    """Represents a vet/staff schedule entry for a specific day."""

    class ShiftType(models.TextChoices):
        GENERAL = 'GENERAL', 'General'
        SURGERY = 'SURGERY', 'Surgery Only'
        TELEHEALTH = 'TELEHEALTH', 'Telehealth'
        BREAK = 'BREAK', 'Break'
        CHECKUP = 'CHECKUP', 'Check-up Only'

    staff = models.ForeignKey(
        StaffMember,
        on_delete=models.CASCADE,
        related_name='schedules',
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='schedules',
    )
    is_available = models.BooleanField(default=True)
    shift_type = models.CharField(
        max_length=20,
        choices=ShiftType.choices,
        default=ShiftType.GENERAL,
    )
    notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'start_time']
        # Removed unique_together to allow multiple shifts per vet per day

    def __str__(self):
        return f'{self.staff.full_name} — {self.date} ({self.start_time}–{self.end_time})'


class RecurringSchedule(models.Model):
    """Weekly recurring schedule template for automatic schedule generation."""

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, 'Monday'
        TUESDAY = 1, 'Tuesday'
        WEDNESDAY = 2, 'Wednesday'
        THURSDAY = 3, 'Thursday'
        FRIDAY = 4, 'Friday'
        SATURDAY = 5, 'Saturday'
        SUNDAY = 6, 'Sunday'

    staff = models.ForeignKey(
        StaffMember,
        on_delete=models.CASCADE,
        related_name='recurring_schedules',
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='recurring_schedules',
    )
    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    shift_type = models.CharField(
        max_length=20,
        choices=VetSchedule.ShiftType.choices,
        default=VetSchedule.ShiftType.GENERAL,
    )
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField(
        null=True, blank=True, help_text='Start applying from this date')
    effective_until = models.DateField(
        null=True, blank=True, help_text='Stop applying after this date')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['staff', 'day_of_week', 'start_time']

    def __str__(self):
        return f'{self.staff.full_name} — {self.get_day_of_week_display()} ({self.start_time}–{self.end_time})'

    def save(self, *args, **kwargs):
        """Override save to auto-generate VetSchedule entries for the next N days."""
        super().save(*args, **kwargs)
        if self.is_active:
            self.generate_entries(days_ahead=SCHEDULE_LOOKAHEAD_DAYS)

    def generate_entries(self, days_ahead=SCHEDULE_LOOKAHEAD_DAYS):
        """Generate VetSchedule entries from this template for the next N days."""
        today = timezone.now().date()
        start_date = self.effective_from if self.effective_from and self.effective_from > today else today
        end_date = start_date + timedelta(days=days_ahead)
        if self.effective_until and end_date > self.effective_until:
            end_date = self.effective_until

        created = 0
        current = start_date
        while current <= end_date:
            if current.weekday() == self.day_of_week:
                # Skip if entry already exists (overlap detection)
                exists = VetSchedule.objects.filter(
                    staff=self.staff,
                    date=current,
                    start_time=self.start_time,
                    end_time=self.end_time,
                    branch=self.branch,
                ).exists()
                if not exists:
                    VetSchedule.objects.create(
                        staff=self.staff,
                        date=current,
                        start_time=self.start_time,
                        end_time=self.end_time,
                        branch=self.branch,
                        shift_type=self.shift_type,
                        is_available=True,
                    )
                    created += 1
            current += timedelta(days=1)
        return created

    @classmethod
    def regenerate_all(cls, days_ahead=SCHEDULE_LOOKAHEAD_DAYS):
        """Regenerate entries for ALL active recurring templates. Can be called via management command or cron."""
        total = 0
        for tmpl in cls.objects.filter(is_active=True).select_related('staff', 'branch'):
            total += tmpl.generate_entries(days_ahead=days_ahead)
        return total
