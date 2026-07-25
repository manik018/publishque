import logging

import requests
from allauth.socialaccount.models import SocialToken
from django.conf import settings
from django.utils import timezone


logger = logging.getLogger("publishque.profiles.services")
PINTEREST_TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"
PINTEREST_BOARDS_URL = "https://api.pinterest.com/v5/boards"
FACEBOOK_PAGES_URL = "https://graph.facebook.com/v19.0/me/accounts"
FACEBOOK_TOKEN_EXCHANGE_URL = "https://graph.facebook.com/v19.0/oauth/access_token"


class PinterestTokenError(Exception):
    pass


class PinterestBoardFetchError(Exception):
    pass


class FacebookPageFetchError(Exception):
    pass


def get_social_token(connected_profile):
    try:
        return SocialToken.objects.get(account=connected_profile.social_account)
    except SocialToken.DoesNotExist as exc:
        raise PinterestTokenError("Pinterest token not found. Reconnect the account.") from exc


def token_needs_refresh(social_token):
    if not social_token.expires_at:
        return False
    return social_token.expires_at <= timezone.now() + timezone.timedelta(minutes=5)


def get_valid_pinterest_token(connected_profile):
    social_token = get_social_token(connected_profile)
    if not token_needs_refresh(social_token):
        return social_token.token

    if not social_token.token_secret:
        raise PinterestTokenError("Pinterest refresh token is missing. Reconnect the account.")

    response = requests.post(
        PINTEREST_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": social_token.token_secret,
        },
        auth=(
            settings.SOCIALACCOUNT_PROVIDERS["pinterest"]["APP"]["client_id"],
            settings.SOCIALACCOUNT_PROVIDERS["pinterest"]["APP"]["secret"],
        ),
        timeout=15,
    )
    if not response.ok:
        logger.warning(
            "Pinterest token refresh failed for connected profile %s: %s",
            connected_profile.pk,
            response.text,
        )
        raise PinterestTokenError("Pinterest token refresh failed. Reconnect the account.")

    data = response.json()
    access_token = data.get("access_token")
    if not access_token:
        raise PinterestTokenError("Pinterest token refresh response did not include an access token.")

    social_token.token = access_token
    if data.get("refresh_token"):
        social_token.token_secret = data["refresh_token"]
    expires_in = data.get("expires_in")
    if expires_in:
        social_token.expires_at = timezone.now() + timezone.timedelta(seconds=int(expires_in))
    social_token.save(update_fields=["token", "token_secret", "expires_at"])
    return social_token.token


def fetch_pinterest_boards(connected_profile):
    token = get_valid_pinterest_token(connected_profile)
    response = requests.get(
        PINTEREST_BOARDS_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    if not response.ok:
        logger.warning(
            "Pinterest board fetch failed for connected profile %s: %s",
            connected_profile.pk,
            response.text,
        )
        raise PinterestBoardFetchError("Could not load Pinterest boards. Reconnect the account and try again.")

    items = response.json().get("items", [])
    return [
        {"id": item["id"], "name": item.get("name", "Untitled board")}
        for item in items
        if item.get("id")
    ]


def fetch_facebook_pages(social_account):
    try:
        social_token = SocialToken.objects.get(account=social_account)
    except SocialToken.DoesNotExist as exc:
        raise FacebookPageFetchError(
            "Facebook token not found. Reconnect the account."
        ) from exc

    access_token = get_long_lived_facebook_user_token(social_account, social_token)

    response = requests.get(
        FACEBOOK_PAGES_URL,
        params={
            "access_token": access_token,
            "fields": "id,name,access_token,picture",
        },
        timeout=15,
    )
    if not response.ok:
        logger.warning(
            "Facebook page fetch failed for social account %s: %s",
            social_account.pk,
            response.text,
        )
        raise FacebookPageFetchError(
            "Could not load Facebook Pages. Reconnect the account and try again."
        )

    pages = []
    for item in response.json().get("data", []):
        page_id = item.get("id")
        access_token = item.get("access_token")
        if not page_id or not access_token:
            continue
        picture = item.get("picture", {}).get("data", {})
        pages.append(
            {
                "id": page_id,
                "name": item.get("name", "Untitled Page"),
                "access_token": access_token,
                "picture_url": picture.get("url", ""),
            }
        )
    return pages


def get_long_lived_facebook_user_token(social_account, social_token=None):
    if social_token is None:
        try:
            social_token = SocialToken.objects.get(account=social_account)
        except SocialToken.DoesNotExist as exc:
            raise FacebookPageFetchError(
                "Facebook token not found. Reconnect the account."
            ) from exc

    response = requests.get(
        FACEBOOK_TOKEN_EXCHANGE_URL,
        params={
            "grant_type": "fb_exchange_token",
            "client_id": settings.SOCIALACCOUNT_PROVIDERS["facebook"]["APP"][
                "client_id"
            ],
            "client_secret": settings.SOCIALACCOUNT_PROVIDERS["facebook"]["APP"][
                "secret"
            ],
            "fb_exchange_token": social_token.token,
        },
        timeout=15,
    )
    if not response.ok:
        # Falling back allows Page connection to proceed when Facebook's token
        # exchange is temporarily unavailable; publishing will still surface
        # revoked/expired token issues through the normal retry path later.
        logger.warning(
            "Facebook long-lived token exchange failed for social account %s: %s",
            social_account.pk,
            response.text,
        )
        return social_token.token

    access_token = response.json().get("access_token")
    if not access_token:
        logger.warning(
            "Facebook long-lived token exchange returned no access token for social account %s",
            social_account.pk,
        )
        return social_token.token

    social_token.token = access_token
    expires_in = response.json().get("expires_in")
    if expires_in:
        social_token.expires_at = timezone.now() + timezone.timedelta(
            seconds=int(expires_in)
        )
    social_token.save(update_fields=["token", "expires_at"])
    return access_token
