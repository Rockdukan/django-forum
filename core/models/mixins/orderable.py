from django.db import models


class OrderableMixin(models.Model):
    """
    Миксин для добавления сортировки объектов.

    Добавляет поле order для ручной сортировки объектов и
    соответствующие методы для управления порядком.
    """
    order = models.PositiveIntegerField(
        "Порядок", default=0, db_index=True, help_text="Порядок сортировки объекта (меньшее значение = выше в списке)"
    )

    class Meta:
        abstract = True
        ordering = ["order"]

    def move_up(self, commit=True):
        """
        Перемещает объект выше в порядке сортировки.

        Args:
            commit (bool): Сохранять ли изменения в базу данных.
                           По умолчанию True.
        """
        if self.order > 0:
            self.order -= 1

            if commit:
                self.save()

    def move_down(self, commit=True):
        """
        Перемещает объект ниже в порядке сортировки.

        Args:
            commit (bool): Сохранять ли изменения в базу данных.
                           По умолчанию True.
        """
        self.order += 1

        if commit:
            self.save()

    def set_first(self, commit=True):
        """
        Устанавливает объект первым в порядке сортировки.

        Args:
            commit (bool): Сохранять ли изменения в базу данных.
                           По умолчанию True.
        """
        # Находим минимальный порядок в модели
        model_class = self.__class__
        min_order = model_class.objects.all().aggregate(models.Min("order"))["order__min"]

        # Устанавливаем порядок на единицу меньше минимального
        # или на 0, если минимальный не найден

        if min_order is not None and min_order > 0:
            self.order = min_order - 1
        else:
            self.order = 0

        if commit:
            self.save()
