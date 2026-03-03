"""URL configuration for the billing app."""
from django.urls import path
from . import views

app_name = 'billing'  # pylint: disable=invalid-name

urlpatterns = [
    path('statements/', views.statement_list, name='statement_list'),
    path('billable-items/', views.BillableItemListView.as_view(),
         name='billable_items'),
    path('billable-items/create/', views.BillableItemCreateView.as_view(),
         name='billable_item_create'),
    path('billable-items/<int:pk>/update/',
         views.BillableItemUpdateView.as_view(), name='billable_item_update'),
    path('billable-items/<int:pk>/delete/',
         views.billable_item_delete, name='billable_item_delete'),
    path('bills-and-payment/', views.InvoiceListView.as_view(),
         name='bills_and_payment'),
    path('bills-and-payment/create/',
         views.InvoiceCreateView.as_view(), name='invoice_create'),
    path('bills-and-payment/<int:pk>/update/',
         views.InvoiceUpdateView.as_view(), name='invoice_update'),
    path('bills-and-payment/<int:pk>/delete/',
         views.invoice_delete, name='invoice_delete'),
]
