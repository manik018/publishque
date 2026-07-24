from unittest.mock import Mock, patch
from datetime import timezone as dt_timezone

import pytest
from allauth.socialaccount.models import SocialAccount
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.notifications.models import Notification
from apps.posts.admin import PostTargetAdmin
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


def create_profile_for_platform(user, platform, uid):
    social_account = SocialAccount.objects.create(
        user=user,
        provider=platform,
        uid=uid,
    )
    return ConnectedProfile.objects.create(
        user=user,
        platform=platform,
        social_account=social_account,
        display_name=f"{platform.title()} Profile",
        platform_account_id=uid,
    )


def create_post_with_target(
    user,
    profile,
    title,
    content,
    status=PostTarget.Status.PENDING,
    scheduled_time=None,
):
    post = Post.objects.create(owner=user, title=title, content=content)
    PostTarget.objects.create(
        post=post,
        connected_profile=profile,
        scheduled_time=scheduled_time or timezone.now() + timezone.timedelta(days=1),
        status=status,
    )
    return post


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
            "title": "Optional title",
            "content": "A scheduled post",
            "connected_profiles": [profile_one.pk, profile_two.pk],
            "scheduled_time": scheduled_time.strftime("%Y-%m-%dT%H:%M"),
            f"board_id_{profile_one.pk}": "board-1",
            f"board_id_{profile_two.pk}": "board-2",
            f"board_name_{profile_one.pk}": "Board One",
            f"board_name_{profile_two.pk}": "Board Two",
            "media": SimpleUploadedFile(
                "pin.png",
                b"fake-image-content",
                content_type="image/png",
            ),
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("posts:list")
    queued_messages = [message.message for message in response.wsgi_request._messages]
    assert "Post scheduled successfully." in queued_messages
    post = Post.objects.get(owner=user)
    assert post.content == "A scheduled post"
    assert post.title == "Optional title"
    assert post.targets.count() == 2
    assert set(post.targets.values_list("connected_profile_id", flat=True)) == {
        profile_one.pk,
        profile_two.pk,
    }
    assert set(post.targets.values_list("board_id", flat=True)) == {"board-1", "board-2"}


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


def test_post_list_search_filters_by_title_or_content(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="search@example.com",
        full_name="Search User",
        password="StrongPass123!",
    )
    profile = create_connected_profile(user, "search-pin", "Search Pins")
    create_post_with_target(user, profile, "Launch plan", "Pinterest roadmap")
    create_post_with_target(user, profile, "Weekly update", "Team notes")
    client.force_login(user)

    response = client.get(reverse("posts:list"), {"q": "roadmap"})

    content = response.content.decode()
    assert response.status_code == 200
    assert "Launch plan" in content
    assert "Weekly update" not in content
    assert "Search: roadmap" in content


def test_post_list_status_filter_returns_matching_posts(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="status@example.com",
        full_name="Status User",
        password="StrongPass123!",
    )
    profile = create_connected_profile(user, "status-pin", "Status Pins")
    create_post_with_target(
        user, profile, "Failed post", "Needs attention", status=PostTarget.Status.FAILED
    )
    create_post_with_target(
        user, profile, "Pending post", "Waiting", status=PostTarget.Status.PENDING
    )
    client.force_login(user)

    response = client.get(reverse("posts:list"), {"status": PostTarget.Status.FAILED})

    content = response.content.decode()
    assert "Failed post" in content
    assert "Pending post" not in content
    assert "Status: Failed" in content


def test_post_list_platform_filter_returns_matching_posts(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="platform@example.com",
        full_name="Platform User",
        password="StrongPass123!",
    )
    pinterest = create_profile_for_platform(user, ConnectedProfile.Platform.PINTEREST, "pin-platform")
    linkedin = create_profile_for_platform(user, ConnectedProfile.Platform.LINKEDIN, "li-platform")
    create_post_with_target(user, pinterest, "Pinterest post", "Pins")
    create_post_with_target(user, linkedin, "LinkedIn post", "Network")
    client.force_login(user)

    response = client.get(
        reverse("posts:list"), {"platform": ConnectedProfile.Platform.LINKEDIN}
    )

    content = response.content.decode()
    assert "LinkedIn post" in content
    assert "Pinterest post" not in content
    assert "Platform: LinkedIn" in content


def test_post_list_date_range_filter_bounds_results(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="dates@example.com",
        full_name="Dates User",
        password="StrongPass123!",
    )
    profile = create_connected_profile(user, "dates-pin", "Dates Pins")
    create_post_with_target(
        user,
        profile,
        "Inside range",
        "Inside",
        scheduled_time=timezone.datetime(2026, 8, 10, 12, tzinfo=dt_timezone.utc),
    )
    create_post_with_target(
        user,
        profile,
        "Outside range",
        "Outside",
        scheduled_time=timezone.datetime(2026, 8, 20, 12, tzinfo=dt_timezone.utc),
    )
    client.force_login(user)

    response = client.get(
        reverse("posts:list"), {"date_from": "2026-08-01", "date_to": "2026-08-15"}
    )

    content = response.content.decode()
    assert "Inside range" in content
    assert "Outside range" not in content
    assert "From: 2026-08-01" in content
    assert "To: 2026-08-15" in content


def test_post_list_combines_filters_with_and_logic(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="and@example.com",
        full_name="And User",
        password="StrongPass123!",
    )
    pinterest = create_profile_for_platform(user, ConnectedProfile.Platform.PINTEREST, "and-pin")
    linkedin = create_profile_for_platform(user, ConnectedProfile.Platform.LINKEDIN, "and-li")
    create_post_with_target(
        user,
        pinterest,
        "Launch failed pin",
        "Campaign",
        status=PostTarget.Status.FAILED,
    )
    create_post_with_target(
        user,
        linkedin,
        "Launch failed linkedin",
        "Campaign",
        status=PostTarget.Status.FAILED,
    )
    create_post_with_target(
        user,
        pinterest,
        "Launch sent pin",
        "Campaign",
        status=PostTarget.Status.SENT,
    )
    client.force_login(user)

    response = client.get(
        reverse("posts:list"),
        {
            "q": "Launch",
            "status": PostTarget.Status.FAILED,
            "platform": ConnectedProfile.Platform.PINTEREST,
        },
    )

    content = response.content.decode()
    assert "Launch failed pin" in content
    assert "Launch failed linkedin" not in content
    assert "Launch sent pin" not in content


def test_post_list_pagination_returns_expected_page_counts(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="pagination@example.com",
        full_name="Pagination User",
        password="StrongPass123!",
    )
    profile = create_connected_profile(user, "pagination-pin", "Pagination Pins")
    for index in range(21):
        create_post_with_target(user, profile, f"Post {index}", f"Content {index}")
    client.force_login(user)

    first_page = client.get(reverse("posts:list"))
    second_page = client.get(reverse("posts:list"), {"page": 2})

    assert "Page 1 of 2" in first_page.content.decode()
    assert "Page 2 of 2" in second_page.content.decode()


def test_post_list_filters_do_not_leak_other_users_posts(client, django_user_model):
    owner = django_user_model.objects.create_user(
        email="scoped@example.com",
        full_name="Scoped User",
        password="StrongPass123!",
    )
    other_user = django_user_model.objects.create_user(
        email="scoped-other@example.com",
        full_name="Scoped Other User",
        password="StrongPass123!",
    )
    owner_profile = create_connected_profile(owner, "scoped-pin", "Scoped Pins")
    other_profile = create_connected_profile(other_user, "scoped-other-pin", "Scoped Other Pins")
    create_post_with_target(owner, owner_profile, "Visible scoped", "Owner")
    create_post_with_target(
        other_user,
        other_profile,
        "Secret failed scoped",
        "Other",
        status=PostTarget.Status.FAILED,
    )
    client.force_login(owner)

    response = client.get(
        reverse("posts:list"),
        {"q": "scoped", "status": PostTarget.Status.FAILED},
    )

    content = response.content.decode()
    assert "Secret failed scoped" not in content
    assert "Visible scoped" not in content


def test_filter_state_persists_in_url_query_string(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="roundtrip@example.com",
        full_name="Round Trip User",
        password="StrongPass123!",
    )
    profile = create_connected_profile(user, "roundtrip-pin", "Roundtrip Pins")
    create_post_with_target(
        user,
        profile,
        "Roundtrip failed",
        "Roundtrip content",
        status=PostTarget.Status.FAILED,
    )
    client.force_login(user)

    response = client.get(
        reverse("posts:list"),
        {
            "q": "Roundtrip",
            "status": PostTarget.Status.FAILED,
            "platform": ConnectedProfile.Platform.PINTEREST,
        },
    )

    content = response.content.decode()
    assert 'value="Roundtrip"' in content
    assert 'value="failed" selected' in content
    assert 'value="pinterest" selected' in content
    assert "q=Roundtrip" in content
    assert "status=failed" in content
    assert "platform=pinterest" in content


def test_composer_rejects_pinterest_target_without_board(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="missing-board@example.com",
        full_name="Missing Board User",
        password="StrongPass123!",
    )
    profile = create_connected_profile(user, "missing-board-pin", "Missing Board Pins")
    client.force_login(user)

    response = client.post(
        reverse("posts:new"),
        {
            "content": "A scheduled post",
            "connected_profiles": [profile.pk],
            "scheduled_time": (
                timezone.now() + timezone.timedelta(days=1)
            ).strftime("%Y-%m-%dT%H:%M"),
            "media": SimpleUploadedFile(
                "pin.png",
                b"fake-image-content",
                content_type="image/png",
            ),
        },
    )

    assert response.status_code == 200
    assert "Select a Pinterest board" in response.content.decode()
    assert Post.objects.filter(owner=user).count() == 0


def test_composer_rejects_pinterest_target_without_media(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="missing-media@example.com",
        full_name="Missing Media User",
        password="StrongPass123!",
    )
    profile = create_connected_profile(user, "missing-media-pin", "Missing Media Pins")
    client.force_login(user)

    response = client.post(
        reverse("posts:new"),
        {
            "content": "A scheduled post",
            "connected_profiles": [profile.pk],
            "scheduled_time": (
                timezone.now() + timezone.timedelta(days=1)
            ).strftime("%Y-%m-%dT%H:%M"),
            f"board_id_{profile.pk}": "board-1",
        },
    )

    assert response.status_code == 200
    assert "Pinterest targets require an image upload." in response.content.decode()
    assert Post.objects.filter(owner=user).count() == 0


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
    notification = Notification.objects.get(related_post_target=post_target)
    assert notification.level == Notification.Level.SUCCESS
    assert "published successfully" in notification.message


def test_check_scheduled_posts_retries_and_reschedules_on_adapter_error(
    django_user_model, settings
):
    settings.PUBLISHQUE_MAX_RETRY_ATTEMPTS = 3
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
    original_scheduled_time = post_target.scheduled_time
    adapter = Mock()
    adapter.publish.side_effect = RuntimeError("Pinterest unavailable")

    with patch("apps.posts.tasks.get_adapter_for_platform", return_value=adapter):
        processed = check_scheduled_posts()

    post_target.refresh_from_db()
    assert processed == 1
    assert post_target.status == PostTarget.Status.PENDING
    assert post_target.sent_at is None
    assert post_target.retry_count == 1
    assert post_target.error_message == "Pinterest unavailable"
    assert post_target.scheduled_time > original_scheduled_time
    assert post_target.scheduled_time > timezone.now()
    assert Notification.objects.count() == 0


def test_check_scheduled_posts_permanent_failure_creates_notification_and_email(
    django_user_model, settings, mailoutbox
):
    settings.PUBLISHQUE_MAX_RETRY_ATTEMPTS = 3
    user = django_user_model.objects.create_user(
        email="final-fail@example.com",
        full_name="Final Fail User",
        password="StrongPass123!",
    )
    profile = create_connected_profile(user, "final-fail-pin", "Final Fail Pins")
    post = Post.objects.create(owner=user, content="Final failing post")
    post_target = PostTarget.objects.create(
        post=post,
        connected_profile=profile,
        scheduled_time=timezone.now() - timezone.timedelta(minutes=1),
        retry_count=2,
    )
    adapter = Mock()
    adapter.publish.side_effect = RuntimeError("Pinterest unavailable")

    with patch("apps.posts.tasks.get_adapter_for_platform", return_value=adapter):
        processed = check_scheduled_posts()

    post_target.refresh_from_db()
    assert processed == 1
    assert post_target.status == PostTarget.Status.FAILED
    assert post_target.retry_count == 3
    assert post_target.error_message == "Pinterest unavailable"

    notification = Notification.objects.get(related_post_target=post_target)
    assert notification.level == Notification.Level.ERROR
    assert "failed to publish after 3 attempts" in notification.message
    assert len(mailoutbox) == 1
    assert "could not publish" in mailoutbox[0].subject


def test_admin_retry_action_resets_failed_posts(rf, django_user_model):
    user = django_user_model.objects.create_user(
        email="admin-retry@example.com",
        full_name="Admin Retry User",
        password="StrongPass123!",
    )
    profile = create_connected_profile(user, "admin-retry-pin", "Admin Retry Pins")
    post = Post.objects.create(owner=user, content="Retry from admin")
    failed_target = PostTarget.objects.create(
        post=post,
        connected_profile=profile,
        scheduled_time=timezone.now() - timezone.timedelta(days=1),
        status=PostTarget.Status.FAILED,
        retry_count=3,
        error_message="Permanent failure",
    )
    request = rf.post("/")
    request.user = user
    setattr(request, "session", {})
    messages = FallbackStorage(request)
    setattr(request, "_messages", messages)
    admin = PostTargetAdmin(PostTarget, AdminSite())

    admin.retry_selected_failed_posts(request, PostTarget.objects.filter(pk=failed_target.pk))

    failed_target.refresh_from_db()
    assert failed_target.status == PostTarget.Status.PENDING
    assert failed_target.retry_count == 0
    assert failed_target.error_message == ""
    assert failed_target.scheduled_time <= timezone.now()
