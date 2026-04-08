from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def user_avatar_upload_to(instance, filename):
    """Формирует относительный путь файла аватара в хранилище."""
    ext = filename.split(".")[-1] if "." in filename else "jpg"
    return f"avatars/{instance.username}.{ext}"


class User(AbstractUser):
    """Единая модель пользователя: поля Django, настройки форума и интеграция с allauth."""
    class Role(models.TextChoices):
        """Допустимые роли участника на форуме."""
        ADMIN = "admin", _("Администратор")
        MODERATOR = "moderator", _("Модератор")
        USER = "user", _("Пользователь")

    avatar = models.ImageField(
        upload_to=user_avatar_upload_to,
        blank=True,
        null=True,
        default="default-avatar.jpg",
        verbose_name=_("Аватар"),
    )
    signature = models.TextField(blank=True, verbose_name=_("Подпись"))
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER, verbose_name=_("Роль на форуме"))
    last_activity = models.DateTimeField(default=timezone.now, verbose_name=_("Последняя активность"))
    karma = models.IntegerField(default=0, verbose_name=_("Репутация"))
    ignored_users = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="ignored_by",
        blank=True,
        verbose_name=_("Игнорируемые пользователи"),
    )
    notify_email_reply = models.BooleanField(default=True, verbose_name=_("Email при ответах в подписанных темах"))
    notify_email_mention = models.BooleanField(default=True, verbose_name=_("Email при @упоминании"))
    notify_email_pm = models.BooleanField(default=True, verbose_name=_("Email при личных сообщениях"))
    notify_email_moderation = models.BooleanField(
        default=True,
        verbose_name=_("Email о модерации (для модераторов)"),
    )
    is_banned = models.BooleanField(default=False, verbose_name=_("Блокировка"))
    ban_reason = models.TextField(blank=True, verbose_name=_("Причина блокировки"))
    banned_until = models.DateTimeField(null=True, blank=True, verbose_name=_("Блокировка до (пусто = бессрочно)"))
    posting_suspended = models.BooleanField(
        default=False,
        verbose_name=_("Только чтение"),
        help_text=_("Пользователь может входить, но не создавать темы и посты"),
    )

    class Meta:
        verbose_name = _("Пользователь")
        verbose_name_plural = _("Пользователи")

    def __str__(self):
        return self.username

    def get_profile_url(self):
        """URL публичного профиля на форуме."""
        return reverse("forum:user_profile", kwargs={"username": self.username})

    def get_post_count(self):
        """Число неудалённых сообщений пользователя."""
        return self.posts.filter(is_removed=False).count()

    def get_topic_count(self):
        """Число неудалённых тем пользователя."""
        return self.topics.filter(is_removed=False).count()

    def update_last_activity(self):
        """Сохраняет метку активности «сейчас» (одно поле)."""
        self.last_activity = timezone.now()
        self.save(update_fields=["last_activity"])

    def ban_active(self) -> bool:
        """Возвращает True, если блокировка ещё действует (в т.ч. по сроку)."""
        if not self.is_banned:
            return False

        if self.banned_until is None:
            return True
        return self.banned_until > timezone.now()
