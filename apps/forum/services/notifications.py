from ..models import Notification, TopicSubscription
from .email_notify import try_email_notification


def notify_topic_subscribers_new_post(*, topic, post, author):
    """Уведомить подписчиков о новом сообщении (кроме автора)."""
    # Автор ответа не получает уведомление о своём же сообщении
    subs = TopicSubscription.objects.filter(topic=topic).exclude(user_id=author.id).select_related("user")
    link = post.get_absolute_url()
    msg = f"Новый ответ в теме «{topic.title}» от {author.username}"

    for sub in subs:
        n = Notification.objects.create(
            recipient=sub.user,
            actor=author,
            notification_type=Notification.TYPE_REPLY,
            message=msg,
            link=link,
            topic=topic,
            post=post,
        )
        try_email_notification(n)
