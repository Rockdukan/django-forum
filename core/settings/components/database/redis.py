# Redis подключается после components/performance/caches.py — используются CACHE_KEY_PREFIX и CACHE_TIMEOUT.

# URL экземпляра Redis. Пустая строка: кэш остаётся как в caches.py (например locmem), онлайн-присутствие в БД.
# Номер логической БД задаётся в URL: redis://127.0.0.1:6379/1
REDIS_URL = env.str("REDIS_URL", default="")

# Сколько секунд запись в sorted set forum:presence:z считается актуальной для «онлайн» (форум).
FORUM_PRESENCE_TTL = env.int("FORUM_PRESENCE_TTL", default=900)

# Интервал (секундах) между записями last_activity в таблицу пользователя; тот же ключ кэшируется в default.
FORUM_LAST_ACTIVITY_DB_SYNC_SECONDS = env.int("FORUM_LAST_ACTIVITY_DB_SYNC_SECONDS", default=300)

# Параметры пула redis.ConnectionPool.from_url (см. пакет redis). 0 = не передавать, оставить дефолт клиента.
REDIS_CACHE_MAX_CONNECTIONS = env.int("REDIS_CACHE_MAX_CONNECTIONS", default=50)
REDIS_CACHE_SOCKET_TIMEOUT = env.int("REDIS_CACHE_SOCKET_TIMEOUT_SEC", default=0)
REDIS_CACHE_SOCKET_CONNECT_TIMEOUT = env.int("REDIS_CACHE_SOCKET_CONNECT_TIMEOUT_SEC", default=0)

if REDIS_URL:
    _pool_kw = {}

    if REDIS_CACHE_MAX_CONNECTIONS > 0:
        _pool_kw["max_connections"] = REDIS_CACHE_MAX_CONNECTIONS

    if REDIS_CACHE_SOCKET_TIMEOUT > 0:
        _pool_kw["socket_timeout"] = REDIS_CACHE_SOCKET_TIMEOUT

    if REDIS_CACHE_SOCKET_CONNECT_TIMEOUT > 0:
        _pool_kw["socket_connect_timeout"] = REDIS_CACHE_SOCKET_CONNECT_TIMEOUT

    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": CACHE_KEY_PREFIX,
            "TIMEOUT": CACHE_TIMEOUT,
            "OPTIONS": _pool_kw,
        },
    }
