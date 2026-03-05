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
    path('product/<int:pk>/reserve/', views.reserve_product_view,
         name='reserve_product'),
    path('reservation/<int:pk>/success/', views.reservation_success_view,
         name='reservation_success'),
    path('my-reservations/', views.my_reservations_view,
         name='my_reservations'),
    path('reservation/<int:pk>/confirm/', views.confirm_reservation_view,
         name='confirm_reservation'),
    path('reservation/<int:pk>/cancel/', views.cancel_reservation_view,
         name='cancel_reservation'),
]
