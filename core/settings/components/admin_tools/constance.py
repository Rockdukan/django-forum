"""
Настройки django-constance

Компонент отвечает за:
1. Хранение глобальных настроек проекта в БД или Redis
2. Доступ к настройкам через админку
"""
# ------------------ ОСНОВНЫЕ НАСТРОЙКИ -------------------

CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"

CONSTANCE_CONFIG = {
    "SITE_NAME": ("Example", "Название сайта"),
    "CONTACT_EMAIL": ("admin@example.com", "Email для обратной связи"),
}

CONSTANCE_CONFIG_FIELDSETS = {
    "Основные": ("SITE_NAME", "CONTACT_EMAIL"),
}
