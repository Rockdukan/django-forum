MODERATOR_ROLES = frozenset({"moderator", "admin"})


def user_profile_role(user) -> str:
    if not user.is_authenticated:
        return "user"
    return getattr(user, "role", "user") or "user"


def can_moderate(user) -> bool:
    if not user.is_authenticated:
        return False

    # Суперпользователь и staff Django обходят проверку роли в профиле
    if user.is_superuser or user.is_staff:
        return True
    return user_profile_role(user) in MODERATOR_ROLES


def forum_captcha_exempt(user) -> bool:
    """Без капчи при создании тем/ответов: персонал Django и роли админ/модератор в профиле."""
    return can_moderate(user)


def can_moderate_content(user) -> bool:
    """Те же права, что для закрытия тем и скрытия постов (роль в профиле или staff)."""
    return can_moderate(user)


def posting_block_reason(user) -> str | None:
    """Причина, по которой нельзя постить (бан / только чтение). None если можно."""
    if not user.is_authenticated:
        return None

    if can_moderate(user):
        return None

    if user.ban_active():
        return "Аккаунт заблокирован."

    if user.posting_suspended:
        return "Для вашего аккаунта отключена публикация (только чтение)."
    return None


def can_edit_topic(user, topic) -> bool:
    if not user.is_authenticated:
        return False

    if posting_block_reason(user):
        return False

    if topic.author_id == user.id:
        return True
    return can_moderate(user)


def can_edit_post(user, post) -> bool:
    if not user.is_authenticated:
        return False

    if posting_block_reason(user):
        return False

    if post.author_id == user.id:
        return True
    return can_moderate(user)


def can_delete_topic(user, topic) -> bool:
    return can_edit_topic(user, topic)


def can_delete_post(user, post) -> bool:
    return can_edit_post(user, post)


def can_reply_to_topic(user, topic) -> bool:
    if not user.is_authenticated:
        return False

    if posting_block_reason(user):
        return False

    if topic.is_removed:
        return False

    # В закрытую тему пишут только модераторы
    if topic.is_closed:
        return can_moderate(user)
    return True


def can_create_new_topic(user) -> bool:
    if not user.is_authenticated:
        return False

    if posting_block_reason(user):
        return False
    return True


def can_view_removed_topic(user, topic) -> bool:
    # Мягко удалённые темы видны только персоналу
    if not topic.is_removed:
        return True
    return can_moderate(user)
