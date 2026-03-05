"""
URL configuration for the inventory application.
"""
from django.urls import path
from . import views

app_name = 'inventory'  # pylint: disable=invalid-name

urlpatterns = [
    path('catalog/', views.catalog_view, name='catalog'),
    path('management/', views.inventory_management_view, name='management'),
    path('adjustment/new/', views.stock_adjustment_create_view,
         name='adjustment_new'),
    path('item/new/', views.product_create_view, name='product_new'),
    path('item/<int:pk>/edit/', views.product_edit_view, name='product_edit'),
]
