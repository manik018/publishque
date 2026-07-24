from django.contrib import admin

from .models import ConnectedProfile


@admin.register(ConnectedProfile)
class ConnectedProfileAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "platform",
        "user",
        "platform_account_id",
        "is_active",
        "connected_at",
    )
    list_filter = ("platform", "is_active", "connected_at")
    search_fields = ("display_name", "platform_account_id", "user__email")
    readonly_fields = ("connected_at",)
