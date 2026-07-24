from unittest.mock import Mock, patch

import pytest
from allauth.socialaccount.models import SocialAccount
from django.urls import reverse
from django.utils import timezone

from apps.posts.models import Post, PostTarget
from apps.posts.tasks import check_scheduled_posts
from apps.profiles.models import ConnectedProfile


pytestmark = pytest.mark.django_db


def create_connected_profile(user, uid="pin-123", display_name="Pinterest Board"):
    social_account = SocialAccount.objects.create(
        user=user,
        provider="pinterest",
        uid=uid,
    )
    return ConnectedProfile.objects.create(
        user=user,
        platform=ConnectedProfile.Platform.PINTEREST,
        social_account=social_account,
        display_name=display_name,
        platform_account_id=uid,
    )


def test_creating_post_with_targets_works(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="composer@example.com",
        full_name="Composer User",
        password="StrongPass123!",
    )
    profile_one = create_connected_profile(user, "pin-1", "Pins One")
    profile_two = create_connected_profile(user, "pin-2", "Pins Two")
    client.force_login(user)
    scheduled_time = timezone.now() + timezone.timedelta(days=1)

    response = client.post(
        reverse("posts:new"),
        {
            "content": "A scheduled post",
            "connected_profiles": [profile_one.pk, profile_two.pk],
            "scheduled_time": scheduled_time.strftime("%Y-%m-%dT%H:%M"),
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("posts:list")
    post = Post.objects.get(owner=user)
    assert post.content == "A scheduled post"
    assert post.targets.count() == 2
    assert set(post.targets.values_list("connected_profile_id", flat=True)) == {
        profile_one.pk,
        profile_two.pk,
    }


def test_post_list_requires_login(client):
    response = client.get(reverse("posts:list"))

    assert response.status_code == 302
    assert response.url == f"{reverse('accounts:login')}?next={reverse('posts:list')}"


def test_post_list_only_shows_owner_posts(client, django_user_model):
    owner = django_user_model.objects.create_user(
        email="owner@example.com",
        full_name="Owner User",
        password="StrongPass123!",
    )
    other_user = django_user_model.objects.create_user(
        email="other@example.com",
        full_name="Other User",
        password="StrongPass123!",
    )
    owner_profile = create_connected_profile(owner, "owner-pin", "Owner Pins")
    other_profile = create_connected_profile(other_user, "other-pin", "Other Pins")
    owner_post = Post.objects.create(owner=owner, content="Owner-only post")
    other_post = Post.objects.create(owner=other_user, content="Hidden post")
    PostTarget.objects.create(
        post=owner_post,
        connected_profile=owner_profile,
        scheduled_time=timezone.now() + timezone.timedelta(hours=2),
    )
    PostTarget.objects.create(
        post=other_post,
        connected_profile=other_profile,
        scheduled_time=timezone.now() + timezone.timedelta(hours=2),
    )
    client.force_login(owner)

    response = client.get(reverse("posts:list"))

    content = response.content.decode()
    assert response.status_code == 200
    assert "Owner-only post" in content
    assert "Hidden post" not in content


def test_check_scheduled_posts_publishes_due_targets(django_user_model):
    user = django_user_model.objects.create_user(
        email="due@example.com",
        full_name="Due User",
        password="StrongPass123!",
    )
    profile = create_connected_profile(user, "due-pin", "Due Pins")
    post = Post.objects.create(owner=user, content="Due post")
    post_target = PostTarget.objects.create(
        post=post,
        connected_profile=profile,
        scheduled_time=timezone.now() - timezone.timedelta(minutes=1),
    )
    adapter = Mock()
    adapter.publish.return_value = True

    with patch("apps.posts.tasks.get_adapter_for_platform", return_value=adapter):
        processed = check_scheduled_posts()

    post_target.refresh_from_db()
    assert processed == 1
    adapter.publish.assert_called_once()
    assert post_target.status == PostTarget.Status.SENT
    assert post_target.sent_at is not None
    assert post_target.retry_count == 0


def test_check_scheduled_posts_marks_failed_on_adapter_error(django_user_model):
    user = django_user_model.objects.create_user(
        email="fail@example.com",
        full_name="Fail User",
        password="StrongPass123!",
    )
    profile = create_connected_profile(user, "fail-pin", "Fail Pins")
    post = Post.objects.create(owner=user, content="Failing post")
    post_target = PostTarget.objects.create(
        post=post,
        connected_profile=profile,
        scheduled_time=timezone.now() - timezone.timedelta(minutes=1),
    )
    adapter = Mock()
    adapter.publish.side_effect = RuntimeError("Pinterest unavailable")

    with patch("apps.posts.tasks.get_adapter_for_platform", return_value=adapter):
        processed = check_scheduled_posts()

    post_target.refresh_from_db()
    assert processed == 1
    assert post_target.status == PostTarget.Status.FAILED
    assert post_target.sent_at is None
    assert post_target.retry_count == 1
    assert post_target.error_message == "Pinterest unavailable"
