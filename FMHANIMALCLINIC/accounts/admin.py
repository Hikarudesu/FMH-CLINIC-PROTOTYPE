from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for the User model with role and branch fields."""

    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'branch', 'is_active')
    list_filter = ('role', 'branch', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    # Add role & branch to the existing fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Clinic Info', {'fields': ('role', 'branch', 'phone_number')}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Clinic Info', {'fields': ('role', 'branch', 'phone_number')}),
    )
