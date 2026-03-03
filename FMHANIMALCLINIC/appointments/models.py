from django.db import models
from django.utils import timezone
from branches.models import Branch
from employees.models import StaffMember, VetSchedule


class Appointment(models.Model):
    """Represents a pet appointment / reservation."""

    class Source(models.TextChoices):
        WALKIN = 'WALKIN', 'Walk-in (Public)'
        PORTAL = 'PORTAL', 'Portal (Logged-in)'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        COMPLETED = 'COMPLETED', 'Completed'

    class Reason(models.TextChoices):
        GENERAL = 'GENERAL', 'General Consultation'
        ROUTINE = 'ROUTINE', 'Routine Check-up'
        VACCINATION = 'VACCINATION', 'Vaccination'
        SURGERY = 'SURGERY', 'Surgery'
        EMERGENCY = 'EMERGENCY', 'Emergency'
        OTHER = 'OTHER', 'Other'

    # Owner info
    owner_name = models.CharField(max_length=200)
    owner_email = models.EmailField(blank=True)
    owner_phone = models.CharField(max_length=20, blank=True)

    # Pet info
    pet_name = models.CharField(max_length=150)
    pet_breed = models.CharField(max_length=150, blank=True)
    pet_symptoms = models.TextField(
        blank=True, help_text='Specific symptoms recorded for this visit')

    # Scheduling
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='appointments',
    )
    preferred_vet = models.ForeignKey(
        StaffMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appointments',
        limit_choices_to={'position': StaffMember.Position.VETERINARIAN},
    )
    appointment_date = models.DateField()
    appointment_time = models.TimeField()

    # Booking metadata
    reason = models.CharField(
        max_length=20,
        choices=Reason.choices,
        default=Reason.GENERAL,
    )
    source = models.CharField(
        max_length=10,
        choices=Source.choices,
        default=Source.WALKIN,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    is_returning_customer = models.BooleanField(default=False)

    # Link to user account (set when logged-in user books)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appointments',
    )

    notes = models.TextField(blank=True, help_text='Additional notes')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-appointment_date', '-appointment_time']

    def __str__(self):
        return f'{self.pet_name} ({self.owner_name}) — {self.appointment_date} {self.appointment_time}'

    @property
    def is_past(self):
        """Returns True if the appointment date+time has already passed."""
        now = timezone.now()
        from datetime import datetime
        appt_dt = timezone.make_aware(
            datetime.combine(self.appointment_date, self.appointment_time)
        )
        return appt_dt < now

    @property
    def should_auto_delete(self):
        """Returns True if 1 day has passed since the appointment time."""
        from datetime import datetime, timedelta
        now = timezone.now()
        appt_dt = timezone.make_aware(
            datetime.combine(self.appointment_date, self.appointment_time)
        )
        return now > appt_dt + timedelta(days=1)

    @classmethod
    def cleanup_expired(cls):
        """Delete appointments that are 1+ day past their booked time."""
        from datetime import datetime, timedelta
        cutoff = timezone.now() - timedelta(days=1)
        expired = cls.objects.filter(
            appointment_date__lt=cutoff.date()
        )
        count = expired.count()
        expired.delete()
        return count
