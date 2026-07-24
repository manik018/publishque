from django.urls import path

from . import views


app_name = "posts"

urlpatterns = [
    path("", views.post_list, name="list"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("calendar/day/", views.calendar_day_detail, name="calendar_day_detail"),
    path("new/", views.new_post, name="new"),
]
