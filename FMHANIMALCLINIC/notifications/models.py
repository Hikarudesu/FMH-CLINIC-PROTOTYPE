from django.db import models
from django.conf import settings


class FollowUp(models.Model):
    """Represents a follow-up visit scheduled by an admin for a pet."""

    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.CASCADE,
        related_name='follow_ups',
    )
    pet_name = models.CharField(
        max_length=150, help_text='Denormalized for easy display')
    follow_up_date = models.DateField(verbose_name="Start Date")
    follow_up_end_date = models.DateField(
        null=True, blank=True, verbose_name="End Date",
        help_text="Optional end date for a follow-up range"
    )
    reason = models.TextField(
        blank=True, help_text='Reason for the return visit')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_follow_ups',
    )
    is_completed = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['follow_up_date']

    def __str__(self):
        if self.follow_up_end_date and self.follow_up_end_date != self.follow_up_date:
            return f'Follow-up: {self.pet_name} from {self.follow_up_date} to {self.follow_up_end_date}'
        return f'Follow-up: {self.pet_name} on {self.follow_up_date}'


class Notification(models.Model):
    """User-facing notification record."""

    class NotificationType(models.TextChoices):
        FOLLOW_UP = 'FOLLOW_UP', 'Follow-up'
        APPOINTMENT = 'APPOINTMENT', 'Appointment'
        INVENTORY_RESTOCK = 'INVENTORY_RESTOCK', 'Inventory Restock'
        LOW_INVENTORY = 'LOW_INVENTORY', 'Low Inventory'
        PRODUCT_RESERVATION = 'PRODUCT_RESERVATION', 'Product Reservation'
        GENERAL = 'GENERAL', 'General'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL,
    )
    related_follow_up = models.ForeignKey(
        FollowUp,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
    )
    related_object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="ID of the related object (e.g., Appointment ID or Product ID)"
    )
    is_read = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} — {self.user.username}'
