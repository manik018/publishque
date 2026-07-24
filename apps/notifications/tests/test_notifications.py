import pytest
from django.urls import reverse

from apps.notifications.models import Notification


pytestmark = pytest.mark.django_db


def test_notification_list_only_shows_owner_notifications(client, django_user_model):
    owner = django_user_model.objects.create_user(
        email="notifications@example.com",
        full_name="Notifications User",
        password="StrongPass123!",
    )
    other_user = django_user_model.objects.create_user(
        email="other-notifications@example.com",
        full_name="Other Notifications User",
        password="StrongPass123!",
    )
    Notification.objects.create(
        user=owner,
        title="Owner notification",
        message="Visible to owner",
        level=Notification.Level.INFO,
    )
    Notification.objects.create(
        user=other_user,
        title="Other notification",
        message="Hidden from owner",
        level=Notification.Level.ERROR,
    )
    client.force_login(owner)

    response = client.get(reverse("notifications:list"))

    content = response.content.decode()
    assert response.status_code == 200
    assert "Owner notification" in content
    assert "Other notification" not in content
