from django.db import models
from django.utils import timezone

from core.models.querysets import SoftDeleteQuerySet


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Менеджер по умолчанию: исключает мягко удаленные записи."""
    def get_queryset(self):
        return super().get_queryset().alive()


class DeletedSoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Менеджер только для мягко удаленных записей."""
    def get_queryset(self):
        return super().get_queryset().deleted()


class SoftDeleteMixin(models.Model):
    """
    Мягкое удаление: запись помечается как удалённая, но остаётся в БД.

    По умолчанию `objects` возвращает только не удаленные записи.
    Для доступа ко всем записям используйте `all_objects`.
    """
    is_deleted = models.BooleanField("Удалён", default=False, db_index=True)
    deleted_at = models.DateTimeField("Дата удаления", null=True, blank=True, editable=False)
    objects = SoftDeleteManager()
    all_objects = models.Manager.from_queryset(SoftDeleteQuerySet)()
    deleted_objects = DeletedSoftDeleteManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, hard=False):
        """
        Удаляет запись мягко или физически.

        Args:
            using: Имя БД alias.
            keep_parents: Поведение удаления родительских записей.
            hard: Если True, выполняет физическое удаление.
        """
        if not hard:
            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save(update_fields=["is_deleted", "deleted_at"])
        else:
            super().delete(using=using, keep_parents=keep_parents)

    def hard_delete(self, using=None, keep_parents=False):
        """Физически удаляет запись из БД."""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Восстанавливает «удалённую» запись."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])
