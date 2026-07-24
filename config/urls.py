"""URL configuration for Publishque."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.core.views import dashboard, settings_coming_soon


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("social/", include("allauth.urls")),
    path("profiles/", include("apps.profiles.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("posts/", include("apps.posts.urls")),
    path("settings/", settings_coming_soon, name="settings"),
    path("dashboard/", dashboard, name="dashboard"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
