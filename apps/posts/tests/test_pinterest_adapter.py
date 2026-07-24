import base64
import json

import pytest
import responses
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone

from apps.posts.adapters.pinterest import PINTEREST_PINS_URL, PinterestAdapter
from apps.posts.models import Post, PostTarget
from apps.profiles.models import ConnectedProfile


pytestmark = pytest.mark.django_db


def create_target(user, tmp_path):
    social_account = SocialAccount.objects.create(
        user=user,
        provider="pinterest",
        uid="pin-adapter",
    )
    profile = ConnectedProfile.objects.create(
        user=user,
        platform=ConnectedProfile.Platform.PINTEREST,
        social_account=social_account,
        display_name="Adapter Pins",
        platform_account_id="pin-adapter",
    )
    SocialToken.objects.create(
        account=social_account,
        token="valid-token",
        token_secret="refresh-token",
        expires_at=timezone.now() + timezone.timedelta(hours=1),
    )
    with override_settings(MEDIA_ROOT=tmp_path):
        post = Post.objects.create(
            owner=user,
            title="Adapter Title",
            content="Adapter content",
            media=SimpleUploadedFile(
                "pin.png",
                b"image-bytes",
                content_type="image/png",
            ),
        )
        target = PostTarget.objects.create(
            post=post,
            connected_profile=profile,
            scheduled_time=timezone.now(),
            board_id="board-123",
            board_name="Board 123",
        )
    return target


@responses.activate
def test_pinterest_adapter_publish_sends_payload_and_returns_true(
    django_user_model, tmp_path
):
    user = django_user_model.objects.create_user(
        email="adapter@example.com",
        full_name="Adapter User",
        password="StrongPass123!",
    )
    with override_settings(MEDIA_ROOT=tmp_path):
        target = create_target(user, tmp_path)
        responses.add(
            responses.POST,
            PINTEREST_PINS_URL,
            json={"id": "pin-123"},
            status=201,
        )

        assert PinterestAdapter().publish(target) is True

    request = responses.calls[0].request
    assert request.headers["Authorization"] == "Bearer valid-token"
    payload = json.loads(request.body)
    assert payload["board_id"] == "board-123"
    assert payload["title"] == "Adapter Title"
    assert payload["description"] == "Adapter content"
    assert payload["media_source"]["source_type"] == "image_base64"
    assert payload["media_source"]["content_type"] == "image/png"
    assert payload["media_source"]["data"] == base64.b64encode(b"image-bytes").decode(
        "ascii"
    )


@responses.activate
def test_pinterest_adapter_publish_raises_descriptive_error(
    django_user_model, tmp_path
):
    user = django_user_model.objects.create_user(
        email="adapter-error@example.com",
        full_name="Adapter Error User",
        password="StrongPass123!",
    )
    with override_settings(MEDIA_ROOT=tmp_path):
        target = create_target(user, tmp_path)
        responses.add(
            responses.POST,
            PINTEREST_PINS_URL,
            json={"message": "Board not found"},
            status=400,
        )

        with pytest.raises(RuntimeError, match="Board not found"):
            PinterestAdapter().publish(target)
