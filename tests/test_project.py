from django.conf import settings


def test_django_settings_are_configured():
    assert settings.ROOT_URLCONF == "config.urls"
