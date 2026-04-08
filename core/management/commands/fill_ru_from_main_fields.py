"""
Копирует значения между основными полями и _ru:
1) main -> _ru, если _ru пусто (для отображения при языке ru и fallback);
2) _ru -> main, если main пусто (MODELTRANSLATION_DEFAULT_LANGUAGE=ru читает main).
Главная, О нас, Направления деятельности — поддерживают ru и en через modeltranslation.
Запуск: python manage.py fill_ru_from_main_fields
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Синхронизирует основные поля и _ru (main↔_ru при пустоте)."

    def handle(self, *args, **options):
        updated = 0
        with connection.cursor() as c:
            # ----- main -> _ru (если _ru пусто) -----
            # news_newsitem
            c.execute(
                "UPDATE news_newsitem SET title_ru = title "
                "WHERE title_ru IS NULL AND title IS NOT NULL AND title != ''"
            )
            updated += c.rowcount
            c.execute(
                "UPDATE news_newsitem SET body_ru = body WHERE body_ru IS NULL AND body IS NOT NULL AND body != ''"
            )
            updated += c.rowcount
            c.execute(
                "UPDATE news_newsitem SET summary_ru = summary "
                "WHERE summary_ru IS NULL AND summary IS NOT NULL AND summary != ''"
            )
            updated += c.rowcount
            # index_index
            c.execute(
                "UPDATE index_index SET content_ru = content "
                "WHERE content_ru IS NULL AND content IS NOT NULL AND content != ''"
            )
            updated += c.rowcount
            # about

            try:
                c.execute(
                    "UPDATE about_about SET intro_text_ru = intro_text "
                    "WHERE intro_text_ru IS NULL AND intro_text IS NOT NULL AND intro_text != ''"
                )
                updated += c.rowcount
                c.execute(
                    "UPDATE about_about SET title_ru = title "
                    "WHERE title_ru IS NULL AND title IS NOT NULL AND title != ''"
                )
                updated += c.rowcount
            except Exception:
                pass
            # contacts (только working_hours; мета только на русском)

            try:
                c.execute(
                    "UPDATE contacts_contacts SET working_hours_ru = working_hours "
                    "WHERE working_hours_ru IS NULL AND working_hours IS NOT NULL AND working_hours != ''"
                )
                updated += c.rowcount
            except Exception:
                pass
            # activity_direction

            try:
                c.execute(
                    "UPDATE activity_direction_activitydirection SET title_ru = title, "
                    "detailed_description_ru = detailed_description "
                    "WHERE title_ru IS NULL AND title IS NOT NULL"
                )
                updated += c.rowcount
            except Exception:
                pass

            # ----- _ru -> main (если main пусто; default language = ru читает main) -----

            try:
                c.execute(
                    "UPDATE index_index SET content = content_ru "
                    "WHERE (content IS NULL OR content = '') AND content_ru IS NOT NULL AND content_ru != ''"
                )
                updated += c.rowcount
            except Exception:
                pass

            try:
                c.execute(
                    "UPDATE about_about SET intro_text = intro_text_ru "
                    "WHERE (intro_text IS NULL OR intro_text = '') "
                    "AND intro_text_ru IS NOT NULL AND intro_text_ru != ''"
                )
                updated += c.rowcount
                c.execute(
                    "UPDATE about_about SET title = title_ru "
                    "WHERE (title IS NULL OR title = '') AND title_ru IS NOT NULL AND title_ru != ''"
                )
                updated += c.rowcount
            except Exception:
                pass

            try:
                c.execute(
                    "UPDATE activity_direction_activitydirection SET title = title_ru "
                    "WHERE (title IS NULL OR title = '') AND title_ru IS NOT NULL AND title_ru != ''"
                )
                updated += c.rowcount
                c.execute(
                    "UPDATE activity_direction_activitydirection "
                    "SET detailed_description = detailed_description_ru "
                    "WHERE (detailed_description IS NULL OR detailed_description = '') "
                    "AND detailed_description_ru IS NOT NULL AND detailed_description_ru != ''"
                )
                updated += c.rowcount
            except Exception:
                pass
        self.stdout.write(self.style.SUCCESS(f"Обновлено полей: {updated}"))
