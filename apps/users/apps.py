from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "apps.users"
    label = "users"
    verbose_name = "Пользователи"

    def ready(self):
        # Поддерживаем инвариант: один email у пользователя, он же основной (allauth EmailAddress).
        from . import signals  # noqa: F401
