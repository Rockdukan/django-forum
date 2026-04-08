from django.conf import settings
from django.db import models


class AuditMixin(models.Model):
    """
    Базовый аудит создания и изменения записи.

    Поля `created_by` и `updated_by` можно заполнять через `save(actor=request.user)`.
    Если `actor` не передан, поля пользователя не изменяются автоматически.
    """
    created_at = models.DateTimeField("Дата создания", auto_now_add=True, editable=False, db_index=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="%(app_label)s_%(class)s_created",
        verbose_name="Кем создано",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="%(app_label)s_%(class)s_updated",
        verbose_name="Кем обновлено",
    )

    class Meta:
        abstract = True

    def save(self, *args, actor=None, **kwargs):
        """
        Сохраняет запись и обновляет audit-поля.

        Args:
            actor: Пользователь, выполнивший изменение.
        """
        if actor and getattr(actor, "is_authenticated", False):
            if not self.pk and not self.created_by_id:
                self.created_by = actor
            self.updated_by = actor
        super().save(*args, **kwargs)
