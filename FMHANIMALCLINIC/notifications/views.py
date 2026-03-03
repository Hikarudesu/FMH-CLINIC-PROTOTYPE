from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Notification, FollowUp


@login_required
def user_notifications(request):
    """List all notifications for the current user."""
    notifications = Notification.objects.filter(user=request.user)
    unread_count = notifications.filter(is_read=False).count()

    return render(request, 'notifications/notification_list.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })


@login_required
@require_POST
def mark_read(request, pk):
    """Mark a notification as read (AJAX endpoint)."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    return JsonResponse({'success': True})


@login_required
@require_POST
def mark_all_read(request):
    """Mark all notifications as read."""
    Notification.objects.filter(
        user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


@login_required
def admin_notification_list(request):
    """List all notifications for the current admin user."""
    # Ensure only staff can access this view
    if not request.user.is_staff:
        # Better to return forbidden or redirect, but let's redirect to user portal if trying to access
        from django.shortcuts import redirect
        return redirect('notifications:notification_list')

    notifications = Notification.objects.filter(user=request.user)
    unread_count = notifications.filter(is_read=False).count()

    return render(request, 'notifications/admin_notification_list.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })
