"""URL configuration for the billing app — Services only."""
from django.urls import path
from . import views

app_name = 'billing'  # pylint: disable=invalid-name

urlpatterns = [
    path('services/', views.BillableItemListView.as_view(),
         name='billable_items'),
    path('services/create/', views.BillableItemCreateView.as_view(),
         name='billable_item_create'),
    path('services/<int:pk>/update/',
         views.BillableItemUpdateView.as_view(), name='billable_item_update'),
    path('services/<int:pk>/delete/',
         views.billable_item_delete, name='billable_item_delete'),
]
