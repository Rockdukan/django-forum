from django.contrib import admin
from solo.admin import SingletonModelAdmin

from .forms import singleton_page_admin_form_factory
from .models import AboutPage, ContactsPage, PrivacyPage, RulesPage


class SummernoteAdminMixin:
    """Подключает стили, чтобы iframe Summernote занимал ширину колонки формы в admin."""

    class Media:
        css = {"all": ("admin/css/summernote_admin.css",)}


@admin.register(AboutPage)
class AboutPageAdmin(SummernoteAdminMixin, SingletonModelAdmin):
    form = singleton_page_admin_form_factory(AboutPage)
    fields = ("title", "content")


@admin.register(ContactsPage)
class ContactsPageAdmin(SummernoteAdminMixin, SingletonModelAdmin):
    form = singleton_page_admin_form_factory(ContactsPage)
    fields = ("title", "content")


@admin.register(PrivacyPage)
class PrivacyPageAdmin(SummernoteAdminMixin, SingletonModelAdmin):
    form = singleton_page_admin_form_factory(PrivacyPage)
    fields = ("title", "content")


@admin.register(RulesPage)
class RulesPageAdmin(SummernoteAdminMixin, SingletonModelAdmin):
    form = singleton_page_admin_form_factory(RulesPage)
    fields = ("title", "content")
