"""Billing app models."""

from django.db import models
from branches.models import Branch


class BillableItem(models.Model):
    """Represents a clinic service (consultations, procedures, grooming, etc.)."""

    name = models.CharField(max_length=200)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL,
                               null=True, blank=True, related_name='billable_items')
    category = models.CharField(max_length=100, blank=True)
    tax_rate = models.CharField(max_length=50, blank=True)
    duration = models.IntegerField(default=0, help_text="Duration in minutes")

    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    content = models.TextField(
        blank=True, help_text="Manage content associated with this service.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options."""
        ordering = ['-created_at']

    def __str__(self):
        return str(self.name)
