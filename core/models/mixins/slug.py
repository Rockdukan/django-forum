from django.db import models

from core.utils.text import slugify


class SlugMixin(models.Model):
    """
    Миксин для автоматического создания slug из указанного поля.

    При сохранении модели автоматически генерирует slug на основе
    указанного поля, если slug не был установлен вручную.
    """
    slug = models.SlugField(
        "URL", max_length=255, unique=True, blank=True, help_text="Уникальный идентификатор для URL"
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Переопределяет метод save для автоматического создания slug.

        Если slug не указан, генерирует его из поля self.slug_source_field.
        По умолчанию использует поле "title".
        """
        # Проверяем, определен ли источник для slug
        slug_source_field = getattr(self, "slug_source_field", "title")
        slug_source = getattr(self, slug_source_field, "")

        # Создаем slug только если он не указан и есть источник

        if not self.slug and slug_source:
            # Получаем базовый slug
            base_slug = slugify(slug_source)

            # Проверяем уникальность slug и добавляем счетчик если нужно
            new_slug = base_slug
            counter = 1

            # Импортируем класс модели внутри метода, чтобы избежать проблем
            # с циклическими импортами
            model_class = self.__class__

            # Ищем дубликаты slug, исключая текущий объект
            while model_class.objects.filter(slug=new_slug).exclude(pk=self.pk).exists():
                new_slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = new_slug

        super().save(*args, **kwargs)
