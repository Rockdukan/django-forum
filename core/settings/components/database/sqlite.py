import environ

env = environ.Env()

# Путь к файлу БД: полный путь (DB_SQLITE_PATH) или имя файла относительно BASE_DIR (DB_SQLITE_NAME).
_db_sqlite_path = env.str("DB_SQLITE_PATH", default="").strip()

if _db_sqlite_path:
    _sqlite_name = _db_sqlite_path
else:
    _sqlite_name = str(BASE_DIR / env.str("DB_SQLITE_NAME", default="db.sqlite3"))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _sqlite_name,
    },
}

CONN_HEALTH_CHECKS = False
DATABASE_ROUTERS = []
MIGRATION_MODULES = {}
