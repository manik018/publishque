import base64
import logging
import mimetypes

import requests

from apps.profiles.services import get_valid_pinterest_token

from .base import BasePlatformAdapter


logger = logging.getLogger("publishque.posts.adapters.pinterest")
PINTEREST_PINS_URL = "https://api.pinterest.com/v5/pins"


class PinterestAdapter(BasePlatformAdapter):
    def publish(self, post_target):
        if not post_target.board_id:
            raise ValueError("Pinterest board selection is required.")
        if not post_target.post.media:
            raise ValueError("Pinterest publishing requires an image.")

        access_token = get_valid_pinterest_token(post_target.connected_profile)
        media_path = post_target.post.media.path
        content_type, _ = mimetypes.guess_type(media_path)
        if not content_type or not content_type.startswith("image/"):
            raise ValueError("Pinterest publishing requires an image media file.")

        with post_target.post.media.open("rb") as media_file:
            encoded_media = base64.b64encode(media_file.read()).decode("ascii")

        payload = {
            "board_id": post_target.board_id,
            "title": self.get_title(post_target),
            "description": post_target.post.content,
            "media_source": {
                "source_type": "image_base64",
                "content_type": content_type,
                "data": encoded_media,
            },
        }
        response = requests.post(
            PINTEREST_PINS_URL,
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(parse_pinterest_error(response)) from exc

        pin_id = response.json().get("id")
        logger.info("Published post target %s to Pinterest pin %s", post_target.pk, pin_id)
        return True

    def get_title(self, post_target):
        return post_target.post.title.strip() or post_target.post.content.strip()[:100]


def parse_pinterest_error(response):
    try:
        data = response.json()
    except ValueError:
        data = {}

    message = (
        data.get("message")
        or data.get("error", {}).get("message")
        or data.get("error_description")
        or response.text
        or "Pinterest API request failed."
    )
    return f"Pinterest API error ({response.status_code}): {message}"
