from crum import get_current_user
from django.db import models
from django.utils import timezone


class ChangeTrackingMixin(models.Model):
    """
    Миксин для отслеживания изменений и их подтверждения
    """
    created_at = models.DateTimeField("Дата создания", auto_now_add=True, editable=False)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True, editable=False)
    created_by = models.ForeignKey(
        "user.User",
        related_name="%(class)s_created",
        verbose_name="Кем создано",
        on_delete=models.SET_NULL,
        null=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        "user.User",
        related_name="%(class)s_updated",
        verbose_name="Кем обновлено",
        on_delete=models.SET_NULL,
        null=True,
        editable=False,
    )
    changes_verified = models.BooleanField("Изменения проверены", default=False)
    last_verified_at = models.DateTimeField("Дата последней проверки", null=True, blank=True)
    verified_by = models.ForeignKey(
        "user.User",
        related_name="%(class)s_verified",
        verbose_name="Кем проверено",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        user = get_current_user()

        # Если это новая запись

        if not self.pk:
            self.created_by = user
            # Если создал админ, считаем проверенным

            if user and user.is_staff:
                self.changes_verified = True
                self.last_verified_at = timezone.now()
                self.verified_by = user
        else:
            self.updated_by = user
            # Если запись обновил не админ, помечаем как непроверенную

            if user and not user.is_staff:
                self.changes_verified = False
            # Если запись обновил админ, считаем проверенной
            elif user and user.is_staff:
                self.changes_verified = True
                self.last_verified_at = timezone.now()
                self.verified_by = user

        super().save(*args, **kwargs)
