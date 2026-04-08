from django.db import models
from solo.models import SingletonModel


class RobotsTxt(SingletonModel):
    content = models.TextField(
        "Содержимое robots.txt",
        default="User-agent: *\nAllow: /",
        help_text="Содержимое файла robots.txt для управления индексацией.")

    class Meta:
        verbose_name = "Robots.txt"
        verbose_name_plural = "Robots.txt"

    def __str__(self):
        return "Robots.txt"
