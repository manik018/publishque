from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.urls import reverse


class PublishqueSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_connect_redirect_url(self, request, socialaccount):
        if socialaccount.provider == "facebook":
            return reverse("profiles:facebook_select_page")
        return reverse("profiles:connected_profiles")
