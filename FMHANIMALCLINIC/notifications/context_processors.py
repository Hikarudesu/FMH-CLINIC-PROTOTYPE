from .models import Notification


def unread_notifications(request):
    """
    Returns the 5 most recent unread notifications for the authenticated user.
    """
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).order_by('-created_at')[:5]

        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        return {
            'recent_notifications': notifications,
            'unread_notifications_count': unread_count
        }
    return {}
