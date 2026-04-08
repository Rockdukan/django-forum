"""Фильтрация контента с учётом списка игнорируемых пользователей."""
from django.db.models import QuerySet

from .permissions import can_moderate


def ignored_user_ids(for_user) -> list[int]:
    """
    Args:
        for_user: Текущий пользователь или аноним.

    Returns:
        Список ``pk`` игнорируемых авторов (пусто для гостя).
    """
    if not for_user.is_authenticated:
        return []
    return list(for_user.ignored_users.values_list("pk", flat=True))


def filter_topics_for_viewer(qs: QuerySet, viewer) -> QuerySet:
    """
    Args:
        qs: Запрос тем.
        viewer: Текущий пользователь.

    Returns:
        Запрос без тем от игнорируемых авторов (модераторы без изменений).
    """
    if not viewer.is_authenticated or can_moderate(viewer):
        return qs
    ids = ignored_user_ids(viewer)

    if not ids:
        return qs
    return qs.exclude(author_id__in=ids)


def filter_posts_for_viewer(qs: QuerySet, viewer) -> QuerySet:
    """
    Args:
        qs: Запрос сообщений.
        viewer: Текущий пользователь.

    Returns:
        Запрос без постов от игнорируемых авторов (модераторы без изменений).
    """
    if not viewer.is_authenticated or can_moderate(viewer):
        return qs
    ids = ignored_user_ids(viewer)

    if not ids:
        return qs
    return qs.exclude(author_id__in=ids)


def users_block_dm(user_a, user_b) -> bool:
    """
    Args:
        user_a: Первый участник.
        user_b: Второй участник.

    Returns:
        True, если кто-то из пары игнорирует другого (ЛС недоступны).
    """
    if user_a.id == user_b.id:
        return True
    return user_a.ignored_users.filter(pk=user_b.pk).exists() or user_b.ignored_users.filter(pk=user_a.pk).exists()
