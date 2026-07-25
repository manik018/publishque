import pytest
import responses
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.utils import timezone
from unittest.mock import patch

from apps.profiles.models import ConnectedProfile
from apps.profiles.services import (
    FACEBOOK_TOKEN_EXCHANGE_URL,
    FACEBOOK_PAGES_URL,
    LINKEDIN_ACLS_URL,
    LINKEDIN_ORGANIZATION_URL,
    PINTEREST_BOARDS_URL,
    PINTEREST_TOKEN_URL,
    fetch_facebook_pages,
    fetch_linkedin_organizations,
    fetch_pinterest_boards,
    get_valid_pinterest_token,
)


pytestmark = pytest.mark.django_db


def create_connected_profile_with_token(
    user,
    token="access-token",
    refresh_token="refresh-token",
    expires_at=None,
):
    social_account = SocialAccount.objects.create(
        user=user,
        provider="pinterest",
        uid="pin-service",
    )
    connected_profile = ConnectedProfile.objects.create(
        user=user,
        platform=ConnectedProfile.Platform.PINTEREST,
        social_account=social_account,
        display_name="Service Pins",
        platform_account_id="pin-service",
    )
    SocialToken.objects.create(
        account=social_account,
        token=token,
        token_secret=refresh_token,
        expires_at=expires_at,
    )
    return connected_profile


def test_get_valid_pinterest_token_returns_existing_token_when_not_expired(
    django_user_model,
):
    user = django_user_model.objects.create_user(
        email="token@example.com",
        full_name="Token User",
        password="StrongPass123!",
    )
    connected_profile = create_connected_profile_with_token(
        user,
        token="fresh-token",
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )

    assert get_valid_pinterest_token(connected_profile) == "fresh-token"


@responses.activate
def test_get_valid_pinterest_token_refreshes_expired_token(
    django_user_model, settings
):
    settings.SOCIALACCOUNT_PROVIDERS["pinterest"]["APP"]["client_id"] = "client-id"
    settings.SOCIALACCOUNT_PROVIDERS["pinterest"]["APP"]["secret"] = "client-secret"
    user = django_user_model.objects.create_user(
        email="expired@example.com",
        full_name="Expired User",
        password="StrongPass123!",
    )
    connected_profile = create_connected_profile_with_token(
        user,
        token="old-token",
        refresh_token="old-refresh",
        expires_at=timezone.now() - timezone.timedelta(minutes=1),
    )
    responses.add(
        responses.POST,
        PINTEREST_TOKEN_URL,
        json={
            "access_token": "new-token",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        },
        status=200,
    )

    assert get_valid_pinterest_token(connected_profile) == "new-token"

    social_token = SocialToken.objects.get(account=connected_profile.social_account)
    assert social_token.token == "new-token"
    assert social_token.token_secret == "new-refresh"
    assert social_token.expires_at > timezone.now()


@responses.activate
def test_fetch_pinterest_boards_returns_parsed_board_list(django_user_model):
    user = django_user_model.objects.create_user(
        email="boards@example.com",
        full_name="Boards User",
        password="StrongPass123!",
    )
    connected_profile = create_connected_profile_with_token(
        user,
        token="board-token",
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )
    responses.add(
        responses.GET,
        PINTEREST_BOARDS_URL,
        json={"items": [{"id": "board-1", "name": "Launch Pins"}]},
        status=200,
    )

    assert fetch_pinterest_boards(connected_profile) == [
        {"id": "board-1", "name": "Launch Pins"}
    ]


@responses.activate
def test_fetch_facebook_pages_returns_parsed_page_list(django_user_model, settings):
    settings.SOCIALACCOUNT_PROVIDERS["facebook"]["APP"]["client_id"] = "fb-client"
    settings.SOCIALACCOUNT_PROVIDERS["facebook"]["APP"]["secret"] = "fb-secret"
    user = django_user_model.objects.create_user(
        email="facebook-pages@example.com",
        full_name="Facebook Pages User",
        password="StrongPass123!",
    )
    social_account = SocialAccount.objects.create(
        user=user,
        provider="facebook",
        uid="fb-user",
    )
    SocialToken.objects.create(account=social_account, token="user-access-token")
    responses.add(
        responses.GET,
        FACEBOOK_TOKEN_EXCHANGE_URL,
        json={"access_token": "long-lived-user-token", "expires_in": 5184000},
        status=200,
    )
    responses.add(
        responses.GET,
        FACEBOOK_PAGES_URL,
        json={
            "data": [
                {
                    "id": "page-1",
                    "name": "Launch Page",
                    "access_token": "page-access-token",
                    "picture": {"data": {"url": "https://example.com/page.jpg"}},
                }
            ]
        },
        status=200,
    )

    assert fetch_facebook_pages(social_account) == [
        {
            "id": "page-1",
            "name": "Launch Page",
            "access_token": "page-access-token",
            "picture_url": "https://example.com/page.jpg",
        }
    ]
    assert "fb_exchange_token=user-access-token" in responses.calls[0].request.url
    assert "access_token=long-lived-user-token" in responses.calls[1].request.url
    social_token = SocialToken.objects.get(account=social_account)
    assert social_token.token == "long-lived-user-token"
    assert social_token.expires_at > timezone.now()


@responses.activate
def test_fetch_facebook_pages_falls_back_when_token_exchange_fails(
    django_user_model, settings
):
    settings.SOCIALACCOUNT_PROVIDERS["facebook"]["APP"]["client_id"] = "fb-client"
    settings.SOCIALACCOUNT_PROVIDERS["facebook"]["APP"]["secret"] = "fb-secret"
    user = django_user_model.objects.create_user(
        email="facebook-fallback@example.com",
        full_name="Facebook Fallback User",
        password="StrongPass123!",
    )
    social_account = SocialAccount.objects.create(
        user=user,
        provider="facebook",
        uid="fb-fallback",
    )
    SocialToken.objects.create(account=social_account, token="short-lived-token")
    responses.add(
        responses.GET,
        FACEBOOK_TOKEN_EXCHANGE_URL,
        json={"error": {"message": "Exchange temporarily failed"}},
        status=400,
    )
    responses.add(
        responses.GET,
        FACEBOOK_PAGES_URL,
        json={
            "data": [
                {
                    "id": "fallback-page",
                    "name": "Fallback Page",
                    "access_token": "fallback-page-token",
                }
            ]
        },
        status=200,
    )

    with patch("apps.profiles.services.logger.warning") as warning:
        pages = fetch_facebook_pages(social_account)

    assert pages[0]["id"] == "fallback-page"
    assert "access_token=short-lived-token" in responses.calls[1].request.url
    warning.assert_called()
    assert "Facebook long-lived token exchange failed" in warning.call_args.args[0]


@responses.activate
def test_fetch_linkedin_organizations_returns_parsed_organization_list(
    django_user_model,
):
    user = django_user_model.objects.create_user(
        email="linkedin-orgs@example.com",
        full_name="LinkedIn Orgs User",
        password="StrongPass123!",
    )
    social_account = SocialAccount.objects.create(
        user=user,
        provider="linkedin_oauth2",
        uid="linkedin-user",
    )
    SocialToken.objects.create(account=social_account, token="linkedin-token")
    responses.add(
        responses.GET,
        LINKEDIN_ACLS_URL,
        json={
            "elements": [
                {"organizationalTarget": "urn:li:organization:12345"},
                {"organizationalTarget": "urn:li:organization:67890"},
            ]
        },
        status=200,
    )
    responses.add(
        responses.GET,
        LINKEDIN_ORGANIZATION_URL.format(organization_id="12345"),
        json={"localizedName": "Publishque Labs"},
        status=200,
    )
    responses.add(
        responses.GET,
        LINKEDIN_ORGANIZATION_URL.format(organization_id="67890"),
        json={"localizedName": "Publishque Studio"},
        status=200,
    )

    organizations = fetch_linkedin_organizations(social_account)

    assert organizations == [
        {"id": "urn:li:organization:12345", "name": "Publishque Labs"},
        {"id": "urn:li:organization:67890", "name": "Publishque Studio"},
    ]
    acl_request = responses.calls[0].request
    assert acl_request.headers["Authorization"] == "Bearer linkedin-token"
    assert acl_request.headers["LinkedIn-Version"] == "202507"
    assert acl_request.headers["X-Restli-Protocol-Version"] == "2.0.0"
