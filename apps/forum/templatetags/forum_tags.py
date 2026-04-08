import re
from urllib.parse import quote_plus

import bleach
import markdown
from django import template
from django.contrib.auth import get_user_model
from django.template.defaultfilters import date as date_filter
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.text import slugify

from ..services.presence import is_user_recently_online, online_user_ids, online_users_count

User = get_user_model()

register = template.Library()


@register.filter
def friendly_date(date):
    now = timezone.now()
    diff = now.date() - date.date()

    if diff.days == 0:
        return f"сегодня в {date_filter(date, 'H:i')}"
    elif diff.days == 1:
        return f"вчера в {date_filter(date, 'H:i')}"
    elif date.year == now.year:
        return date_filter(date, "d M в H:i")
    else:
        return date_filter(date, "d M Y в H:i")


@register.filter
def online_status(user):
    if not isinstance(user, User):
        return False

    try:

        if getattr(settings, "REDIS_URL", ""):
            return is_user_recently_online(user.pk)
        la = getattr(user, "last_activity", None)

        if not la:
            return False
        return (timezone.now() - la).total_seconds() < 900
    except Exception:
        return False


@register.filter
def posts_page(post_number, posts_per_page=10):
    return (post_number - 1) // posts_per_page + 1


@register.filter
def get_user_role_display(user):
    if not isinstance(user, User):
        return "—"

    try:
        return user.get_role_display()
    except Exception:
        return "—"


def linkify_at_mentions(raw: str) -> str:
    if not raw:
        return raw

    def repl(m):
        name = m.group(1)

        if not User.objects.filter(username=name).exists():
            return m.group(0)
        url = reverse("forum:user_profile", kwargs={"username": name})
        return f"[@{name}]({url})"

    return re.sub(r"(?<!\w)@([a-zA-Z0-9.@+\-_]+)", repl, raw)


_ALLOWED_MARKDOWN_TAGS = frozenset(
    {
        "p",
        "pre",
        "code",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "br",
        "hr",
        "ul",
        "ol",
        "li",
        "strong",
        "em",
        "blockquote",
        "a",
        "img",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "span",
        "div",
    }
)
_ALLOWED_ATTRS = {
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "title"],
    "code": ["class"],
    "*": ["class"],
}


@register.filter(name="markdown")
def markdown_format(text):
    text = linkify_at_mentions(text or "")
    raw = markdown.markdown(
        text,
        extensions=[
            "markdown.extensions.fenced_code",
            "markdown.extensions.codehilite",
            "markdown.extensions.tables",
            "markdown.extensions.nl2br",
        ],
    )
    clean = bleach.clean(
        raw,
        tags=_ALLOWED_MARKDOWN_TAGS,
        attributes=_ALLOWED_ATTRS,
        strip=True,
    )
    return mark_safe(clean)


@register.inclusion_tag("forum/tags/online_users.html")
def show_online_users(limit=10):

    if getattr(settings, "REDIS_URL", ""):
        ids = online_user_ids(limit=limit)
        ordering = {pk: i for i, pk in enumerate(ids)}
        qs = User.objects.filter(pk__in=ids)
        online_users = sorted(qs, key=lambda u: ordering.get(u.pk, 999999))

        return {"online_users": online_users, "online_count": online_users_count()}
    time_threshold = timezone.now() - timezone.timedelta(minutes=15)
    qs = User.objects.filter(last_activity__gte=time_threshold).order_by("-last_activity")[:limit]
    online_users = list(qs)
    return {
        "online_users": online_users,
        "online_count": User.objects.filter(last_activity__gte=time_threshold).count(),
    }


@register.filter
def format_tags(tags_string):
    if not tags_string:
        return ""

    tags = [tag.strip() for tag in tags_string.split(",") if tag.strip()]
    html = '<div class="tags-container">'

    for tag in tags:
        slug = slugify(tag)[:50]
        if slug:
            url = reverse("forum:tag_detail", kwargs={"tag_slug": slug})
        else:
            url = f"{reverse('forum:search')}?q={quote_plus(tag)}"
        html += f'<a href="{url}" class="tag">{tag}</a>'

    html += "</div>"
    return mark_safe(html)


@register.filter
def highlight_search_term(text, query):
    if not query:
        return text

    highlighted = re.sub(
        f"({re.escape(query)})",
        r'<span class="search-highlight">\1</span>',
        text,
        flags=re.IGNORECASE,
    )

    return mark_safe(highlighted)
