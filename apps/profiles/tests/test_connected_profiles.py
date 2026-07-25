import pytest
import responses
from allauth.socialaccount.models import SocialAccount, SocialLogin, SocialToken
from allauth.socialaccount.signals import social_account_added
from django.urls import reverse

from apps.profiles.models import ConnectedProfile
from apps.profiles.services import (
    FACEBOOK_PAGES_URL,
    FACEBOOK_TOKEN_EXCHANGE_URL,
    LINKEDIN_ACLS_URL,
    LINKEDIN_ORGANIZATION_URL,
)


pytestmark = pytest.mark.django_db


def mock_facebook_exchange(access_token="long-lived-user-token", status=200):
    responses.add(
        responses.GET,
        FACEBOOK_TOKEN_EXCHANGE_URL,
        json={"access_token": access_token, "expires_in": 5184000},
        status=status,
    )


def mock_linkedin_organizations(organizations):
    responses.add(
        responses.GET,
        LINKEDIN_ACLS_URL,
        json={
            "elements": [
                {"organizationalTarget": organization["id"]}
                for organization in organizations
            ]
        },
        status=200,
    )
    for organization in organizations:
        organization_id = organization["id"].rsplit(":", 1)[-1]
        responses.add(
            responses.GET,
            LINKEDIN_ORGANIZATION_URL.format(organization_id=organization_id),
            json={"localizedName": organization["name"]},
            status=200,
        )


def test_connected_profiles_page_requires_login(client):
    response = client.get(reverse("profiles:connected_profiles"))

    expected_url = (
        f"{reverse('accounts:login')}?next={reverse('profiles:connected_profiles')}"
    )
    assert response.status_code == 302
    assert response.url == expected_url


def test_connected_profiles_empty_state_connect_button_is_visible(
    client, django_user_model
):
    user = django_user_model.objects.create_user(
        email="empty-profiles@example.com",
        full_name="Empty Profiles User",
        password="StrongPass123!",
    )
    client.force_login(user)

    response = client.get(reverse("profiles:connected_profiles"))

    content = response.content.decode()
    assert response.status_code == 200
    assert "Connect your first profile" in content
    assert "Connect Facebook" in content
    assert "Connect LinkedIn" in content
    assert "Connect Pinterest" in content
    assert "btn-primary" in content


def test_connected_profiles_page_shows_facebook_and_pinterest_connect_options(
    client, django_user_model
):
    user = django_user_model.objects.create_user(
        email="connect-options@example.com",
        full_name="Connect Options User",
        password="StrongPass123!",
    )
    client.force_login(user)

    response = client.get(reverse("profiles:connected_profiles"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Connect Facebook" in content
    assert "Connect LinkedIn" in content
    assert "Connect Pinterest" in content
    assert "/social/facebook/login/" in content
    assert "/social/pinterest/login/" in content


def test_connected_profile_created_when_social_account_is_added(
    rf, django_user_model
):
    user = django_user_model.objects.create_user(
        email="pinner@example.com",
        full_name="Pinner User",
        password="StrongPass123!",
    )
    social_account = SocialAccount.objects.create(
        user=user,
        provider="pinterest",
        uid="pin-123",
        extra_data={"name": "Publishque Pins"},
    )
    sociallogin = SocialLogin(account=social_account, user=user)

    social_account_added.send(
        sender=SocialLogin,
        request=rf.get("/"),
        sociallogin=sociallogin,
    )

    connected_profile = ConnectedProfile.objects.get(
        user=user,
        platform=ConnectedProfile.Platform.PINTEREST,
        platform_account_id="pin-123",
    )
    assert connected_profile.social_account == social_account
    assert connected_profile.display_name == "Publishque Pins"


def test_facebook_social_account_added_does_not_create_connected_profile(
    rf, django_user_model
):
    user = django_user_model.objects.create_user(
        email="facebook-signal@example.com",
        full_name="Facebook Signal User",
        password="StrongPass123!",
    )
    social_account = SocialAccount.objects.create(
        user=user,
        provider="facebook",
        uid="fb-user",
        extra_data={"name": "Facebook User"},
    )
    sociallogin = SocialLogin(account=social_account, user=user)

    social_account_added.send(
        sender=SocialLogin,
        request=rf.get("/"),
        sociallogin=sociallogin,
    )

    assert not ConnectedProfile.objects.filter(
        user=user,
        platform=ConnectedProfile.Platform.FACEBOOK,
    ).exists()


def test_linkedin_social_account_added_does_not_create_connected_profile(
    rf, django_user_model
):
    user = django_user_model.objects.create_user(
        email="linkedin-signal@example.com",
        full_name="LinkedIn Signal User",
        password="StrongPass123!",
    )
    social_account = SocialAccount.objects.create(
        user=user,
        provider="linkedin_oauth2",
        uid="linkedin-user",
        extra_data={"name": "LinkedIn User"},
    )
    sociallogin = SocialLogin(account=social_account, user=user)

    social_account_added.send(
        sender=SocialLogin,
        request=rf.get("/"),
        sociallogin=sociallogin,
    )

    assert not ConnectedProfile.objects.filter(
        user=user,
        platform=ConnectedProfile.Platform.LINKEDIN,
    ).exists()


@responses.activate
def test_facebook_single_page_auto_connect_creates_connected_profile(
    client, django_user_model, settings
):
    settings.SOCIALACCOUNT_PROVIDERS["facebook"]["APP"]["client_id"] = "fb-client"
    settings.SOCIALACCOUNT_PROVIDERS["facebook"]["APP"]["secret"] = "fb-secret"
    user = django_user_model.objects.create_user(
        email="single-page@example.com",
        full_name="Single Page User",
        password="StrongPass123!",
    )
    social_account = SocialAccount.objects.create(
        user=user,
        provider="facebook",
        uid="fb-single",
    )
    SocialToken.objects.create(account=social_account, token="user-access-token")
    mock_facebook_exchange()
    responses.add(
        responses.GET,
        FACEBOOK_PAGES_URL,
        json={
            "data": [
                {
                    "id": "single-page",
                    "name": "Single Page",
                    "access_token": "single-page-token",
                }
            ]
        },
        status=200,
    )
    client.force_login(user)

    response = client.get(reverse("profiles:facebook_select_page"))

    assert response.status_code == 302
    assert response.url == reverse("profiles:connected_profiles")
    connected_profile = ConnectedProfile.objects.get(
        user=user,
        platform=ConnectedProfile.Platform.FACEBOOK,
        platform_account_id="single-page",
    )
    assert connected_profile.social_account == social_account
    assert connected_profile.display_name == "Single Page"
    assert connected_profile.page_access_token == "single-page-token"
    assert connected_profile.token_obtained_at is not None


@responses.activate
def test_facebook_multi_page_flow_shows_selection_screen(
    client, django_user_model, settings
):
    settings.SOCIALACCOUNT_PROVIDERS["facebook"]["APP"]["client_id"] = "fb-client"
    settings.SOCIALACCOUNT_PROVIDERS["facebook"]["APP"]["secret"] = "fb-secret"
    user = django_user_model.objects.create_user(
        email="multi-page@example.com",
        full_name="Multi Page User",
        password="StrongPass123!",
    )
    social_account = SocialAccount.objects.create(
        user=user,
        provider="facebook",
        uid="fb-multi",
    )
    SocialToken.objects.create(account=social_account, token="user-access-token")
    mock_facebook_exchange()
    responses.add(
        responses.GET,
        FACEBOOK_PAGES_URL,
        json={
            "data": [
                {"id": "page-1", "name": "Page One", "access_token": "token-one"},
                {"id": "page-2", "name": "Page Two", "access_token": "token-two"},
            ]
        },
        status=200,
    )
    client.force_login(user)

    response = client.get(reverse("profiles:facebook_select_page"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Select a Facebook Page" in content
    assert "Page One" in content
    assert "Page Two" in content
    assert not ConnectedProfile.objects.filter(
        user=user,
        platform=ConnectedProfile.Platform.FACEBOOK,
    ).exists()


@responses.activate
def test_selecting_facebook_page_creates_connected_profile_with_page_token(
    client, django_user_model, settings
):
    settings.SOCIALACCOUNT_PROVIDERS["facebook"]["APP"]["client_id"] = "fb-client"
    settings.SOCIALACCOUNT_PROVIDERS["facebook"]["APP"]["secret"] = "fb-secret"
    user = django_user_model.objects.create_user(
        email="select-page@example.com",
        full_name="Select Page User",
        password="StrongPass123!",
    )
    social_account = SocialAccount.objects.create(
        user=user,
        provider="facebook",
        uid="fb-select",
    )
    SocialToken.objects.create(account=social_account, token="user-access-token")
    mock_facebook_exchange()
    responses.add(
        responses.GET,
        FACEBOOK_PAGES_URL,
        json={
            "data": [
                {"id": "page-1", "name": "Page One", "access_token": "token-one"},
                {"id": "page-2", "name": "Page Two", "access_token": "token-two"},
            ]
        },
        status=200,
    )
    client.force_login(user)

    response = client.post(
        reverse("profiles:facebook_select_page"),
        {"page_id": "page-2"},
    )

    assert response.status_code == 302
    assert response.url == reverse("profiles:connected_profiles")
    connected_profile = ConnectedProfile.objects.get(
        user=user,
        platform=ConnectedProfile.Platform.FACEBOOK,
        platform_account_id="page-2",
    )
    assert connected_profile.social_account == social_account
    assert connected_profile.display_name == "Page Two"
    assert connected_profile.page_access_token == "token-two"
    assert connected_profile.token_obtained_at is not None


@responses.activate
def test_linkedin_single_org_auto_connect_creates_connected_profile(
    client, django_user_model
):
    user = django_user_model.objects.create_user(
        email="single-org@example.com",
        full_name="Single Org User",
        password="StrongPass123!",
    )
    social_account = SocialAccount.objects.create(
        user=user,
        provider="linkedin_oauth2",
        uid="linkedin-single",
    )
    SocialToken.objects.create(account=social_account, token="linkedin-token")
    mock_linkedin_organizations(
        [{"id": "urn:li:organization:12345", "name": "Single Org"}]
    )
    client.force_login(user)

    response = client.get(reverse("profiles:linkedin_select_organization"))

    assert response.status_code == 302
    assert response.url == reverse("profiles:connected_profiles")
    connected_profile = ConnectedProfile.objects.get(
        user=user,
        platform=ConnectedProfile.Platform.LINKEDIN,
        platform_account_id="urn:li:organization:12345",
    )
    assert connected_profile.social_account == social_account
    assert connected_profile.display_name == "Single Org"
    assert connected_profile.page_access_token == "linkedin-token"


@responses.activate
def test_linkedin_multi_org_flow_shows_selection_screen(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="multi-org@example.com",
        full_name="Multi Org User",
        password="StrongPass123!",
    )
    social_account = SocialAccount.objects.create(
        user=user,
        provider="linkedin_oauth2",
        uid="linkedin-multi",
    )
    SocialToken.objects.create(account=social_account, token="linkedin-token")
    mock_linkedin_organizations(
        [
            {"id": "urn:li:organization:12345", "name": "Org One"},
            {"id": "urn:li:organization:67890", "name": "Org Two"},
        ]
    )
    client.force_login(user)

    response = client.get(reverse("profiles:linkedin_select_organization"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Select a LinkedIn Organization" in content
    assert "Org One" in content
    assert "Org Two" in content
    assert not ConnectedProfile.objects.filter(
        user=user,
        platform=ConnectedProfile.Platform.LINKEDIN,
    ).exists()


@responses.activate
def test_selecting_linkedin_org_creates_connected_profile_with_access_token(
    client, django_user_model
):
    user = django_user_model.objects.create_user(
        email="select-org@example.com",
        full_name="Select Org User",
        password="StrongPass123!",
    )
    social_account = SocialAccount.objects.create(
        user=user,
        provider="linkedin_oauth2",
        uid="linkedin-select",
    )
    SocialToken.objects.create(account=social_account, token="linkedin-token")
    mock_linkedin_organizations(
        [
            {"id": "urn:li:organization:12345", "name": "Org One"},
            {"id": "urn:li:organization:67890", "name": "Org Two"},
        ]
    )
    client.force_login(user)

    response = client.post(
        reverse("profiles:linkedin_select_organization"),
        {"organization_id": "urn:li:organization:67890"},
    )

    assert response.status_code == 302
    assert response.url == reverse("profiles:connected_profiles")
    connected_profile = ConnectedProfile.objects.get(
        user=user,
        platform=ConnectedProfile.Platform.LINKEDIN,
        platform_account_id="urn:li:organization:67890",
    )
    assert connected_profile.social_account == social_account
    assert connected_profile.display_name == "Org Two"
    assert connected_profile.page_access_token == "linkedin-token"


def test_disconnect_removes_connected_profile_social_account_and_token(
    client, django_user_model
):
    user = django_user_model.objects.create_user(
        email="disconnect@example.com",
        full_name="Disconnect User",
        password="StrongPass123!",
    )
    social_account = SocialAccount.objects.create(
        user=user,
        provider="pinterest",
        uid="pin-456",
        extra_data={"name": "Disconnect Pins"},
    )
    SocialToken.objects.create(
        account=social_account,
        token="access-token",
    )
    connected_profile = ConnectedProfile.objects.create(
        user=user,
        platform=ConnectedProfile.Platform.PINTEREST,
        social_account=social_account,
        display_name="Disconnect Pins",
        platform_account_id="pin-456",
    )
    client.force_login(user)

    confirm_response = client.get(
        reverse("profiles:disconnect_profile", args=[connected_profile.pk])
    )
    assert confirm_response.status_code == 200

    response = client.post(
        reverse("profiles:disconnect_profile", args=[connected_profile.pk])
    )

    assert response.status_code == 302
    assert response.url == reverse("profiles:connected_profiles")
    queued_messages = [message.message for message in response.wsgi_request._messages]
    assert "Disconnect Pins was disconnected from Pinterest." in queued_messages
    assert not ConnectedProfile.objects.filter(pk=connected_profile.pk).exists()
    assert not SocialAccount.objects.filter(pk=social_account.pk).exists()
    assert not SocialToken.objects.filter(account=social_account).exists()
