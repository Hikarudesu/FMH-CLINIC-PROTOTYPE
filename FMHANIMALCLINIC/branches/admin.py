from django.contrib import admin

from .models import Branch


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch_code', 'city', 'phone_number', 'is_active')
    list_filter = ('is_active', 'city', 'state')
    search_fields = ('name', 'branch_code', 'city')
