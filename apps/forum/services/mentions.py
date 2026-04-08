import re

from django.contrib.auth import get_user_model

User = get_user_model()

from ..models import Notification
from .email_notify import try_email_notification

MENTION_RE = re.compile(r"@([a-zA-Z0-9.@+\-_]+)")


def extract_mentioned_usernames(text: str) -> list[str]:
    if not text:
        return []
    found = MENTION_RE.findall(text)
    seen = set()
    out = []
    # Сохраняем порядок первых вхождений @ника без дубликатов
    for name in found:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def notify_mentions(*, body: str, actor, topic, post, exclude_user_ids: set[int] | None = None):
    exclude = exclude_user_ids or set()
    exclude.add(actor.id)
    names = extract_mentioned_usernames(body)

    if not names:
        return
    users = User.objects.filter(username__in=names).exclude(id__in=exclude)
    link = post.get_absolute_url()
    msg = f"{actor.username} упомянул(а) вас в теме «{topic.title}»"
    # По одному in-app уведомлению (и опционально email) на каждого найденного пользователя
    for u in users:
        n = Notification.objects.create(
            recipient=u,
            actor=actor,
            notification_type=Notification.TYPE_MENTION,
            message=msg,
            link=link,
            topic=topic,
            post=post,
        )
        try_email_notification(n)
