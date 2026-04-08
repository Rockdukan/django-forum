"""Онлайн-присутствие участников через Redis (sorted set по timestamp)."""
import time

from django.conf import settings

_PRESENCE_KEY = "forum:presence:z"
_redis_client = None


def redis_client():
    """
    Returns:
        Клиент Redis или None, если ``REDIS_URL`` не задан.
    """
    global _redis_client
    url = getattr(settings, "REDIS_URL", "") or ""

    if not url:
        return None

    if _redis_client is None:
        import redis

        _redis_client = redis.Redis.from_url(url, decode_responses=True)
    return _redis_client


def record_user_presence(user_id: int) -> None:
    """
    Обновляет отметку присутствия пользователя и очищает устаревшие записи.

    Args:
        user_id: Первичный ключ пользователя.
    """
    client = redis_client()

    if client is None:
        return
    now = time.time()
    ttl = float(getattr(settings, "FORUM_PRESENCE_TTL", 900))
    pipe = client.pipeline()
    pipe.zadd(_PRESENCE_KEY, {str(user_id): now})
    pipe.zremrangebyscore(_PRESENCE_KEY, "-inf", now - ttl)
    pipe.execute()


def is_user_recently_online(user_id: int) -> bool:
    """
    Args:
        user_id: Первичный ключ пользователя.

    Returns:
        True, если пользователь недавно активен по данным Redis.
    """
    client = redis_client()

    if client is None:
        return False
    now = time.time()
    ttl = float(getattr(settings, "FORUM_PRESENCE_TTL", 900))
    score = client.zscore(_PRESENCE_KEY, str(user_id))

    if score is None:
        return False
    return now - float(score) <= ttl


def online_user_ids(limit: int = 500) -> list[int]:
    """
    Args:
        limit: Максимум идентификаторов в выборке (после отсечения по TTL).

    Returns:
        Список ``user_id`` недавно активных пользователей.
    """
    client = redis_client()

    if client is None:
        return []
    now = time.time()
    ttl = float(getattr(settings, "FORUM_PRESENCE_TTL", 900))
    pipe = client.pipeline()
    pipe.zremrangebyscore(_PRESENCE_KEY, "-inf", now - ttl)
    pipe.zrevrangebyscore(_PRESENCE_KEY, now, now - ttl, start=0, num=limit)
    _, raw_ids = pipe.execute()
    out: list[int] = []

    for x in raw_ids:

        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return out


def online_users_count() -> int:
    """
    Returns:
        Число недавно активных пользователей в Redis.
    """
    client = redis_client()

    if client is None:
        return 0
    now = time.time()
    ttl = float(getattr(settings, "FORUM_PRESENCE_TTL", 900))
    client.zremrangebyscore(_PRESENCE_KEY, "-inf", now - ttl)
    return int(client.zcount(_PRESENCE_KEY, now - ttl, now))
