from django.db import models


class TimestampMixin(models.Model):
    """
    Миксин, добавляющий поля даты создания и обновления записи.

    Автоматически устанавливает текущее время при создании записи
    и обновляет его при каждом сохранении.
    """
    created_at = models.DateTimeField("Дата создания", auto_now_add=True, editable=False, db_index=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True, editable=False)

    class Meta:
        abstract = True
