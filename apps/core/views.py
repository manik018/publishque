from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.posts.models import PostTarget
from apps.profiles.models import ConnectedProfile


@login_required
def dashboard(request):
    connected_profile_count = ConnectedProfile.objects.filter(user=request.user).count()
    scheduled_posts_count = PostTarget.objects.filter(
        post__owner=request.user,
        status__in=[PostTarget.Status.PENDING, PostTarget.Status.PROCESSING],
    ).count()
    published_posts_count = PostTarget.objects.filter(
        post__owner=request.user,
        status=PostTarget.Status.SENT,
    ).count()
    return render(
        request,
        "core/dashboard.html",
        {
            "connected_profile_count": connected_profile_count,
            "scheduled_posts_count": scheduled_posts_count,
            "published_posts_count": published_posts_count,
        },
    )


@login_required
def settings_coming_soon(request):
    return render(
        request,
        "core/coming_soon.html",
        {
            "page_title": "Settings",
            "message": "Profile, workspace, and billing preferences will live here soon.",
        },
    )
