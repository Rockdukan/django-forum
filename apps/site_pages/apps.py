from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SitePagesConfig(AppConfig):
    name = "apps.site_pages"
    verbose_name = _("Тексты сайта")
