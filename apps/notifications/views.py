from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from .models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)
    paginator = Paginator(notifications, 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "notifications/notification_list.html",
        {"page_obj": page},
    )


@login_required
def notification_dropdown(request):
    notifications = Notification.objects.filter(user=request.user)[:10]
    return render(
        request,
        "notifications/partials/dropdown.html",
        {"notifications": notifications},
    )


@login_required
def mark_all_read(request):
    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True
        )
    notifications = Notification.objects.filter(user=request.user)[:10]
    return render(
        request,
        "notifications/partials/dropdown.html",
        {"notifications": notifications},
    )
