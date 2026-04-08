"""
Переносит русские/английские строки из старых таблиц phrases в .po (gettext).
Запуск: python manage.py fill_translations_from_phrases
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

# Соответствие msgid в шаблонах/коде и ключа в phrases
MSGID_TO_PHRASE_KEY = {
    "Главная": "nav_home",
    "О нас": "nav_about",
    "Направления деятельности": "nav_activity",
    "Партнёры": "nav_partners",
    "Новости": "nav_news",
    "Контакты": "nav_contacts",
    "Личный кабинет": "nav_account",
    "Выйти": "nav_logout",
    "Вход": "nav_login",
    "Регистрация": "nav_register",
    "Все права защищены": "footer_rights",
    "Язык интерфейса": None,  # заполним вручную
    "Администрирование сайта": None,
    "Админка": None,
}


def get_phrases_from_db():
    """Читает phrases_* из БД (таблицы остались после удаления приложения)."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.key, l.code, t.value
            FROM phrases_phrasetranslation t
            JOIN phrases_phrase p ON t.phrase_id = p.id
            JOIN phrases_language l ON t.language_id = l.id
            ORDER BY p.key, l.code
            """
        )
        rows = cursor.fetchall()
    result = {}
    for key, code, value in rows:
        if key not in result:
            result[key] = {}
        result[key][code] = (value or "").strip()
    return result


def update_po_file(locale_path, lang_code, phrases_by_key, dry_run=False):
    """Обновляет msgstr в django.po для заданного языка из phrases."""
    try:
        import polib
    except ImportError:
        raise ImportError("Нужен polib: pip install polib (или уже есть с rosetta)")

    po_path = os.path.join(locale_path, lang_code, "LC_MESSAGES", "django.po")

    if not os.path.isfile(po_path):
        return 0

    po = polib.pofile(po_path)
    updated = 0
    key_to_msgstr = {}
    for msgid, phrase_key in MSGID_TO_PHRASE_KEY.items():
        if phrase_key and phrase_key in phrases_by_key and lang_code in phrases_by_key[phrase_key]:
            key_to_msgstr[msgid] = phrases_by_key[phrase_key][lang_code]
        elif phrase_key is None and lang_code == "ru":
            key_to_msgstr[msgid] = msgid
        elif phrase_key is None and lang_code == "en":
            key_to_msgstr[msgid] = {
                "Язык интерфейса": "Interface language",
                "Администрирование сайта": "Site administration",
                "Админка": "Admin",
            }.get(msgid, msgid)

    for entry in po:
        if not entry.msgid:
            continue
        msgid = entry.msgid.strip()
        new_str = None

        if msgid in key_to_msgstr:
            new_str = key_to_msgstr[msgid]
        elif lang_code == "ru" and not (entry.msgstr or "").strip():
            new_str = msgid

        if new_str is not None and new_str != (entry.msgstr or ""):
            entry.msgstr = new_str

            if "fuzzy" in entry.flags:
                entry.flags.remove("fuzzy")
            updated += 1

    if not dry_run:
        po.save()
    return updated


class Command(BaseCommand):
    help = "Заполняет .po из старых таблиц phrases (русский/английский)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Не сохранять .po")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        locale_path = settings.LOCALE_PATHS[0] if settings.LOCALE_PATHS else os.path.join(settings.BASE_DIR, "locale")

        if not os.path.isdir(locale_path):
            self.stderr.write(self.style.ERROR(f"Нет каталога локалей: {locale_path}"))
            return

        phrases_by_key = get_phrases_from_db()
        self.stdout.write(f"Загружено {len(phrases_by_key)} ключей из phrases.")

        for lang in ("ru", "en"):
            n = update_po_file(locale_path, lang, phrases_by_key, dry_run=dry_run)
            self.stdout.write(self.style.SUCCESS(f"{lang}: обновлено записей: {n}"))

        if dry_run:
            self.stdout.write("Dry-run: .po не сохранены. Запустите без --dry-run.")
