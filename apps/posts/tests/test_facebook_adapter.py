import pytest
import responses
from allauth.socialaccount.models import SocialAccount
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone

from apps.posts.adapters.facebook import FACEBOOK_GRAPH_BASE_URL, FacebookAdapter
from apps.posts.models import Post, PostTarget
from apps.profiles.models import ConnectedProfile


pytestmark = pytest.mark.django_db


def create_facebook_target(user, tmp_path, media=None):
    social_account = SocialAccount.objects.create(
        user=user,
        provider="facebook",
        uid="fb-user",
    )
    profile = ConnectedProfile.objects.create(
        user=user,
        platform=ConnectedProfile.Platform.FACEBOOK,
        social_account=social_account,
        display_name="Launch Page",
        platform_account_id="page-123",
        page_access_token="page-access-token",
    )
    with override_settings(MEDIA_ROOT=tmp_path):
        post = Post.objects.create(
            owner=user,
            content="Facebook post content",
            media=media,
        )
        target = PostTarget.objects.create(
            post=post,
            connected_profile=profile,
            scheduled_time=timezone.now(),
        )
    return target


@responses.activate
def test_facebook_adapter_publish_with_media_posts_to_photos(
    django_user_model, tmp_path
):
    user = django_user_model.objects.create_user(
        email="facebook-photo@example.com",
        full_name="Facebook Photo User",
        password="StrongPass123!",
    )
    media = SimpleUploadedFile(
        "facebook.png",
        b"facebook-image-bytes",
        content_type="image/png",
    )
    target = create_facebook_target(user, tmp_path, media=media)
    responses.add(
        responses.POST,
        f"{FACEBOOK_GRAPH_BASE_URL}/page-123/photos",
        json={"id": "photo-123", "post_id": "post-123"},
        status=200,
    )

    with override_settings(MEDIA_ROOT=tmp_path):
        assert FacebookAdapter().publish(target) is True

    request = responses.calls[0].request
    body = request.body.decode("utf-8", errors="ignore")
    assert request.url == f"{FACEBOOK_GRAPH_BASE_URL}/page-123/photos"
    assert "multipart/form-data" in request.headers["Content-Type"]
    assert "Facebook post content" in body
    assert "page-access-token" in body
    assert "facebook-image-bytes" in body


@responses.activate
def test_facebook_adapter_publish_without_media_posts_to_feed(
    django_user_model, tmp_path
):
    user = django_user_model.objects.create_user(
        email="facebook-feed@example.com",
        full_name="Facebook Feed User",
        password="StrongPass123!",
    )
    target = create_facebook_target(user, tmp_path)
    responses.add(
        responses.POST,
        f"{FACEBOOK_GRAPH_BASE_URL}/page-123/feed",
        json={"id": "feed-post-123"},
        status=200,
    )

    assert FacebookAdapter().publish(target) is True

    request = responses.calls[0].request
    body = request.body.decode() if isinstance(request.body, bytes) else request.body
    assert request.url == f"{FACEBOOK_GRAPH_BASE_URL}/page-123/feed"
    assert "message=Facebook+post+content" in body
    assert "access_token=page-access-token" in body


@responses.activate
def test_facebook_adapter_publish_raises_descriptive_error(
    django_user_model, tmp_path
):
    user = django_user_model.objects.create_user(
        email="facebook-error@example.com",
        full_name="Facebook Error User",
        password="StrongPass123!",
    )
    target = create_facebook_target(user, tmp_path)
    responses.add(
        responses.POST,
        f"{FACEBOOK_GRAPH_BASE_URL}/page-123/feed",
        json={
            "error": {
                "message": "The user must be an administrator of the page.",
                "type": "OAuthException",
                "code": 200,
            }
        },
        status=400,
    )

    with pytest.raises(RuntimeError, match="administrator of the page"):
        FacebookAdapter().publish(target)
