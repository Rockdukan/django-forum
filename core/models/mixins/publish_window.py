from django.db import models
from django.utils import timezone


class PublishWindowMixin(models.Model):
    """
    Управляет окном публикации записи.

    Запись считается доступной, если текущее время входит в интервал
    [`published_from`, `published_to`]. Любая из границ может быть пустой.
    """
    published_from = models.DateTimeField("Публиковать с", null=True, blank=True, db_index=True)
    published_to = models.DateTimeField("Публиковать до", null=True, blank=True, db_index=True)

    class Meta:
        abstract = True

    def is_in_publication_window(self, at=None):
        """
        Проверяет, попадает ли запись в окно публикации.

        Args:
            at: Время проверки. По умолчанию используется текущее время.

        Returns:
            bool: True, если запись должна быть видимой по окну публикации.
        """
        now = at or timezone.now()
        after_start = self.published_from is None or self.published_from <= now
        before_end = self.published_to is None or self.published_to >= now
        return after_start and before_end
