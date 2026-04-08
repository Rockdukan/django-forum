"""Вспомогательные куски для django.contrib.admin (стили Lucus и т.п.)."""


class LucusChangelistDateHierarchyAdminMixin:
    """CSS для changelist под Lucus: иерархия дат; скрытие sortpriority при мультисортировке."""

    class Media:
        css = {"all": ("admin/css/lucus_changelist_date_hierarchy.css",)}
