from django.template import Library

register = Library()

# Русские названия приложений для Rosetta
ROSETTA_APP_NAMES = {
    "project": "Проект",
    "core": "Ядро",
    "index": "Главная",
    "about": "О нас",
    "contacts": "Контакты",
    "news": "Новости",
    "partners": "Партнёры",
    "activity_direction": "Направления деятельности",
}


@register.filter
def rosetta_app_name(app_key):
    """Возвращает русское название приложения для Rosetta по ключу (папка)."""
    key = (app_key or "").lower().replace("-", "_")
    return ROSETTA_APP_NAMES.get(key, app_key)
