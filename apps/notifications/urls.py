from django.urls import path

from . import views


app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path("dropdown/", views.notification_dropdown, name="dropdown"),
    path("mark-all-read/", views.mark_all_read, name="mark_all_read"),
]
