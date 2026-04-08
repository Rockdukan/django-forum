from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "role",
        "is_banned",
        "posting_suspended",
        "last_activity",
    )
    list_filter = DjangoUserAdmin.list_filter + ("role", "is_banned", "posting_suspended")
    search_fields = ("username", "email", "first_name", "last_name")

    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            _("Форум"),
            {
                "fields": (
                    "avatar",
                    "signature",
                    "role",
                    "last_activity",
                    "notify_email_reply",
                    "notify_email_mention",
                    "notify_email_pm",
                    "notify_email_moderation",
                    "is_banned",
                    "ban_reason",
                    "banned_until",
                    "posting_suspended",
                )
            },
        ),
    )
