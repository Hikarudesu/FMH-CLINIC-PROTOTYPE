"""
Main URL Configuration for the FMHANIMALCLINIC project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Public-facing pages
    path('', include('landing.urls')),

    # App URLs
    path('accounts/', include('accounts.urls')),
    path('branches/', include('branches.urls')),
    path('patients/', include('patients.urls')),
    path('appointments/', include('appointments.urls')),
    path('records/', include('records.urls')),
    path('inventory/', include('inventory.urls')),
    path('billing/', include('billing.urls')),
    path('diagnostics/', include('diagnostics.urls')),
    path('employees/', include('employees.urls')),
    path('notifications/', include('notifications.urls')),
    path('reports/', include('reports.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else None
    )
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
