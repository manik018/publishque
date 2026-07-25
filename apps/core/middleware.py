from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.utils import timezone


class UserTimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tz_name = settings.TIME_ZONE
        if getattr(request, "user", None) and request.user.is_authenticated:
            tz_name = request.user.timezone or settings.TIME_ZONE

        try:
            timezone.activate(ZoneInfo(tz_name))
        except ZoneInfoNotFoundError:
            timezone.activate(ZoneInfo(settings.TIME_ZONE))

        try:
            return self.get_response(request)
        finally:
            timezone.deactivate()
