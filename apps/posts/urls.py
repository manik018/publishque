from django.urls import path

from . import views


app_name = "posts"

urlpatterns = [
    path("", views.post_list, name="list"),
    path("new/", views.new_post, name="new"),
]
