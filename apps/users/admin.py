from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


try:
    from allauth.account.models import EmailAddress
except Exception:  # pragma: no cover
    EmailAddress = None


class EmailAddressInline(admin.TabularInline):
    model = EmailAddress
    extra = 0
    can_delete = False
    max_num = 1
    verbose_name = "Email (allauth)"
    verbose_name_plural = "Email (подтверждение)"
    fields = ("email", "verified", "primary")
    readonly_fields = ("email",)


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

    def get_inlines(self, request, obj):
        inlines = list(super().get_inlines(request, obj))
        if EmailAddress is not None:
            inlines.append(EmailAddressInline)
        return inlines
