import pytest
from allauth.socialaccount.models import SocialAccount
from django.urls import reverse

from apps.notifications.models import Notification, NotificationPreference
from apps.posts.models import Post, PostTarget
from apps.profiles.models import ConnectedProfile


pytestmark = pytest.mark.django_db


def test_profile_update_sets_pending_email_and_sends_verification_email(
    client, django_user_model, mailoutbox
):
    user = django_user_model.objects.create_user(
        email="old@example.com",
        full_name="Old Name",
        password="StrongPass123!",
        is_email_verified=True,
    )
    client.force_login(user)

    response = client.post(
        reverse("settings_profile"),
        {
            "full_name": "New Name",
            "email": "new@example.com",
        },
    )

    user.refresh_from_db()
    assert response.status_code == 302
    assert response.url == reverse("settings_profile")
    assert user.full_name == "New Name"
    assert user.email == "old@example.com"
    assert user.pending_email == "new@example.com"
    assert user.is_email_verified is False
    assert len(mailoutbox) == 1
    assert "Verify your new Publishque email address" in mailoutbox[0].subject


def test_password_change_keeps_user_logged_in(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="password@example.com",
        full_name="Password User",
        password="OldStrongPass123!",
    )
    client.force_login(user)

    response = client.post(
        reverse("settings_security"),
        {
            "action": "change_password",
            "old_password": "OldStrongPass123!",
            "new_password1": "NewStrongPass123!",
            "new_password2": "NewStrongPass123!",
        },
    )

    user.refresh_from_db()
    assert response.status_code == 302
    assert response.url == reverse("settings_security")
    assert user.check_password("NewStrongPass123!")
    assert "_auth_user_id" in client.session


def test_account_deletion_cascades_related_data_and_logs_out(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="delete@example.com",
        full_name="Delete User",
        password="StrongPass123!",
    )
    social_account = SocialAccount.objects.create(
        user=user,
        provider="pinterest",
        uid="delete-pin",
    )
    connected_profile = ConnectedProfile.objects.create(
        user=user,
        platform=ConnectedProfile.Platform.PINTEREST,
        social_account=social_account,
        display_name="Delete Pins",
        platform_account_id="delete-pin",
    )
    post = Post.objects.create(owner=user, content="Delete me")
    post_target = PostTarget.objects.create(
        post=post,
        connected_profile=connected_profile,
        scheduled_time="2026-08-01T12:00:00Z",
    )
    Notification.objects.create(
        user=user,
        title="Delete notification",
        message="Delete notification",
        related_post_target=post_target,
    )
    client.force_login(user)

    response = client.post(
        reverse("settings_security"),
        {
            "action": "delete_account",
            "confirm_delete": "DELETE",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("account_deleted")
    assert not django_user_model.objects.filter(pk=user.pk).exists()
    assert not Post.objects.filter(pk=post.pk).exists()
    assert not PostTarget.objects.filter(pk=post_target.pk).exists()
    assert not ConnectedProfile.objects.filter(pk=connected_profile.pk).exists()
    assert not Notification.objects.filter(title="Delete notification").exists()
    assert "_auth_user_id" not in client.session


def test_notification_preferences_save_correctly(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="prefs@example.com",
        full_name="Prefs User",
        password="StrongPass123!",
    )
    client.force_login(user)

    response = client.post(
        reverse("settings_notifications"),
        {
            "email_on_post_success": "on",
            "in_app_on_post_failure": "on",
        },
    )

    preferences = NotificationPreference.objects.get(user=user)
    assert response.status_code == 302
    assert response.url == reverse("settings_notifications")
    assert preferences.email_on_post_success is True
    assert preferences.email_on_post_failure is False
    assert preferences.in_app_on_post_success is False
    assert preferences.in_app_on_post_failure is True
