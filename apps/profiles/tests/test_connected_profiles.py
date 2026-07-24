import pytest
from allauth.socialaccount.models import SocialAccount, SocialLogin, SocialToken
from allauth.socialaccount.signals import social_account_added
from django.urls import reverse

from apps.profiles.models import ConnectedProfile


pytestmark = pytest.mark.django_db


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
    assert "Connect Pinterest" in content
    assert "bg-[#2E2A5C]" in content
    assert "text-white" in content


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
