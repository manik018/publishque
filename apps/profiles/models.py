from django.conf import settings
from django.db import models


class ConnectedProfile(models.Model):
    class Platform(models.TextChoices):
        FACEBOOK = "facebook", "Facebook"
        TWITTER = "twitter", "X/Twitter"
        LINKEDIN = "linkedin", "LinkedIn"
        PINTEREST = "pinterest", "Pinterest"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="connected_profiles",
    )
    platform = models.CharField(max_length=20, choices=Platform.choices)
    social_account = models.ForeignKey(
        "socialaccount.SocialAccount",
        on_delete=models.CASCADE,
        related_name="connected_profiles",
    )
    display_name = models.CharField(max_length=255)
    platform_account_id = models.CharField(max_length=255)
    page_access_token = models.CharField(max_length=500, blank=True, null=True)
    token_obtained_at = models.DateTimeField(auto_now_add=True, null=True)
    is_active = models.BooleanField(default=True)
    connected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["platform", "display_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "platform", "platform_account_id"],
                name="unique_connected_profile_per_platform_account",
            )
        ]

    def __str__(self):
        return f"{self.get_platform_display()} - {self.display_name}"
