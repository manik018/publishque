"""URL configuration for Publishque."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.accounts import settings_views
from apps.core.views import dashboard


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("social/", include("allauth.urls")),
    path("profiles/", include("apps.profiles.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("posts/", include("apps.posts.urls")),
    path("settings/", settings_views.settings_hub, name="settings"),
    path("settings/profile/", settings_views.profile_settings, name="settings_profile"),
    path("settings/security/", settings_views.security_settings, name="settings_security"),
    path(
        "settings/notifications/",
        settings_views.notification_settings,
        name="settings_notifications",
    ),
    path(
        "settings/verify-email/<path:token>/",
        settings_views.verify_email,
        name="settings_email_verify",
    ),
    path("account-deleted/", settings_views.account_deleted, name="account_deleted"),
    path("dashboard/", dashboard, name="dashboard"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
