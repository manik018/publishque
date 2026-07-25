import json

import pytest
import responses
from allauth.socialaccount.models import SocialAccount
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone

from apps.posts.adapters.linkedin import (
    LINKEDIN_IMAGES_URL,
    LINKEDIN_POSTS_URL,
    LinkedInAdapter,
)
from apps.posts.models import Post, PostTarget
from apps.profiles.models import ConnectedProfile


pytestmark = pytest.mark.django_db


def create_linkedin_target(user, tmp_path, media=None):
    social_account = SocialAccount.objects.create(
        user=user,
        provider="linkedin_oauth2",
        uid="linkedin-user",
    )
    profile = ConnectedProfile.objects.create(
        user=user,
        platform=ConnectedProfile.Platform.LINKEDIN,
        social_account=social_account,
        display_name="Publishque Labs",
        platform_account_id="urn:li:organization:12345",
        page_access_token="linkedin-access-token",
    )
    with override_settings(MEDIA_ROOT=tmp_path):
        post = Post.objects.create(
            owner=user,
            content="LinkedIn post content",
            media=media,
        )
        target = PostTarget.objects.create(
            post=post,
            connected_profile=profile,
            scheduled_time=timezone.now(),
        )
    return target


@responses.activate
def test_linkedin_adapter_publish_without_media_sends_payload_and_returns_true(
    django_user_model, tmp_path
):
    user = django_user_model.objects.create_user(
        email="linkedin-text@example.com",
        full_name="LinkedIn Text User",
        password="StrongPass123!",
    )
    target = create_linkedin_target(user, tmp_path)
    responses.add(
        responses.POST,
        LINKEDIN_POSTS_URL,
        json={},
        headers={"x-restli-id": "urn:li:share:abc123"},
        status=201,
    )

    assert LinkedInAdapter().publish(target) is True

    request = responses.calls[0].request
    payload = json.loads(request.body)
    assert request.headers["Authorization"] == "Bearer linkedin-access-token"
    assert request.headers["LinkedIn-Version"] == "202507"
    assert request.headers["X-Restli-Protocol-Version"] == "2.0.0"
    assert payload == {
        "author": "urn:li:organization:12345",
        "commentary": "LinkedIn post content",
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }


@responses.activate
def test_linkedin_adapter_publish_with_media_uploads_image_before_posting(
    django_user_model, tmp_path
):
    user = django_user_model.objects.create_user(
        email="linkedin-image@example.com",
        full_name="LinkedIn Image User",
        password="StrongPass123!",
    )
    media = SimpleUploadedFile(
        "linkedin.png",
        b"linkedin-image-bytes",
        content_type="image/png",
    )
    target = create_linkedin_target(user, tmp_path, media=media)
    responses.add(
        responses.POST,
        LINKEDIN_IMAGES_URL,
        json={
            "value": {
                "uploadUrl": "https://upload.linkedin.test/image",
                "image": "urn:li:image:image123",
            }
        },
        status=200,
    )
    responses.add(
        responses.PUT,
        "https://upload.linkedin.test/image",
        body="",
        status=201,
    )
    responses.add(
        responses.POST,
        LINKEDIN_POSTS_URL,
        json={},
        headers={"x-restli-id": "urn:li:share:image-post"},
        status=201,
    )

    with override_settings(MEDIA_ROOT=tmp_path):
        assert LinkedInAdapter().publish(target) is True

    initialize_payload = json.loads(responses.calls[0].request.body)
    assert initialize_payload == {
        "initializeUploadRequest": {"owner": "urn:li:organization:12345"}
    }
    assert responses.calls[1].request.body == b"linkedin-image-bytes"
    post_payload = json.loads(responses.calls[2].request.body)
    assert post_payload["content"] == {"media": {"id": "urn:li:image:image123"}}
    assert post_payload["author"] == "urn:li:organization:12345"


@responses.activate
def test_linkedin_adapter_publish_raises_descriptive_error(
    django_user_model, tmp_path
):
    user = django_user_model.objects.create_user(
        email="linkedin-error@example.com",
        full_name="LinkedIn Error User",
        password="StrongPass123!",
    )
    target = create_linkedin_target(user, tmp_path)
    responses.add(
        responses.POST,
        LINKEDIN_POSTS_URL,
        json={"message": "Organization author is not authorized."},
        status=403,
    )

    with pytest.raises(RuntimeError, match="Organization author is not authorized"):
        LinkedInAdapter().publish(target)
