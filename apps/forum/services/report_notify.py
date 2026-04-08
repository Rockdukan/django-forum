"""In-app и email-уведомления модераторам и администраторам о новых жалобах."""
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse

from ..models import Notification
from ..permissions import MODERATOR_ROLES

User = get_user_model()
from .email_notify import try_email_notification


def moderator_recipient_users():
    """Пользователи с доступом к очереди жалоб (как в ``can_moderate``): роль в профиле или staff/superuser."""
    role_ids = set(User.objects.filter(role__in=MODERATOR_ROLES).values_list("pk", flat=True))
    staff_ids = set(User.objects.filter(Q(is_superuser=True) | Q(is_staff=True)).values_list("id", flat=True))
    all_ids = role_ids | staff_ids

    if not all_ids:
        return User.objects.none()
    return User.objects.filter(id__in=all_ids)


def notify_moderators_new_report(report) -> None:
    """Создаёт ``Notification`` типа ``report`` и при необходимости шлёт письмо (``try_email_notification``)."""
    link = reverse("forum:mod_reports")
    base = f"Новая жалоба #{report.id} от {report.reporter.username}"
    reason_bit = (report.reason or "").strip()

    if reason_bit:
        sep = ": " if base[-1] not in ":." else " "
        msg = f"{base}{sep}{reason_bit}"
    else:
        msg = base

    if len(msg) > 500:
        msg = msg[:497] + "..."

    for user in moderator_recipient_users().exclude(id=report.reporter_id):
        n = Notification.objects.create(
            recipient=user,
            actor=report.reporter,
            notification_type=Notification.TYPE_REPORT,
            message=msg,
            link=link,
            topic=report.topic,
            post=report.post,
        )
        try_email_notification(n)
