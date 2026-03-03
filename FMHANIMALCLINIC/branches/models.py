from django.db import models


class Branch(models.Model):
    """Represents a physical clinic location."""

    name = models.CharField(max_length=150, unique=True, help_text="Branch name (e.g. Downtown Clinic)")
    branch_code = models.CharField(max_length=50, unique=True, blank=True, null=True)

    # Contact
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)

    # Address
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)

    # Operations
    operating_hours = models.TextField(blank=True, null=True, help_text="e.g. Mon-Fri: 8am-6pm, Sat: 9am-2pm")
    is_active = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Branches'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} — {self.city}'
