from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import PostComposerForm
from .models import Post, PostTarget


def group_profiles_by_platform(profiles):
    grouped = {}
    for profile in profiles:
        grouped.setdefault(profile.get_platform_display(), []).append(profile)
    return grouped.items()


@login_required
def post_list(request):
    posts = (
        Post.objects.filter(owner=request.user)
        .prefetch_related("targets__connected_profile")
        .order_by("-created_at")
    )
    return render(request, "posts/post_list.html", {"posts": posts})


@login_required
def new_post(request):
    if request.method == "POST":
        form = PostComposerForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                post = form.save(commit=False)
                post.owner = request.user
                post.save()
                scheduled_time = form.cleaned_data["scheduled_time"]
                connected_profiles = form.cleaned_data["connected_profiles"]
                PostTarget.objects.bulk_create(
                    [
                        PostTarget(
                            post=post,
                            connected_profile=profile,
                            scheduled_time=scheduled_time,
                            board_id=request.POST.get(f"board_id_{profile.pk}", "")
                            or None,
                            board_name=request.POST.get(
                                f"board_name_{profile.pk}", ""
                            )
                            or None,
                        )
                        for profile in connected_profiles
                    ]
                )
            messages.success(request, "Post scheduled successfully.")
            return redirect("posts:list")
    else:
        form = PostComposerForm(user=request.user)

    profiles = form.fields["connected_profiles"].queryset
    return render(
        request,
        "posts/post_form.html",
        {
            "form": form,
            "profiles_by_platform": group_profiles_by_platform(profiles),
        },
    )
