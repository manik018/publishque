from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import ConnectedProfile
from .services import (
    FacebookPageFetchError,
    LinkedInOrganizationFetchError,
    PinterestBoardFetchError,
    PinterestTokenError,
    fetch_facebook_pages,
    fetch_linkedin_organizations,
    fetch_pinterest_boards,
)


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
        platform = connected_profile.get_platform_display()
        display_name = connected_profile.display_name
        social_account = connected_profile.social_account
        connected_profile.delete()
        if not ConnectedProfile.objects.filter(social_account=social_account).exists():
            SocialAccount.objects.filter(pk=social_account.pk).delete()
        messages.success(request, f"{display_name} was disconnected from {platform}.")
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


def connect_facebook_page(user, social_account, page):
    connected_profile, created = ConnectedProfile.objects.update_or_create(
        user=user,
        platform=ConnectedProfile.Platform.FACEBOOK,
        platform_account_id=page["id"],
        defaults={
            "social_account": social_account,
            "display_name": page["name"],
            "page_access_token": page["access_token"],
            "is_active": True,
        },
    )
    return connected_profile, created


def connect_linkedin_organization(user, social_account, organization):
    social_token = social_account.socialtoken_set.get()
    connected_profile, created = ConnectedProfile.objects.update_or_create(
        user=user,
        platform=ConnectedProfile.Platform.LINKEDIN,
        platform_account_id=organization["id"],
        defaults={
            "social_account": social_account,
            "display_name": organization["name"],
            "page_access_token": social_token.token,
            "is_active": True,
        },
    )
    return connected_profile, created


@login_required
def facebook_select_page(request):
    social_account = (
        SocialAccount.objects.filter(user=request.user, provider="facebook")
        .order_by("-id")
        .first()
    )
    if social_account is None:
        messages.error(request, "Connect Facebook before selecting a Page.")
        return redirect("profiles:connected_profiles")

    try:
        pages = fetch_facebook_pages(social_account)
    except FacebookPageFetchError as exc:
        messages.error(request, str(exc))
        return redirect("profiles:connected_profiles")

    if request.method == "POST":
        page_id = request.POST.get("page_id", "")
        selected_page = next((page for page in pages if page["id"] == page_id), None)
        if selected_page is None:
            messages.error(request, "Select a valid Facebook Page to connect.")
        else:
            connected_profile, created = connect_facebook_page(
                request.user,
                social_account,
                selected_page,
            )
            action = "connected" if created else "updated"
            messages.success(
                request,
                f"{connected_profile.display_name} was {action} for Facebook.",
            )
            return redirect("profiles:connected_profiles")

    elif len(pages) == 1:
        connected_profile, created = connect_facebook_page(
            request.user,
            social_account,
            pages[0],
        )
        action = "connected" if created else "updated"
        messages.success(
            request,
            f"{connected_profile.display_name} was {action} for Facebook.",
        )
        return redirect("profiles:connected_profiles")

    return render(
        request,
        "profiles/facebook_select_page.html",
        {
            "pages": pages,
        },
    )


@login_required
def linkedin_select_organization(request):
    social_account = (
        SocialAccount.objects.filter(user=request.user, provider="linkedin_oauth2")
        .order_by("-id")
        .first()
    )
    if social_account is None:
        messages.error(request, "Connect LinkedIn before selecting an Organization.")
        return redirect("profiles:connected_profiles")

    try:
        organizations = fetch_linkedin_organizations(social_account)
    except LinkedInOrganizationFetchError as exc:
        messages.error(request, str(exc))
        return redirect("profiles:connected_profiles")

    if request.method == "POST":
        organization_id = request.POST.get("organization_id", "")
        selected_organization = next(
            (
                organization
                for organization in organizations
                if organization["id"] == organization_id
            ),
            None,
        )
        if selected_organization is None:
            messages.error(request, "Select a valid LinkedIn Organization to connect.")
        else:
            connected_profile, created = connect_linkedin_organization(
                request.user,
                social_account,
                selected_organization,
            )
            action = "connected" if created else "updated"
            messages.success(
                request,
                f"{connected_profile.display_name} was {action} for LinkedIn.",
            )
            return redirect("profiles:connected_profiles")

    elif len(organizations) == 1:
        connected_profile, created = connect_linkedin_organization(
            request.user,
            social_account,
            organizations[0],
        )
        action = "connected" if created else "updated"
        messages.success(
            request,
            f"{connected_profile.display_name} was {action} for LinkedIn.",
        )
        return redirect("profiles:connected_profiles")

    return render(
        request,
        "profiles/linkedin_select_organization.html",
        {
            "organizations": organizations,
        },
    )
