from django.urls import path

from . import views


app_name = "profiles"

urlpatterns = [
    path("", views.connected_profiles, name="connected_profiles"),
    path(
        "disconnect/<int:pk>/",
        views.disconnect_profile,
        name="disconnect_profile",
    ),
    path(
        "<int:pk>/boards/",
        views.pinterest_board_options,
        name="pinterest_board_options",
    ),
]
