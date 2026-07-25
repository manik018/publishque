import logging
import mimetypes

import requests

from .base import BasePlatformAdapter


logger = logging.getLogger("publishque.posts.adapters.facebook")
FACEBOOK_GRAPH_BASE_URL = "https://graph.facebook.com/v19.0"


class FacebookAdapter(BasePlatformAdapter):
    def publish(self, post_target):
        connected_profile = post_target.connected_profile
        page_id = connected_profile.platform_account_id
        access_token = connected_profile.page_access_token
        if not page_id:
            raise ValueError("Facebook Page ID is missing.")
        if not access_token:
            raise ValueError("Facebook Page access token is missing. Reconnect the Page.")

        if self.has_image_media(post_target):
            response = self.publish_photo(post_target, page_id, access_token)
        else:
            response = self.publish_feed(post_target, page_id, access_token)

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(parse_facebook_error(response)) from exc

        data = response.json()
        graph_id = data.get("post_id") or data.get("id")
        logger.info(
            "Published post target %s to Facebook object %s",
            post_target.pk,
            graph_id,
        )
        return True

    def has_image_media(self, post_target):
        media = post_target.post.media
        if not media:
            return False
        content_type, _ = mimetypes.guess_type(media.name)
        return bool(content_type and content_type.startswith("image/"))

    def publish_feed(self, post_target, page_id, access_token):
        return requests.post(
            f"{FACEBOOK_GRAPH_BASE_URL}/{page_id}/feed",
            data={
                "message": post_target.post.content,
                "access_token": access_token,
            },
            timeout=15,
        )

    def publish_photo(self, post_target, page_id, access_token):
        media = post_target.post.media
        content_type, _ = mimetypes.guess_type(media.name)
        with media.open("rb") as media_file:
            return requests.post(
                f"{FACEBOOK_GRAPH_BASE_URL}/{page_id}/photos",
                data={
                    "caption": post_target.post.content,
                    "access_token": access_token,
                },
                files={
                    "source": (
                        media.name.rsplit("/", 1)[-1],
                        media_file,
                        content_type or "application/octet-stream",
                    )
                },
                timeout=15,
            )


def parse_facebook_error(response):
    try:
        data = response.json()
    except ValueError:
        data = {}

    message = (
        data.get("error", {}).get("message")
        or data.get("message")
        or response.text
        or "Facebook Graph API request failed."
    )
    return f"Facebook Graph API error ({response.status_code}): {message}"
