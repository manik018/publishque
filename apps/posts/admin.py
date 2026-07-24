from django.contrib import admin

from .models import Post, PostTarget


class PostTargetInline(admin.TabularInline):
    model = PostTarget
    extra = 0
    readonly_fields = ("sent_at", "error_message", "retry_count")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "short_content", "created_at", "updated_at")
    search_fields = ("content", "owner__email", "owner__full_name")
    list_filter = ("created_at", "updated_at")
    inlines = [PostTargetInline]

    def short_content(self, obj):
        return obj.content[:80]


@admin.register(PostTarget)
class PostTargetAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "post",
        "connected_profile",
        "scheduled_time",
        "status",
        "sent_at",
        "retry_count",
    )
    list_filter = ("status", "scheduled_time", "connected_profile__platform")
    search_fields = (
        "post__content",
        "post__owner__email",
        "connected_profile__display_name",
    )
