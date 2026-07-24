from django.db import migrations


def create_check_scheduled_posts_task(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = IntervalSchedule.objects.get_or_create(
        every=1,
        period="minutes",
    )
    PeriodicTask.objects.get_or_create(
        name="Check scheduled posts every minute",
        defaults={
            "interval": schedule,
            "task": "apps.posts.tasks.check_scheduled_posts",
            "enabled": True,
        },
    )


def remove_check_scheduled_posts_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name="Check scheduled posts every minute").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("django_celery_beat", "0019_alter_periodictasks_options"),
        ("posts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            create_check_scheduled_posts_task,
            remove_check_scheduled_posts_task,
        ),
    ]
