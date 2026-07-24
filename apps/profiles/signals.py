from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.signals import social_account_added
from django.dispatch import receiver

from .models import ConnectedProfile


SUPPORTED_PLATFORMS = {
    "pinterest": ConnectedProfile.Platform.PINTEREST,
}


def get_social_display_name(social_account):
    extra_data = social_account.extra_data or {}
    return (
        extra_data.get("name")
        or extra_data.get("username")
        or extra_data.get("display_name")
        or social_account.user.get_full_name()
        or social_account.user.email
    )


@receiver(social_account_added)
def create_connected_profile(request, sociallogin, **kwargs):
    social_account = sociallogin.account
    platform = SUPPORTED_PLATFORMS.get(social_account.provider)
    if platform is None:
        return

    ConnectedProfile.objects.get_or_create(
        user=social_account.user,
        platform=platform,
        platform_account_id=social_account.uid,
        defaults={
            "social_account": social_account,
            "display_name": get_social_display_name(social_account),
            "is_active": True,
        },
    )


def create_connected_profile_for_social_account(social_account):
    platform = SUPPORTED_PLATFORMS.get(social_account.provider)
    if platform is None:
        return None

    connected_profile, _ = ConnectedProfile.objects.get_or_create(
        user=social_account.user,
        platform=platform,
        platform_account_id=social_account.uid,
        defaults={
            "social_account": social_account,
            "display_name": get_social_display_name(social_account),
            "is_active": True,
        },
    )
    return connected_profile
