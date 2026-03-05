from django.contrib import admin
from .models import Pet


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ('name', 'species', 'breed', 'dob_or_age', 'sex', 'color', 'owner', 'created_at')
    list_filter = ('species', 'sex')
    search_fields = ('name', 'breed', 'owner__username')
