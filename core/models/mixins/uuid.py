import uuid

from django.db import models


class UUIDMixin(models.Model):
    """
    Миксин, добавляющий уникальный UUID к модели.

    Полезно для публичных идентификаторов (ссылки, API),
    когда нежелательно светить числовым pk.
    """
    uuid = models.UUIDField(
        "UUID",
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )

    class Meta:
        abstract = True
