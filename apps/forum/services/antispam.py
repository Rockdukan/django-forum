import time

from django.conf import settings
from django.core.cache import cache


def post_cooldown_seconds() -> int:
    """Минимальный интервал (сек.) между сообщениями одного пользователя."""
    return int(getattr(settings, "FORUM_POST_COOLDOWN_SECONDS", 45))


def post_burst_limit() -> int:
    """Максимум сообщений за окно ``post_burst_window_seconds``."""
    return int(getattr(settings, "FORUM_BURST_POST_LIMIT", 12))


def post_burst_window_seconds() -> int:
    """Длина окна (сек.) для подсчёта «всплеска» сообщений."""
    return int(getattr(settings, "FORUM_BURST_POST_WINDOW", 600))


def allow_user_post(user) -> tuple[bool, str | None]:
    """
    Антиспам: минимальный интервал между сообщениями и «всплеск» за окно.

    Returns:
        Кортеж (разрешено ли действие, текст ошибки или ``None``).
    """
    if not user.is_authenticated:
        return False, "Требуется вход."
    # Ключ в кэше на пользователя: последний момент публикации
    uid = user.id
    now = time.time()
    cooldown_key = f"forum:post_cooldown:{uid}"
    last = cache.get(cooldown_key)
    cd = post_cooldown_seconds()

    if last is not None and (now - float(last)) < cd:
        wait = int(cd - (now - float(last))) + 1
        return False, f"Подождите {wait} с. перед следующим сообщением."

    # Второй уровень: счётчик сообщений в скользящем окне
    burst_key = f"forum:post_burst:{uid}"
    raw = cache.get(burst_key)

    if raw is not None:
        count, window_start = raw
        window = post_burst_window_seconds()

        # Окно устарело — начинаем отсчёт заново
        if now - window_start > window:
            count, window_start = 0, now

        if count >= post_burst_limit():
            return False, "Слишком много сообщений за короткий промежуток. Попробуйте позже."

    return True, None


def record_user_post(user) -> None:
    if not user.is_authenticated:
        return
    uid = user.id
    now = time.time()
    cache.set(f"forum:post_cooldown:{uid}", now, timeout=300)

    burst_key = f"forum:post_burst:{uid}"
    window = post_burst_window_seconds()
    raw = cache.get(burst_key)

    if raw is None:
        # Первое сообщение в новом окне
        cache.set(burst_key, (1, now), timeout=window + 60)
        return
    count, window_start = raw

    # Сброс окна или инкремент счётчика
    if now - window_start > window:
        cache.set(burst_key, (1, now), timeout=window + 60)
    else:
        cache.set(burst_key, (count + 1, window_start), timeout=window + 60)


def is_duplicate_recent_post(user, topic_id: int | None, content: str, window_seconds: int = 120) -> bool:
    """Тот же текст недавно от того же пользователя (в теме topic_id или где угодно при topic_id=None)."""
    from django.utils import timezone

    from ..models import Post

    since = timezone.now() - timezone.timedelta(seconds=window_seconds)
    content_stripped = (content or "").strip()

    if not content_stripped:
        return False
    # Дубликат: тот же автор, тот же текст за окно window_seconds (опционально в одной теме)
    qs = Post.objects.filter(
        author_id=user.id,
        content__iexact=content_stripped,
        created_at__gte=since,
        is_removed=False,
    )

    if topic_id is not None and topic_id > 0:
        qs = qs.filter(topic_id=topic_id)
    return qs.exists()
