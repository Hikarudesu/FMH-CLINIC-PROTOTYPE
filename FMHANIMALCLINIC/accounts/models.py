"""Models for the accounts app."""
# pylint: disable=no-member,unused-argument

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    """Custom user model with role-based access control."""

    class Role(models.TextChoices):
        """User role choices."""
        PET_OWNER = 'PET_OWNER', 'Pet Owner'
        STAFF = 'STAFF', 'Staff'
        VETERINARIAN = 'VETERINARIAN', 'Veterinarian'
        BRANCH_ADMIN = 'BRANCH_ADMIN', 'Branch Admin'
        ADMIN = 'ADMIN', 'Admin'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PET_OWNER,
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text='The branch this user belongs to.',
    )
    profile_picture = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True,
        help_text='Profile picture for the user'
    )
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(
        blank=True, help_text='Full address of the pet owner')

    # ── helper properties ──────────────────────────────────
    def is_admin_role(self):
        """Returns True for Admin and Branch Admin roles."""
        return self.role in (self.Role.ADMIN, self.Role.BRANCH_ADMIN)

    def is_clinic_staff(self):
        """Returns True for any role that accesses the admin portal."""
        return self.role in (
            self.Role.STAFF,
            self.Role.VETERINARIAN,
            self.Role.BRANCH_ADMIN,
            self.Role.ADMIN,
        )

    def is_pet_owner(self):
        """Returns True if the user is a pet owner."""
        return self.role == self.Role.PET_OWNER

    def save(self, *args, **kwargs):
        """Save user and set ADMIN role for superusers."""
        # Superusers should always have the ADMIN role
        if self.is_superuser and self.role == self.Role.PET_OWNER:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    class Meta:
        """Meta options for User model."""
        ordering = ['username']

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


class UserActivity(models.Model):
    """Logs recent actions performed by the user."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='recent_activities')
    action = models.CharField(max_length=50)  # e.g., 'Created', 'Updated'
    object_name = models.CharField(max_length=200)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta options for UserActivity model."""
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.action} {self.object_name}"


# Signals for UserActivity


@receiver(post_save, sender='patients.Pet')
def log_pet_activity(sender, instance, created, **kwargs):
    """Log an activity when a Pet record is created or updated."""
    if hasattr(instance, 'owner') and instance.owner:
        action = 'Created Pet' if created else 'Updated Pet'
        UserActivity.objects.create(
            user=instance.owner,
            action=action,
            object_name=instance.name
        )


@receiver(post_save, sender='appointments.Appointment')
def log_appointment_activity(sender, instance, created, **kwargs):
    """Log an activity when an Appointment is created or updated."""
    if hasattr(instance, 'user') and instance.user:
        action = 'Created Appointment' if created else 'Updated Appointment'
        UserActivity.objects.create(
            user=instance.user,
            action=action,
            object_name=f"Appointment on {instance.appointment_date}"
        )
