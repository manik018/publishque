from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def coming_soon(request):
    return render(
        request,
        "posts/coming_soon.html",
        {
            "page_title": "Posts & Scheduler",
            "message": "Post creation, approvals, queues, and publishing calendars are coming soon.",
        },
    )
