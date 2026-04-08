from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from ..models import Notification

User = get_user_model()

try:
    from constance import config as constance_config
except ImportError:
    constance_config = None


def get_site_name() -> str:
    """Человекочитаемое имя сайта (constance или ``settings.SITE_NAME``)."""
    if constance_config is not None:
        try:
            return constance_config.SITE_NAME
        except Exception:
            pass
    return getattr(settings, "SITE_NAME", "Форум")


def get_public_base_url() -> str:
    """Публичный базовый URL форума без завершающего слэша."""
    if constance_config is not None:
        try:
            base = (constance_config.FORUM_PUBLIC_BASE_URL or "").rstrip("/")

            if base:
                return base
        except Exception:
            pass
    return getattr(settings, "FORUM_PUBLIC_BASE_URL", "").rstrip("/")


def build_absolute_link(path: str) -> str:
    """Собирает абсолютную ссылку из пути и ``get_public_base_url()``."""
    path = path or "/"

    if not path.startswith("/"):
        path = "/" + path
    base = get_public_base_url()
    return f"{base}{path}" if base else path


def user_wants_email(user: User, attr: str) -> bool:
    """Проверяет флаг уведомлений по email на модели пользователя."""
    return bool(getattr(user, attr, True))


def try_email_notification(notification: Notification) -> None:
    if not notification.recipient.email:
        return
    nt = notification.notification_type
    rec = notification.recipient

    if nt == Notification.TYPE_REPLY and not rec.notify_email_reply:
        return

    if nt == Notification.TYPE_MENTION and not rec.notify_email_mention:
        return

    if nt == Notification.TYPE_PM and not rec.notify_email_pm:
        return

    if nt in (Notification.TYPE_MOD, Notification.TYPE_REPORT) and not rec.notify_email_moderation:
        return

    link = build_absolute_link(notification.link)
    subject = f"[{get_site_name()}] {notification.message[:60]}"
    body = f"{notification.message}\n\n{link}\n"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)

    # Ошибки SMTP не должны прерывать обработку HTTP-запроса
    try:
        send_mail(subject, body, from_email, [notification.recipient.email], fail_silently=True)
    except Exception:
        pass


def try_email_pm(recipient: User, sender_name: str, thread_path: str) -> None:
    if not recipient.email:
        return

    if not user_wants_email(recipient, "notify_email_pm"):
        return
    link = build_absolute_link(thread_path)
    subject = f"[{get_site_name()}] Личное сообщение от {sender_name}"
    body = f"Вам написал пользователь {sender_name}.\n\n{link}\n"

    try:
        send_mail(subject, body, getattr(settings, "DEFAULT_FROM_EMAIL", None), [recipient.email], fail_silently=True)
    except Exception:
        pass
