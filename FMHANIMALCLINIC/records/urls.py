"""
URL patterns for the records application block.
"""
from django.urls import path
from . import views

app_name = 'records'  # pylint: disable=invalid-name

urlpatterns = [
    path('admin/', views.admin_records_list, name='admin_list'),
    path('admin/create/', views.admin_record_create, name='admin_create'),
    path('admin/<int:pk>/', views.admin_record_detail, name='admin_detail'),
    path('admin/<int:pk>/edit/', views.admin_record_edit, name='admin_edit'),
    path('admin/<int:pk>/delete/', views.admin_record_delete, name='admin_delete'),
    path('<int:pk>/download-pdf/', views.download_pdf_view, name='download_pdf'),
    path('<int:pk>/view/', views.user_record_detail, name='user_detail'),
]
