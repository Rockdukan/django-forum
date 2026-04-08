import bleach
from bleach.css_sanitizer import CSSSanitizer
from django.db import models
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from solo.models import SingletonModel

# Разрешённые имена тегов для bleach.clean() в BaseHtmlSingletonPage.save():
# HTML из админки (Summernote) обрезается до этого набора, остальное (в т.ч. <script>) удаляется.
_BLEACH_TAGS = frozenset(
    {
        "p",
        "br",
        "div",
        "span",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "strong",
        "b",
        "em",
        "i",
        "u",
        "s",
        "strike",
        "del",
        "sub",
        "sup",
        "ul",
        "ol",
        "li",
        "blockquote",
        "pre",
        "code",
        "hr",
        "a",
        "img",
        "table",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "th",
        "td",
        "iframe",
        "figure",
        "figcaption",
    }
)
_BLEACH_ATTRS = {
    "*": ["class", "align"],
    "a": ["href", "title", "rel", "target"],
    "img": ["src", "alt", "title", "width", "height", "style"],
    "span": ["style"],
    "p": ["style"],
    "div": ["style"],
    "td": ["colspan", "rowspan", "style"],
    "th": ["colspan", "rowspan", "scope", "style"],
    "table": ["style", "border"],
    "iframe": ["src", "width", "height", "allowfullscreen", "frameborder", "title"],
    "blockquote": [],
    "code": [],
    "pre": [],
}
_BLEACH_PROTOCOLS = ["http", "https", "mailto"]
_BLEACH_CSS = CSSSanitizer(
    allowed_css_properties=[
        "color",
        "background-color",
        "font-size",
        "font-family",
        "font-weight",
        "text-align",
        "line-height",
        "margin",
        "margin-left",
        "margin-right",
        "margin-top",
        "margin-bottom",
        "padding",
        "padding-left",
        "padding-right",
        "width",
        "height",
        "max-width",
        "border",
        "border-collapse",
        "vertical-align",
        "text-decoration",
        "float",
    ]
)


class BaseHtmlSingletonPage(SingletonModel):
    # SingletonModel.get_solo() создаёт запись без параметров; поэтому title должен иметь default.
    title = models.CharField("Заголовок (H1)", max_length=200, blank=True, default="")
    content = models.TextField(
        "Содержимое (HTML)",
        blank=True,
        help_text="Редактор Summernote. При сохранении HTML очищается bleach (безопасное подмножество тегов).",)

    class Meta:
        abstract = True

    def __str__(self):
        return self.title or force_str(self._meta.verbose_name)

    def clean(self):
        super().clean()
        self.content = bleach.clean(
            self.content or "",
            tags=_BLEACH_TAGS,
            attributes=_BLEACH_ATTRS,
            protocols=_BLEACH_PROTOCOLS,
            css_sanitizer=_BLEACH_CSS,
            strip=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def html_safe(self):
        return mark_safe(self.content) if self.content else mark_safe("")


class AboutPage(BaseHtmlSingletonPage):
    class Meta:
        verbose_name = _("Страница «О нас»")
        verbose_name_plural = _("Страница «О нас»")
        db_table = "site_pages_aboutpage"


class ContactsPage(BaseHtmlSingletonPage):
    class Meta:
        verbose_name = _("Страница «Контакты»")
        verbose_name_plural = _("Страница «Контакты»")
        db_table = "site_pages_contactspage"


class PrivacyPage(BaseHtmlSingletonPage):
    class Meta:
        verbose_name = _("Страница «Конфиденциальность»")
        verbose_name_plural = _("Страница «Конфиденциальность»")
        db_table = "site_pages_privacypage"


class RulesPage(BaseHtmlSingletonPage):
    class Meta:
        verbose_name = _("Страница «Правила»")
        verbose_name_plural = _("Страница «Правила»")
        db_table = "site_pages_rulespage"
