"""URL configuration for Publishque."""
from django.contrib import admin
from django.urls import include, path

from apps.core.views import dashboard


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("social/", include("allauth.urls")),
    path("profiles/", include("apps.profiles.urls")),
    path("dashboard/", dashboard, name="dashboard"),
]
