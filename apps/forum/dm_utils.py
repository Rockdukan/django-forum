from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from .ignore_utils import users_block_dm
from .models import Notification, PrivateMessage, PrivateThread, PrivateThreadParticipant

User = get_user_model()


def get_or_create_dm_thread(user_a: User, user_b: User) -> tuple[PrivateThread, bool]:
    """Личный диалог 1:1: находит существующий тред с ровно двумя участниками или создаёт новый."""
    # Диалог всегда между двумя разными учётными записями
    if user_a.id == user_b.id:
        raise ValueError(str(_("Нельзя открыть диалог с самим собой.")))

    if users_block_dm(user_a, user_b):
        raise ValueError(str(_("Переписка недоступна из-за настроек игнора.")))

    # Ищем уже существующий тред ровно с этой парой участников (по счётчику связей)
    existing = (
        PrivateThread.objects.annotate(n=Count("participants", distinct=True))
        .filter(n=2, participants__user_id=user_a.id)
        .filter(participants__user_id=user_b.id)
        .distinct()
    ).first()

    if existing:
        return existing, False

    # Создаём тред и обе связи участников атомарно
    with transaction.atomic():
        thread = PrivateThread.objects.create()
        PrivateThreadParticipant.objects.create(thread=thread, user=user_a)
        PrivateThreadParticipant.objects.create(thread=thread, user=user_b)
    return thread, True


def unread_dm_count_for(user: User) -> int:
    if not user.is_authenticated:
        return 0
    total = 0

    # Суммируем непрочитанные входящие по каждому треду (отсечка по last_read_at)
    for part in PrivateThreadParticipant.objects.filter(user=user).select_related("thread"):
        last_read = part.last_read_at
        qs = PrivateMessage.objects.filter(thread=part.thread).exclude(sender=user)

        if last_read:
            qs = qs.filter(created_at__gt=last_read)
        total += qs.count()
    return total


def get_dm_inbox_summaries(user: User, limit: int | None = None) -> list[dict]:
    """
    Данные для списка ЛС и превью на профиле: собеседник, последнее сообщение,
    признак «непрочитано» (последнее не от вас и новее last_read_at).
    """
    if not user.is_authenticated:
        return []

    thread_ids = list(PrivateThreadParticipant.objects.filter(user=user).values_list("thread_id", flat=True))
    if not thread_ids:
        return []

    qs = (
        PrivateThread.objects.filter(id__in=thread_ids)
        .order_by("-updated_at")
        .prefetch_related(
            Prefetch(
                "participants",
                PrivateThreadParticipant.objects.select_related("user"),
            ),
            Prefetch(
                "messages",
                PrivateMessage.objects.select_related("sender").order_by("-created_at"),
            ),
        )
    )
    threads = list(qs[:limit]) if limit is not None else list(qs)

    my_id = user.id
    summaries: list[dict] = []
    for thread in threads:
        my_part: PrivateThreadParticipant | None = None
        other_user = None
        for part in thread.participants.all():
            if part.user_id == my_id:
                my_part = part
            else:
                other_user = part.user

        msgs = list(thread.messages.all())
        last_msg = msgs[0] if msgs else None

        unread = False
        last_from_self = False
        if last_msg:
            last_from_self = last_msg.sender_id == my_id
            if not last_from_self:
                lr = my_part.last_read_at if my_part else None
                if lr is None or last_msg.created_at > lr:
                    unread = True

        if other_user is None:
            continue

        if users_block_dm(user, other_user):
            continue
        summaries.append(
            {
                "thread": thread,
                "other_user": other_user,
                "last_message": last_msg,
                "unread": unread,
                "last_from_self": last_from_self,
            }
        )
    return summaries


def mark_pm_notifications_read_for_thread(user: User, thread_id: int) -> int:
    """Помечает прочитанными уведомления о ЛС, ведущие в этот тред (как при клике по уведомлению)."""
    if not user.is_authenticated:
        return 0
    canonical = reverse("forum:dm_thread", kwargs={"thread_id": thread_id})
    tail = f"/messages/thread/{thread_id}/"
    now = timezone.now()
    return Notification.objects.filter(
        recipient=user,
        notification_type=Notification.TYPE_PM,
        read_at__isnull=True,
    ).filter(Q(link=canonical) | Q(link__endswith=tail)).update(read_at=now)
