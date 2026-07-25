import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.notifications.models import Notification, NotificationPreference

from .adapters import get_adapter_for_platform
from .models import PostTarget


logger = logging.getLogger("publishque.posts.tasks")


def summarize_error(exc):
    message = str(exc).strip() or exc.__class__.__name__
    return message[:500]


def create_success_notification(post_target):
    platform = post_target.connected_profile.get_platform_display()
    user = post_target.post.owner
    preferences, _ = NotificationPreference.objects.get_or_create(user=user)
    message = f"Your post to {platform} was published successfully."
    if preferences.in_app_on_post_success:
        Notification.objects.create(
            user=user,
            title="Post published",
            message=message,
            level=Notification.Level.SUCCESS,
            related_post_target=post_target,
        )
    if preferences.email_on_post_success:
        send_mail(
            subject=f"Publishque published your post to {platform}",
            message=message,
            from_email=None,
            recipient_list=[user.email],
            fail_silently=True,
        )


def create_failure_notification(post_target, error_summary):
    platform = post_target.connected_profile.get_platform_display()
    attempts = settings.PUBLISHQUE_MAX_RETRY_ATTEMPTS
    user = post_target.post.owner
    preferences, _ = NotificationPreference.objects.get_or_create(user=user)
    message = (
        f"Your post to {platform} failed to publish after {attempts} "
        f"attempts: {error_summary}"
    )
    if preferences.in_app_on_post_failure:
        Notification.objects.create(
            user=user,
            title="Post failed to publish",
            message=message,
            level=Notification.Level.ERROR,
            related_post_target=post_target,
        )
    if preferences.email_on_post_failure:
        send_mail(
            subject=f"Publishque could not publish your post to {platform}",
            message=(
                f"Your post to {platform} failed to publish after {attempts} "
                f"attempts.\n\nError: {error_summary}\n\nReview your posts at /posts/."
            ),
            from_email=None,
            recipient_list=[user.email],
            fail_silently=True,
        )


@shared_task
def check_scheduled_posts():
    # scheduled_time is stored as an aware UTC value with USE_TZ=True, and
    # timezone.now() returns the same kind of value. Per-user timezones only
    # affect request-time parsing/rendering, so the scheduler stays timezone-neutral.
    due_targets = PostTarget.objects.select_related(
        "post",
        "connected_profile",
    ).filter(
        status=PostTarget.Status.PENDING,
        scheduled_time__lte=timezone.now(),
    )

    processed = 0
    for post_target in due_targets:
        post_target.status = PostTarget.Status.PROCESSING
        post_target.error_message = ""
        post_target.save(update_fields=["status", "error_message"])

        try:
            adapter = get_adapter_for_platform(post_target.connected_profile.platform)
            logger.info("Publishing post target %s", post_target.pk)
            published = adapter.publish(post_target)
            if not published:
                raise RuntimeError("Adapter returned False while publishing.")

            post_target.status = PostTarget.Status.SENT
            post_target.sent_at = timezone.now()
            post_target.error_message = ""
            post_target.save(update_fields=["status", "sent_at", "error_message"])
            create_success_notification(post_target)
            logger.info("Published post target %s", post_target.pk)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Publishing post target %s failed", post_target.pk)
            error_summary = summarize_error(exc)
            post_target.retry_count += 1
            post_target.error_message = error_summary

            if post_target.retry_count < settings.PUBLISHQUE_MAX_RETRY_ATTEMPTS:
                delay_minutes = 2**post_target.retry_count
                post_target.status = PostTarget.Status.PENDING
                post_target.scheduled_time = timezone.now() + timezone.timedelta(
                    minutes=delay_minutes
                )
                post_target.save(
                    update_fields=[
                        "status",
                        "retry_count",
                        "error_message",
                        "scheduled_time",
                    ]
                )
                logger.warning(
                    "Rescheduled post target %s after failure; retry %s/%s in %s minutes",
                    post_target.pk,
                    post_target.retry_count,
                    settings.PUBLISHQUE_MAX_RETRY_ATTEMPTS,
                    delay_minutes,
                )
            else:
                post_target.status = PostTarget.Status.FAILED
                post_target.save(
                    update_fields=["status", "retry_count", "error_message"]
                )
                create_failure_notification(post_target, error_summary)
                logger.error(
                    "Post target %s permanently failed after %s attempts",
                    post_target.pk,
                    post_target.retry_count,
                )

        processed += 1

    return processed
