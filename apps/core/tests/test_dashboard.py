import pytest
from allauth.socialaccount.models import SocialAccount
from django.urls import reverse

from apps.profiles.models import ConnectedProfile


pytestmark = pytest.mark.django_db


def test_dashboard_loads_for_authenticated_user_and_shows_profile_count(
    client, django_user_model
):
    user = django_user_model.objects.create_user(
        email="dashboard@example.com",
        full_name="Dashboard User",
        password="StrongPass123!",
    )
    social_account = SocialAccount.objects.create(
        user=user,
        provider="pinterest",
        uid="pin-dashboard",
    )
    ConnectedProfile.objects.create(
        user=user,
        platform=ConnectedProfile.Platform.PINTEREST,
        social_account=social_account,
        display_name="Dashboard Pins",
        platform_account_id="pin-dashboard",
    )
    client.force_login(user)

    response = client.get(reverse("dashboard"))

    content = response.content.decode()
    assert response.status_code == 200
    assert "Welcome back, Dashboard User" in content
    assert "Connected Profiles" in content
    assert ">1<" in content


def test_dashboard_redirects_to_login_when_not_authenticated(client):
    response = client.get(reverse("dashboard"))

    assert response.status_code == 302
    assert response.url == f"{reverse('accounts:login')}?next={reverse('dashboard')}"


def test_posts_placeholder_loads_for_authenticated_user(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="posts@example.com",
        full_name="Posts User",
        password="StrongPass123!",
    )
    client.force_login(user)

    response = client.get(reverse("posts:coming_soon"))

    assert response.status_code == 200
    assert "Posts &amp; Scheduler" in response.content.decode()


def test_settings_placeholder_loads_for_authenticated_user(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="settings@example.com",
        full_name="Settings User",
        password="StrongPass123!",
    )
    client.force_login(user)

    response = client.get(reverse("settings"))

    assert response.status_code == 200
    assert "Settings" in response.content.decode()
