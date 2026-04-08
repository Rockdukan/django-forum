from django.db import models


class MetaMixin(models.Model):
    """
    Миксин для добавления SEO-метаданных к модели.

    Добавляет поля для мета-заголовка, описания и ключевых слов,
    используемых для SEO-оптимизации страниц.
    """
    meta_title = models.CharField(
        "Мета-заголовок", max_length=255, blank=True, help_text="Заголовок страницы для SEO (тег title)"
    )
    meta_description = models.TextField(
        "Мета-описание", blank=True, help_text="Краткое описание страницы для SEO (мета-тег description)"
    )
    meta_keywords = models.CharField(
        "Ключевые слова",
        max_length=255,
        blank=True,
        help_text="Ключевые слова через запятую для SEO (мета-тег keywords)",
    )

    class Meta:
        abstract = True
