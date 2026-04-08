from django.contrib import admin
from django.contrib.admin.models import LogEntry

from apps.forum.admin_extras import LucusChangelistDateHierarchyAdminMixin


@admin.register(LogEntry)
class LogEntryAdmin(LucusChangelistDateHierarchyAdminMixin, admin.ModelAdmin):
    list_display = ("action_time", "user", "content_type", "object_repr", "action_flag", "change_message")
    list_filter = ("action_flag", "action_time")
    search_fields = ("object_repr", "change_message")
    readonly_fields = (
        "action_time",
        "user",
        "content_type",
        "object_id",
        "object_repr",
        "action_flag",
        "change_message",
    )
    date_hierarchy = "action_time"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
