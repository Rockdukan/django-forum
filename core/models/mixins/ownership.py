from django.conf import settings
from django.db import models


class OwnershipMixin(models.Model):
    """Добавляет владельца записи для ACL и фильтрации данных."""
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_owned",
        verbose_name="Владелец",
    )

    class Meta:
        abstract = True


class TenantMixin(models.Model):
    """
    Добавляет tenant-контекст к записи.

    По умолчанию используется строковый идентификатор tenant.
    """
    tenant_id = models.CharField("Tenant ID", max_length=64, db_index=True)

    class Meta:
        abstract = True
