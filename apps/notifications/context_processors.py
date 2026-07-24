from .models import Notification


def notifications(request):
    if not request.user.is_authenticated:
        return {
            "unread_notification_count": 0,
            "recent_notifications": [],
        }

    notifications_queryset = Notification.objects.filter(user=request.user)
    return {
        "unread_notification_count": notifications_queryset.filter(is_read=False).count(),
        "recent_notifications": notifications_queryset[:10],
    }
