"""
URL configurations for the patients app.
"""
from django.urls import path
from . import views

# pylint: disable=invalid-name
app_name = 'patients'

urlpatterns = [
    path('admin/list/', views.admin_list_view, name='admin_list'),
    path('admin/add/', views.admin_add_pet_view, name='admin_add_pet'),
    path('admin/<int:pk>/edit/', views.admin_edit_pet_view, name='admin_edit_pet'),
    path('admin/<int:pk>/delete/', views.admin_delete_pet_view, name='admin_delete_pet'),
    path('my-pets/', views.my_pets_view, name='my_pets'),
    path('add/', views.add_pet_view, name='add_pet'),
    path('<int:pk>/edit/', views.edit_pet_view, name='edit_pet'),
    path('<int:pk>/delete/', views.delete_pet_view, name='delete_pet'),
]
