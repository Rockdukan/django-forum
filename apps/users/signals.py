from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def ensure_single_primary_email(sender, instance: User, **kwargs):
    """
    Проектный инвариант:
    - email может быть только один;
    - он же основной (primary) в allauth EmailAddress.

    allauth хранит состояние подтверждения в отдельной модели EmailAddress.
    Мы синхронизируем её с User.email и убираем «лишние» адреса.
    """
    email = (instance.email or "").strip()
    if not email:
        return

    try:
        from allauth.account.models import EmailAddress
    except Exception:
        return

    # Создаём/обновляем запись для текущего email и делаем её основной.
    obj, created = EmailAddress.objects.get_or_create(user=instance, email=email)
    if created or not obj.primary:
        obj.primary = True
        obj.save(update_fields=["primary"])

    # Удаляем остальные адреса (в т.ч. старые).
    EmailAddress.objects.filter(user=instance).exclude(email=email).delete()
