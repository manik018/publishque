from django.conf import settings
from django.db import models


class Post(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )
    title = models.CharField(max_length=120, blank=True)
    content = models.TextField()
    media = models.FileField(upload_to="posts/%Y/%m/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Post #{self.pk} by {self.owner.email}"


class PostTarget(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="targets",
    )
    connected_profile = models.ForeignKey(
        "profiles.ConnectedProfile",
        on_delete=models.CASCADE,
        related_name="post_targets",
    )
    scheduled_time = models.DateTimeField()
    board_id = models.CharField(max_length=255, blank=True, null=True)
    board_name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    sent_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["scheduled_time"]

    def __str__(self):
        return (
            f"{self.post} -> {self.connected_profile.display_name} "
            f"({self.get_status_display()})"
        )
