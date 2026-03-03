"""
Django Administration config for the Records application.
"""
from django.contrib import admin
from .models import MedicalRecord


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    """Admin interface customization for the MedicalRecord model."""
    list_display = ('pet', 'vet', 'branch', 'date_recorded', 'treatment')
    list_filter = ('branch', 'vet', 'date_recorded')
    search_fields = ('pet__name', 'history_clinical_signs', 'treatment')
    autocomplete_fields = ('pet', 'vet')
