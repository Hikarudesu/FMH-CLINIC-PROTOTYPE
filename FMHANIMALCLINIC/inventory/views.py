"""
Views for handling inventory catalog display.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from branches.models import Branch
from .models import Product, StockAdjustment
from .forms import StockAdjustmentForm, ProductForm
from django.shortcuts import get_object_or_404


@login_required
def catalog_view(request):
    """Digital Catalog displaying products available."""

    # Get all active branches for the filter dropdown
    # pylint: disable=no-member
    branches = Branch.objects.filter(is_active=True)

    # Base queryset for products
    # pylint: disable=no-member
    products = Product.objects.all().select_related('branch')

    # Get the selected branch from query params
    selected_branch_id = request.GET.get('branch')

    if selected_branch_id:
        try:
            products = products.filter(branch_id=selected_branch_id)
            # pylint: disable=no-member
            selected_branch = Branch.objects.get(id=selected_branch_id)
        except Branch.DoesNotExist:  # pylint: disable=no-member
            selected_branch = None
    else:
        selected_branch = None

    return render(request, 'inventory/catalog.html', {
        'products': products,
        'branches': branches,
        'selected_branch': selected_branch,
    })


@login_required
def inventory_management_view(request):
    """Admin view for managing stock adjustments."""
    if not request.user.is_admin_role() and not request.user.is_superuser:
        messages.error(
            request, "You don't have permission to access inventory management.")
        return redirect('patients:my_pets')

    # pylint: disable=no-member
    adjustments = StockAdjustment.objects.all().select_related('product', 'branch')

    # Filter by branch if needed
    branches = Branch.objects.filter(is_active=True)
    selected_branch_id = request.GET.get('branch')

    # pylint: disable=no-member
    products = Product.objects.all().select_related('branch')

    if selected_branch_id:
        adjustments = adjustments.filter(branch_id=selected_branch_id)
        products = products.filter(branch_id=selected_branch_id)

    # Health Metrics
    total_value = sum(p.inventory_value for p in products)
    low_stock_count = sum(1 for p in products if p.status == 'LOW_STOCK')
    out_of_stock_count = sum(1 for p in products if p.status == 'OUT_OF_STOCK')

    return render(request, 'inventory/management.html', {
        'adjustments': adjustments,
        'products': products,
        'branches': branches,
        'selected_branch_id': selected_branch_id,
        'total_value': total_value,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
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

    return render(request, 'inventory/product_form.html', {'form': form, 'product': product})


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
                request, "Failed to record adjustment. Please check the form errors.")
    else:
        form = StockAdjustmentForm()

    return render(request, 'inventory/adjustment_form.html', {
        'form': form
    })
