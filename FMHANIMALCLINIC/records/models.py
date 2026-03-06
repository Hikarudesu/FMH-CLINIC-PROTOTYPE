"""
Models for managing Patient Medical Records.
"""
from django.db import models
from patients.models import Pet
from employees.models import StaffMember
from branches.models import Branch


class MedicalRecord(models.Model):
    """
    Represents a specific medical record/visit history item attached to a Pet.
    """
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE,
                            related_name='medical_records')
    vet = models.ForeignKey(StaffMember, on_delete=models.SET_NULL,
                            null=True, related_name='medical_records')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL,
                               null=True, blank=True,
                               related_name='medical_records')
    weight = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Weight in kg", null=True, blank=True)
    temperature = models.DecimalField(
        max_digits=4, decimal_places=1, help_text="Temperature in °C", null=True, blank=True)
    history_clinical_signs = models.TextField(
        verbose_name="History / Clinical Signs", blank=True, null=True)
    treatment = models.TextField(verbose_name="Tx (Treatment)")
    rx = models.TextField(
        verbose_name="Rx (Prescription)", blank=True, null=True)
    ff_up = models.DateField(
        verbose_name="FF-UP (Follow-Up)", blank=True, null=True)
    date_recorded = models.DateField()

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='Active')

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        """Meta options for MedicalRecord model."""
        ordering = ['-date_recorded', '-created_at']

    def __str__(self):
        return f"Record for {self.pet.name} on {self.date_recorded}"

    @property
    def latest_entry(self):
        """Return the most recent RecordEntry for this record."""
        return self.entries.order_by('-date_recorded', '-created_at').first()


class RecordEntry(models.Model):
    """
    Represents a single visit/consultation entry on a pet's medical record card.
    Multiple entries can belong to one MedicalRecord (one card per pet).
    """
    record = models.ForeignKey(
        MedicalRecord, on_delete=models.CASCADE, related_name='entries')
    vet = models.ForeignKey(
        StaffMember, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='record_entries')
    date_recorded = models.DateField()
    weight = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Weight in kg",
        null=True, blank=True)
    temperature = models.DecimalField(
        max_digits=4, decimal_places=1, help_text="Temperature in °C",
        null=True, blank=True)
    history_clinical_signs = models.TextField(
        verbose_name="History / Clinical Signs", blank=True, null=True)
    treatment = models.TextField(verbose_name="Tx (Treatment)", blank=True, null=True)
    rx = models.TextField(
        verbose_name="Rx (Prescription)", blank=True, null=True)
    ff_up = models.DateField(
        verbose_name="FF-UP (Follow-Up)", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        """Meta options for RecordEntry model."""
        ordering = ['-date_recorded', '-created_at']

    def __str__(self):
        return f"Entry for {self.record.pet.name} on {self.date_recorded}"
