import environ

env = environ.Env()

_pg_options = {}

if env.str("DB_POSTGRES_SSLMODE", default="").strip():
    _pg_options["sslmode"] = env.str("DB_POSTGRES_SSLMODE").strip()

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": env.str("DB_POSTGRES_HOST", default="localhost"),
        "PORT": env.str("DB_POSTGRES_PORT", default="5432"),
        "NAME": env.str("DB_POSTGRES_NAME", default=""),
        "USER": env.str("DB_POSTGRES_USER", default=""),
        "PASSWORD": env.str("DB_POSTGRES_PASSWORD", default=""),
        "CONN_MAX_AGE": env.int("DB_POSTGRES_CONN_MAX_AGE", default=600),
        "OPTIONS": _pg_options,
    },
}

CONN_HEALTH_CHECKS = False
DATABASE_ROUTERS = []
MIGRATION_MODULES = {}
