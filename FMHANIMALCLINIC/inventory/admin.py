from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'price', 'is_available',
                    'stock_quantity', 'updated_at')
    list_filter = ('branch', 'is_available')
    search_fields = ('name', 'description')
    list_editable = ('price', 'is_available', 'stock_quantity')
