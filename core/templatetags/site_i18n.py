"""Теги для языков и переводов: список языков из settings.LANGUAGES (gettext/rosetta)."""
from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def get_site_languages():
    """Список языков для переключателя (из settings.LANGUAGES)."""
    languages = getattr(settings, "LANGUAGES", [])
    return [(code, str(name)) for code, name in languages]
