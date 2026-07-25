import pytest
from django.http import HttpResponse
from django.urls import path
from django.test import override_settings
from django.utils import timezone


def current_timezone_view(request):
    return HttpResponse(str(timezone.get_current_timezone()))


urlpatterns = [
    path("current-timezone/", current_timezone_view, name="current_timezone"),
]


pytestmark = pytest.mark.django_db


@override_settings(ROOT_URLCONF=__name__)
def test_authenticated_request_activates_user_timezone(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="middleware-tz@example.com",
        full_name="Middleware Timezone User",
        password="StrongPass123!",
        timezone="Asia/Dhaka",
    )
    client.force_login(user)

    response = client.get("/current-timezone/")

    assert response.status_code == 200
    assert response.content.decode() == "Asia/Dhaka"
