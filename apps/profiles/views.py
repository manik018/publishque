from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import ConnectedProfile
from .services import PinterestBoardFetchError, PinterestTokenError, fetch_pinterest_boards


@login_required
def connected_profiles(request):
    profiles = (
        ConnectedProfile.objects.filter(user=request.user)
        .select_related("social_account")
        .order_by("platform", "display_name")
    )
    return render(
        request,
        "profiles/connected_profiles.html",
        {"connected_profiles": profiles},
    )


@login_required
def disconnect_profile(request, pk):
    connected_profile = get_object_or_404(
        ConnectedProfile.objects.select_related("social_account"),
        pk=pk,
        user=request.user,
    )

    if request.method == "POST":
        social_account = connected_profile.social_account
        SocialAccount.objects.filter(pk=social_account.pk).delete()
        return redirect("profiles:connected_profiles")

    return render(
        request,
        "profiles/disconnect_confirm.html",
        {"connected_profile": connected_profile},
    )


@login_required
def pinterest_board_options(request, pk):
    connected_profile = get_object_or_404(
        ConnectedProfile,
        pk=pk,
        user=request.user,
        platform=ConnectedProfile.Platform.PINTEREST,
    )
    try:
        boards = fetch_pinterest_boards(connected_profile)
        error = ""
    except (PinterestBoardFetchError, PinterestTokenError) as exc:
        boards = []
        error = str(exc)

    return render(
        request,
        "profiles/partials/pinterest_board_options.html",
        {
            "connected_profile": connected_profile,
            "boards": boards,
            "error": error,
        },
    )
