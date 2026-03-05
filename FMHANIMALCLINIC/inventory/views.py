"""
Views for handling inventory catalog display.
"""
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from accounts.models import User
from branches.models import Branch
from notifications.models import Notification
from notifications.email_utils import send_reservation_notification
from .models import Product, StockAdjustment, Reservation
from .forms import StockAdjustmentForm, ProductForm


@login_required
def catalog_view(request):
    """Digital Catalog displaying products available."""

    # pylint: disable=no-member
    branches = Branch.objects.filter(is_active=True)
    products = Product.objects.all().select_related('branch')

    selected_branch_id = request.GET.get('branch')

    if selected_branch_id:
        try:
            products = products.filter(branch_id=selected_branch_id)
            selected_branch = Branch.objects.get(  # pylint: disable=no-member
                id=selected_branch_id
            )
        except Branch.DoesNotExist:  # pylint: disable=no-member
            selected_branch = None
    else:
        selected_branch = None

    # User's own reservations
    user_reservations = Reservation.objects.filter(  # pylint: disable=no-member
        user=request.user
    ).select_related('product', 'product__branch')

    return render(request, 'inventory/catalog.html', {
        'products': products,
        'branches': branches,
        'selected_branch': selected_branch,
        'user_reservations': user_reservations,
    })


@login_required
def inventory_management_view(request):
    """Admin view for managing stock adjustments."""
    if not request.user.is_admin_role() and not request.user.is_superuser:
        messages.error(
            request, "You don't have permission to access inventory management.")
        return redirect('patients:my_pets')

    # pylint: disable=no-member
    adjustments = StockAdjustment.objects.all().select_related(
        'product', 'branch')

    branches = Branch.objects.filter(is_active=True)
    selected_branch_id = request.GET.get('branch')
    products = Product.objects.all().select_related('branch')

    if selected_branch_id:
        adjustments = adjustments.filter(branch_id=selected_branch_id)
        products = products.filter(branch_id=selected_branch_id)

    # Health Metrics
    total_value = sum(p.inventory_value for p in products)
    low_stock_count = sum(1 for p in products if p.status == 'Low Stock')
    out_of_stock_count = sum(
        1 for p in products if p.status == 'Out of Stock'
    )

    # Pending reservations for admin view
    # pylint: disable=no-member
    pending_reservations = Reservation.objects.filter(
        status=Reservation.Status.PENDING
    ).select_related('product', 'user')

    return render(request, 'inventory/management.html', {
        'adjustments': adjustments,
        'products': products,
        'branches': branches,
        'selected_branch_id': selected_branch_id,
        'total_value': total_value,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'pending_reservations': pending_reservations,
    })


@login_required
def product_create_view(request):
    """View to create a new inventory item."""
    if not request.user.is_admin_role() and not request.user.is_superuser:
        messages.error(request, "Permission denied.")
        return redirect('patients:my_pets')

    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Item created successfully.")
            return redirect('inventory:management')
    else:
        form = ProductForm()

    return render(request, 'inventory/product_form.html', {'form': form})


@login_required
def product_edit_view(request, pk):
    """View to edit an existing inventory item."""
    product = get_object_or_404(Product, pk=pk)
    if not request.user.is_admin_role() and not request.user.is_superuser:
        messages.error(request, "Permission denied.")
        return redirect('patients:my_pets')

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Item updated successfully.")
            return redirect('inventory:management')
    else:
        form = ProductForm(instance=product)

    return render(request, 'inventory/product_form.html', {
        'form': form, 'product': product
    })


@login_required
def stock_adjustment_create_view(request):
    """Admin view to create a new stock adjustment."""
    if not request.user.is_admin_role() and not request.user.is_superuser:
        messages.error(
            request, "You don't have permission to access inventory management.")
        return redirect('patients:my_pets')

    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, "Stock adjustment recorded successfully.")
            return redirect('inventory:management')
        else:
            messages.error(
                request,
                "Failed to record adjustment. Please check the form errors."
            )
    else:
        form = StockAdjustmentForm()

    return render(request, 'inventory/adjustment_form.html', {
        'form': form
    })


@login_required
def reserve_product_view(request, pk):
    """Handle a product reservation from the digital catalog."""
    product = get_object_or_404(Product, pk=pk)

    if request.method != 'POST':
        return redirect('inventory:catalog')

    quantity = int(request.POST.get('quantity', 1))

    # Validate stock
    if quantity < 1:
        messages.error(request, "Quantity must be at least 1.")
        return redirect('inventory:catalog')

    if quantity > product.stock_quantity:
        messages.error(
            request,
            f"Not enough stock. Only {product.stock_quantity} available."
        )
        return redirect('inventory:catalog')

    # Create reservation
    reservation = Reservation.objects.create(  # pylint: disable=no-member
        user=request.user,
        product=product,
        quantity=quantity,
        notes=request.POST.get('notes', ''),
    )

    # Log stock adjustment
    StockAdjustment.objects.create(  # pylint: disable=no-member
        branch=product.branch,
        product=product,
        adjustment_type='Reservation',
        reference=f"RSV-{reservation.pk}",
        date=date.today(),
        quantity=quantity,  # save() enforces negative sign
        cost_per_unit=product.unit_cost,
        reason=f"Reserved by {request.user.get_full_name() or request.user.username}",
    )

    # Notify all admin users
    admin_users = User.objects.filter(  # pylint: disable=no-member
        role__in=[User.Role.ADMIN, User.Role.BRANCH_ADMIN]
    )
    for admin in admin_users:
        Notification.objects.create(  # pylint: disable=no-member
            user=admin,
            title="New Product Reservation",
            message=(
                f"{request.user.get_full_name() or request.user.username} "
                f"reserved {quantity}x {product.name}."
            ),
            notification_type=Notification.NotificationType.PRODUCT_RESERVATION,
            related_object_id=reservation.pk,
        )

    # Email notification to user
    send_reservation_notification(reservation)

    return redirect('inventory:reservation_success', pk=reservation.pk)


@login_required
def reservation_success_view(request, pk):
    """Confirmation page after a successful reservation."""
    reservation = get_object_or_404(
        Reservation, pk=pk, user=request.user
    )
    return render(request, 'inventory/reservation_success.html', {
        'reservation': reservation,
    })


@login_required
def my_reservations_view(request):
    """User view for their reservation history."""
    # pylint: disable=no-member
    reservations = Reservation.objects.filter(
        user=request.user
    ).select_related('product', 'product__branch')

    return render(request, 'inventory/my_reservations.html', {
        'reservations': reservations,
    })


@login_required
def confirm_reservation_view(request, pk):
    """Admin confirms a reservation when the user arrives to pick up."""
    if not request.user.is_admin_role() and not request.user.is_superuser:
        messages.error(request, "Permission denied.")
        return redirect('inventory:catalog')

    reservation = get_object_or_404(Reservation, pk=pk)

    if reservation.status != Reservation.Status.PENDING:
        messages.warning(request, "This reservation is no longer pending.")
        return redirect('inventory:management')

    reservation.status = Reservation.Status.CONFIRMED
    reservation.save()

    # Notify the user
    Notification.objects.create(  # pylint: disable=no-member
        user=reservation.user,
        title="Reservation Confirmed",
        message=(
            f"Your reservation for {reservation.quantity}x "
            f"{reservation.product.name} has been confirmed. "
            f"Thank you for your purchase!"
        ),
        notification_type=Notification.NotificationType.PRODUCT_RESERVATION,
        related_object_id=reservation.pk,
    )

    # Email notification
    send_reservation_notification(reservation)

    messages.success(
        request,
        f"Reservation RSV-{reservation.pk} confirmed."
    )
    return redirect('inventory:management')


@login_required
def cancel_reservation_view(request, pk):
    """User cancels their own pending reservation. Stock is restored."""
    reservation = get_object_or_404(
        Reservation, pk=pk, user=request.user
    )

    if reservation.status != Reservation.Status.PENDING:
        messages.warning(request, "This reservation cannot be cancelled.")
        return redirect('inventory:catalog')

    reservation.status = Reservation.Status.CANCELLED
    reservation.save()

    # Restore stock via a Return adjustment
    StockAdjustment.objects.create(  # pylint: disable=no-member
        branch=reservation.product.branch,
        product=reservation.product,
        adjustment_type='Return',
        reference=f"RSV-{reservation.pk}-CANCEL",
        date=date.today(),
        quantity=reservation.quantity,  # positive = stock added back
        cost_per_unit=reservation.product.unit_cost,
        reason=f"Reservation cancelled by {request.user.get_full_name() or request.user.username}",
    )

    # Notify admins
    admin_users = User.objects.filter(  # pylint: disable=no-member
        role__in=[User.Role.ADMIN, User.Role.BRANCH_ADMIN]
    )
    for admin in admin_users:
        Notification.objects.create(  # pylint: disable=no-member
            user=admin,
            title="Reservation Cancelled",
            message=(
                f"{request.user.get_full_name() or request.user.username} "
                f"cancelled reservation for {reservation.quantity}x "
                f"{reservation.product.name}. Stock has been restored."
            ),
            notification_type=Notification.NotificationType.PRODUCT_RESERVATION,
            related_object_id=reservation.pk,
        )

    # Email notification
    send_reservation_notification(reservation)

    messages.success(
        request, "Reservation cancelled. Stock has been restored.")
    return redirect('inventory:catalog')
