import logging
import mimetypes

import requests

from .base import BasePlatformAdapter


logger = logging.getLogger("publishque.posts.adapters.linkedin")
LINKEDIN_POSTS_URL = "https://api.linkedin.com/rest/posts"
LINKEDIN_IMAGES_URL = "https://api.linkedin.com/rest/images?action=initializeUpload"
LINKEDIN_VERSION = "202507"


class LinkedInAdapter(BasePlatformAdapter):
    def publish(self, post_target):
        connected_profile = post_target.connected_profile
        organization_urn = connected_profile.platform_account_id
        access_token = connected_profile.page_access_token
        if not organization_urn:
            raise ValueError("LinkedIn Organization URN is missing.")
        if not access_token:
            raise ValueError(
                "LinkedIn access token is missing. Reconnect the Organization."
            )

        payload = self.build_post_payload(post_target, organization_urn)
        if self.has_image_media(post_target):
            payload["content"] = {
                "media": {
                    "id": self.upload_image(post_target, organization_urn, access_token)
                }
            }

        response = requests.post(
            LINKEDIN_POSTS_URL,
            json=payload,
            headers={
                **linkedin_headers(access_token),
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(parse_linkedin_error(response)) from exc

        post_urn = response.headers.get("x-restli-id")
        logger.info(
            "Published post target %s to LinkedIn post %s",
            post_target.pk,
            post_urn,
        )
        return True

    def build_post_payload(self, post_target, organization_urn):
        return {
            "author": organization_urn,
            "commentary": post_target.post.content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

    def has_image_media(self, post_target):
        media = post_target.post.media
        if not media:
            return False
        content_type, _ = mimetypes.guess_type(media.name)
        return bool(content_type and content_type.startswith("image/"))

    def upload_image(self, post_target, organization_urn, access_token):
        response = requests.post(
            LINKEDIN_IMAGES_URL,
            json={"initializeUploadRequest": {"owner": organization_urn}},
            headers={
                **linkedin_headers(access_token),
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(parse_linkedin_error(response)) from exc

        value = response.json().get("value", {})
        upload_url = value.get("uploadUrl")
        image_urn = value.get("image")
        if not upload_url or not image_urn:
            raise RuntimeError("LinkedIn image upload initialization was incomplete.")

        media = post_target.post.media
        content_type, _ = mimetypes.guess_type(media.name)
        with media.open("rb") as media_file:
            upload_response = requests.put(
                upload_url,
                data=media_file.read(),
                headers={"Content-Type": content_type or "application/octet-stream"},
                timeout=15,
            )
        try:
            upload_response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(parse_linkedin_error(upload_response)) from exc

        return image_urn


def linkedin_headers(access_token):
    return {
        "Authorization": f"Bearer {access_token}",
        "LinkedIn-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }


def parse_linkedin_error(response):
    try:
        data = response.json()
    except ValueError:
        data = {}

    message = data.get("message") or response.text or "LinkedIn API request failed."
    return f"LinkedIn API error ({response.status_code}): {message}"
