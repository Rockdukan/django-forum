from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet для моделей с мягким удалением."""
    def alive(self):
        """
        Возвращает записи, не помеченные как удалённые.

        Returns:
            QuerySet: Набор активных записей.
        """
        return self.filter(is_deleted=False)

    def deleted(self):
        """
        Возвращает только мягко удалённые записи.

        Returns:
            QuerySet: Набор удалённых записей.
        """
        return self.filter(is_deleted=True)

    def soft_delete(self):
        """
        Мягко удаляет все записи QuerySet одним запросом.

        Returns:
            int: Количество обновлённых записей.
        """
        return self.update(is_deleted=True, deleted_at=timezone.now())

    def restore(self):
        """
        Восстанавливает мягко удалённые записи QuerySet.

        Returns:
            int: Количество обновлённых записей.
        """
        return self.update(is_deleted=False, deleted_at=None)

    def hard_delete(self):
        """
        Физически удаляет записи из БД.

        Returns:
            tuple: Результат стандартного удаления Django.
        """
        return super().delete()


class VisibilityQuerySet(models.QuerySet):
    """Унифицированные фильтры видимости для контентных моделей."""
    def active(self):
        """
        Возвращает записи с `is_active=True`.

        Returns:
            QuerySet: Набор активных записей.
        """
        return self.filter(is_active=True)

    def inactive(self):
        """
        Возвращает записи с `is_active=False`.

        Returns:
            QuerySet: Набор неактивных записей.
        """
        return self.filter(is_active=False)

    def with_status(self, status):
        """
        Фильтрует записи по статусу публикации.

        Args:
            status: Значение статуса.

        Returns:
            QuerySet: Отфильтрованный набор записей.
        """
        return self.filter(status=status)

    def published(self):
        """
        Возвращает записи со статусом `published`.

        Returns:
            QuerySet: Набор опубликованных записей.
        """
        return self.with_status("published")

    def in_publication_window(self, at=None):
        """
        Возвращает записи, попадающие в окно публикации.

        Args:
            at: Момент времени для проверки. Если не передан,
                используется текущее время.

        Returns:
            QuerySet: Набор записей, доступных для публикации.
        """
        # Если момент времени не передан, используем текущее время.
        now = at or timezone.now()

        # Объект считается попадающим в окно публикации, если:
        # 1) дата начала не задана или уже наступила;
        # 2) дата окончания не задана или ещё не наступила.
        return self.filter(
            models.Q(published_from__isnull=True) | models.Q(published_from__lte=now),
            models.Q(published_to__isnull=True) | models.Q(published_to__gte=now),
        )

    def for_owner(self, owner):
        """
        Возвращает записи конкретного владельца.

        Args:
            owner: Объект владельца.

        Returns:
            QuerySet: Набор записей владельца.
        """
        return self.filter(owner=owner)

    def for_tenant(self, tenant_id):
        """
        Возвращает записи конкретного tenant.

        Args:
            tenant_id: Идентификатор tenant.

        Returns:
            QuerySet: Набор записей tenant.
        """
        return self.filter(tenant_id=tenant_id)


class ContentQuerySet(SoftDeleteQuerySet, VisibilityQuerySet):
    """Комбинированный QuerySet для контентных моделей."""


class ContentManager(models.Manager.from_queryset(ContentQuerySet)):
    """Менеджер контентных моделей с исключением мягко удалённых записей."""
    def get_queryset(self):
        """
        Возвращает базовый QuerySet без мягко удалённых записей.

        Returns:
            QuerySet: Набор активных записей.
        """
        # По умолчанию скрываем мягко удалённые записи на уровне менеджера.
        return super().get_queryset().alive()
