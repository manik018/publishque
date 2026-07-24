from celery import shared_task
from django.utils import timezone

from .adapters import get_adapter_for_platform
from .models import PostTarget


@shared_task
def check_scheduled_posts():
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
            published = adapter.publish(post_target)
            if not published:
                raise RuntimeError("Adapter returned False while publishing.")

            post_target.status = PostTarget.Status.SENT
            post_target.sent_at = timezone.now()
            post_target.error_message = ""
            post_target.save(update_fields=["status", "sent_at", "error_message"])
        except Exception as exc:  # noqa: BLE001
            post_target.status = PostTarget.Status.FAILED
            post_target.retry_count += 1
            post_target.error_message = str(exc)
            post_target.save(
                update_fields=["status", "retry_count", "error_message"]
            )

        processed += 1

    return processed
