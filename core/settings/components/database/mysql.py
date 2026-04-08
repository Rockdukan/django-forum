import environ

env = environ.Env()

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "HOST": env.str("DB_MYSQL_HOST", default="localhost"),
        "PORT": env.int("DB_MYSQL_PORT", default=3306),
        "NAME": env.str("DB_MYSQL_NAME", default=""),
        "USER": env.str("DB_MYSQL_USER", default=""),
        "PASSWORD": env.str("DB_MYSQL_PASSWORD", default=""),
        "OPTIONS": {
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "CONN_MAX_AGE": env.int("DB_MYSQL_CONN_MAX_AGE", default=600),
    },
}

CONN_HEALTH_CHECKS = False
DATABASE_ROUTERS = []
MIGRATION_MODULES = {}
