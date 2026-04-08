import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


def user_avatar_path(instance, filename):
    """Путь сохранения файла аватара пользователя (относительно MEDIA_ROOT)."""
    ext = filename.split(".")[-1]
    return f"media/{instance.user.username}.{ext}"


def post_attachment_upload_to(instance, filename):
    """Возвращает уникальный путь файла вложения сообщения."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"

    if len(ext) > 8:
        ext = "bin"
    return f"forum/attachments/{instance.post_id}/{uuid.uuid4().hex}.{ext}"


class VisibleTopicManager(models.Manager):
    """Менеджер выборки только тем, не помеченных как удалённые."""
    def get_queryset(self):
        return super().get_queryset().filter(is_removed=False)


class Category(models.Model):
    """Раздел форума (категория тем); поддерживается вложенность (подфорумы)."""
    name = models.CharField(max_length=100, verbose_name=_("Название"))
    description = models.TextField(blank=True, verbose_name=_("Описание"))
    slug = models.SlugField(unique=True, max_length=100, verbose_name=_("URL-slug"))
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
        verbose_name=_("Родительский раздел"),
    )
    order = models.IntegerField(default=0, verbose_name=_("Порядок"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))

    class Meta:
        verbose_name = _("Категория")
        verbose_name_plural = _("Категории")
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Slug по умолчанию строится из названия, если не задан вручную

        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("forum:category_detail", kwargs={"slug": self.slug})

    def subtree_ids(self) -> list[int]:
        """
        Returns:
            Идентификаторы этой категории и всех потомков (плоский список).
        """
        if self.pk is None:
            return []
        result = [self.pk]

        for child in Category.objects.filter(parent_id=self.pk).order_by("order", "name"):
            result.extend(child.subtree_ids())
        return result

    def get_ancestors(self) -> list["Category"]:
        """
        Returns:
            Цепочка от корня к текущей категории (включая её).
        """
        chain: list[Category] = []
        node: Category | None = self

        while node is not None:
            chain.append(node)
            node = node.parent
        chain.reverse()
        return chain

    def get_topic_count(self):
        return Topic.objects.filter(category_id__in=self.subtree_ids()).count()

    def get_post_count(self):
        return Post.objects.filter(topic__category_id__in=self.subtree_ids(), is_removed=False).count()

    def get_last_post(self):
        return Post.objects.filter(
            topic__category_id__in=self.subtree_ids(),
            is_removed=False,
            is_hidden=False,
        ).order_by("-created_at").first()


class Tag(models.Model):
    """Тег для тем (многие ко многим с Topic)."""
    name = models.CharField(max_length=50, verbose_name=_("Название"))
    slug = models.SlugField(max_length=50, unique=True, db_index=True, verbose_name=_("Slug"))

    class Meta:
        verbose_name = _("Тег")
        verbose_name_plural = _("Теги")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = (slugify(self.name)[:50] if self.name else "") or "tag"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("forum:tag_detail", kwargs={"tag_slug": self.slug})


class Topic(models.Model):
    """Тема обсуждения в категории."""
    title = models.CharField(max_length=200, verbose_name=_("Заголовок"))
    slug = models.SlugField(max_length=200, verbose_name=_("URL (slug)"), db_index=True, default="", blank=True)
    content = models.TextField(verbose_name=_("Содержание"))
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="topics", verbose_name=_("Категория"),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topics",
        verbose_name=_("Автор"),
    )
    tags = models.ManyToManyField("Tag", blank=True, related_name="topics", verbose_name=_("Теги"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))
    is_sticky = models.BooleanField(default=False, verbose_name=_("Закреплено"))
    is_closed = models.BooleanField(default=False, verbose_name=_("Закрыто"))
    views = models.PositiveIntegerField(default=0, verbose_name=_("Просмотры"))

    is_removed = models.BooleanField(default=False, verbose_name=_("Удалено (мягко)"))
    removed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Когда удалено"))
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="topics_removed",
        verbose_name=_("Кто удалил"),
    )
    removal_reason = models.TextField(blank=True, verbose_name=_("Причина удаления темы"))

    objects = VisibleTopicManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = _("Тема")
        verbose_name_plural = _("Темы")
        ordering = ["-is_sticky", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "slug"],
                name="forum_topic_unique_slug_per_category",
            ),
        ]

    def __str__(self):
        return self.title

    def make_unique_slug(self, base: str) -> str:
        """Строит уникальный slug темы в пределах категории (суффиксы -2, -3, …)."""
        base = (slugify(base)[:180] if base else "") or "topic"
        slug = base
        n = 1
        qs = Topic.all_objects.filter(category_id=self.category_id)

        if self.pk:
            qs = qs.exclude(pk=self.pk)
        # Подбор slug, пока не уникален в категории

        while qs.filter(slug=slug).exists():
            n += 1
            slug = f"{base}-{n}"
        return slug

    def save(self, *args, **kwargs):
        # Уникальный slug при пустом значении

        if not self.slug:
            self.slug = self.make_unique_slug(self.title or "topic")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "forum:topic_detail",
            kwargs={"category_slug": self.category.slug, "topic_slug": self.slug},
        )

    def get_reply_count(self):
        count = self.posts.filter(is_removed=False).count()

        if count <= 1:
            return 0
        return count - 1

    def get_last_post(self):
        return self.posts.filter(is_removed=False, is_hidden=False).order_by("-created_at").first()

    @classmethod
    def get_for_view(cls, user, category_slug: str, topic_slug: str):
        """
        Загружает тему по slug категории и темы с учётом мягкого удаления.

        Args:
            user: Текущий пользователь (или аноним).
            category_slug: Идентификатор раздела в URL.
            topic_slug: Идентификатор темы в URL.

        Returns:
            Экземпляр Topic или None, если не найдена или скрыта от пользователя.
        """
        from .permissions import can_view_removed_topic

        qs = cls.all_objects.select_related("category", "author").prefetch_related("tags")
        topic = qs.filter(slug=topic_slug, category__slug=category_slug).first()

        if not topic:
            return None
        # Скрытие удалённых тем от посетителей без прав

        if not can_view_removed_topic(user, topic):
            return None
        from .ignore_utils import ignored_user_ids
        from .permissions import can_moderate

        if user.is_authenticated and not can_moderate(user):

            if topic.author_id in ignored_user_ids(user):
                return None
        return topic

    def increment_views(self):
        # Просмотры не считаются для тем, убранных с публичной ленты

        if self.is_removed:
            return
        self.views += 1
        self.save(update_fields=["views"])

    def first_post(self):
        return self.posts.filter(is_removed=False).order_by("created_at").first()


class Post(models.Model):
    """Сообщение внутри темы."""
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="posts", verbose_name=_("Тема"))
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
        verbose_name=_("Автор"),
    )
    content = models.TextField(verbose_name=_("Содержание"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))
    liked_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="liked_posts",
        blank=True,
        verbose_name=_("Понравилось"),
    )

    is_removed = models.BooleanField(default=False, verbose_name=_("Удалено (мягко)"))
    removed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Когда удалено"))
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="posts_removed",
        verbose_name=_("Кто удалил"),
    )
    removal_reason = models.CharField(max_length=500, blank=True, verbose_name=_("Причина удаления"))

    is_hidden = models.BooleanField(default=False, verbose_name=_("Скрыто модератором"))
    hidden_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Когда скрыто"))
    hidden_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="posts_hidden",
        verbose_name=_("Кто скрыл"),
    )
    hidden_reason = models.CharField(max_length=500, blank=True, verbose_name=_("Причина скрытия"))

    class Meta:
        verbose_name = _("Сообщение")
        verbose_name_plural = _("Сообщения")
        ordering = ["created_at"]

    def __str__(self):
        return f"Сообщение от {self.author.username} в теме {self.topic.title}"

    def get_absolute_url(self):
        return f"{self.topic.get_absolute_url()}#post-{self.id}"

    def get_like_count(self):
        return self.liked_by.count()


class TopicRevision(models.Model):
    """Снимок правок заголовка и текста темы."""
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="revisions", verbose_name=_("Тема"))
    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="topic_edits",
        verbose_name=_("Редактор"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Когда"))
    old_title = models.CharField(max_length=200, verbose_name=_("Был заголовок"))
    new_title = models.CharField(max_length=200, verbose_name=_("Стал заголовок"))
    old_content = models.TextField(verbose_name=_("Было содержание"))
    new_content = models.TextField(verbose_name=_("Стало содержание"))
    edit_reason = models.CharField(max_length=500, blank=True, verbose_name=_("Причина правки"))

    class Meta:
        verbose_name = _("История правок темы")
        verbose_name_plural = _("История правок тем")
        ordering = ["-created_at"]


class PostRevision(models.Model):
    """Снимок правок текста сообщения."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="revisions", verbose_name=_("Сообщение"))
    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="post_edits",
        verbose_name=_("Редактор"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Когда"))
    old_content = models.TextField(verbose_name=_("Было"))
    new_content = models.TextField(verbose_name=_("Стало"))
    edit_reason = models.CharField(max_length=500, blank=True, verbose_name=_("Причина правки"))

    class Meta:
        verbose_name = _("История правок сообщения")
        verbose_name_plural = _("История правок сообщений")
        ordering = ["-created_at"]


class TopicSubscription(models.Model):
    """Подписка пользователя на уведомления по теме."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topic_subscriptions",
        verbose_name=_("Пользователь"),
    )
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="subscriptions", verbose_name=_("Тема"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Подписан с"))

    class Meta:
        verbose_name = _("Подписка на тему")
        verbose_name_plural = _("Подписки на темы")
        constraints = [
            models.UniqueConstraint(fields=["user", "topic"], name="forum_unique_topic_subscription"),
        ]


class TopicBookmark(models.Model):
    """Закладка на тему без подписки на уведомления."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topic_bookmarks",
        verbose_name=_("Пользователь"),
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="bookmarks",
        verbose_name=_("Тема"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Добавлено"))

    class Meta:
        verbose_name = _("Закладка на тему")
        verbose_name_plural = _("Закладки на темы")
        constraints = [
            models.UniqueConstraint(fields=["user", "topic"], name="forum_unique_topic_bookmark"),
        ]


class Poll(models.Model):
    """Опрос, привязанный к теме (один к одному)."""
    topic = models.OneToOneField(
        Topic,
        on_delete=models.CASCADE,
        related_name="poll",
        verbose_name=_("Тема"),
    )
    question = models.CharField(max_length=200, verbose_name=_("Вопрос"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Создан"))

    class Meta:
        verbose_name = _("Опрос")
        verbose_name_plural = _("Опросы")


class PollOption(models.Model):
    """Вариант ответа в опросе."""
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options", verbose_name=_("Опрос"))
    text = models.CharField(max_length=200, verbose_name=_("Текст варианта"))
    order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Порядок"))

    class Meta:
        verbose_name = _("Вариант опроса")
        verbose_name_plural = _("Варианты опроса")
        ordering = ["order", "id"]


class PollVote(models.Model):
    """Голос пользователя за один вариант опроса."""
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes", verbose_name=_("Опрос"))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="poll_votes",
        verbose_name=_("Пользователь"),
    )
    option = models.ForeignKey(
        PollOption,
        on_delete=models.CASCADE,
        related_name="votes",
        verbose_name=_("Вариант"),
    )

    class Meta:
        verbose_name = _("Голос в опросе")
        verbose_name_plural = _("Голоса в опросах")
        constraints = [
            models.UniqueConstraint(fields=["poll", "user"], name="forum_pollvote_unique_user_poll"),
        ]


class Notification(models.Model):
    """Внутрисайтовое уведомление пользователя."""
    class Type(models.TextChoices):
        """Тип записи для маршрутизации и писем."""
        REPLY = "reply", _("Ответ в теме")
        MENTION = "mention", _("Упоминание")
        PM = "pm", _("Личное сообщение")
        MOD = "mod", _("Модерация")
        REPORT = "report", _("Жалоба")

    TYPE_REPLY = Type.REPLY
    TYPE_MENTION = Type.MENTION
    TYPE_PM = Type.PM
    TYPE_MOD = Type.MOD
    TYPE_REPORT = Type.REPORT

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Получатель"),
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications_sent",
        verbose_name=_("Инициатор"),
    )
    notification_type = models.CharField(max_length=20, choices=Type.choices, verbose_name=_("Тип"))
    message = models.CharField(max_length=500, verbose_name=_("Текст"))
    link = models.CharField(max_length=500, blank=True, verbose_name=_("Ссылка"))
    topic = models.ForeignKey(
        Topic,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Тема"),
    )
    post = models.ForeignKey(
        Post,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Сообщение"),
    )
    read_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Прочитано"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Создано"))

    class Meta:
        verbose_name = _("Уведомление")
        verbose_name_plural = _("Уведомления")
        ordering = ["-created_at"]


class PrivateThread(models.Model):
    """Контейнер личной переписки между участниками."""
    subject = models.CharField(max_length=200, blank=True, verbose_name=_("Тема переписки"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Создана"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Обновлена"))

    class Meta:
        verbose_name = _("Личная переписка")
        verbose_name_plural = _("Личные переписки")
        ordering = ["-updated_at"]


class PrivateThreadParticipant(models.Model):
    """Участник треда ЛС и отметка прочитанного."""
    thread = models.ForeignKey(
        PrivateThread, on_delete=models.CASCADE, related_name="participants", verbose_name=_("Тред"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="private_thread_parts",
        verbose_name=_("Участник"),
    )
    last_read_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Прочитано до"))

    class Meta:
        verbose_name = _("Участник ЛС")
        verbose_name_plural = _("Участники ЛС")
        constraints = [
            models.UniqueConstraint(fields=["thread", "user"], name="forum_unique_dm_participant"),
        ]


class PrivateMessage(models.Model):
    """Одно сообщение в личной переписке."""
    thread = models.ForeignKey(
        PrivateThread, on_delete=models.CASCADE, related_name="messages", verbose_name=_("Тред"),
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="private_messages_sent",
        verbose_name=_("Отправитель"),
    )
    body = models.TextField(verbose_name=_("Текст"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Отправлено"))

    class Meta:
        verbose_name = _("Личное сообщение")
        verbose_name_plural = _("Личные сообщения")
        ordering = ["created_at"]


class ContentReport(models.Model):
    """Жалоба пользователя на контент или участника."""
    class Status(models.TextChoices):
        """Стадии рассмотрения жалобы модератором."""
        PENDING = "pending", _("На рассмотрении")
        RESOLVED = "resolved", _("Приняты меры")
        DISMISSED = "dismissed", _("Отклонена")

    STATUS_PENDING = Status.PENDING
    STATUS_RESOLVED = Status.RESOLVED
    STATUS_DISMISSED = Status.DISMISSED

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_submitted",
        verbose_name=_("Жалобщик"),
    )
    topic = models.ForeignKey(Topic, null=True, blank=True, on_delete=models.CASCADE, related_name="reports")
    post = models.ForeignKey(Post, null=True, blank=True, on_delete=models.CASCADE, related_name="reports")
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="reports_against",
        verbose_name=_("На пользователя"),
    )
    reason = models.TextField(verbose_name=_("Описание"))
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("Статус"),
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports_resolved",
        verbose_name=_("Рассмотрел"),
    )
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Когда рассмотрено"))
    moderator_note = models.TextField(blank=True, verbose_name=_("Заметка модератора"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Создано"))

    class Meta:
        verbose_name = _("Жалоба")
        verbose_name_plural = _("Жалобы")
        ordering = ["-created_at"]


class PostAttachment(models.Model):
    """Прикреплённый к сообщению файл."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="attachments", verbose_name=_("Сообщение"))
    file = models.FileField(upload_to=post_attachment_upload_to, verbose_name=_("Файл"))
    original_name = models.CharField(max_length=255, verbose_name=_("Исходное имя"))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Загружено"))

    class Meta:
        verbose_name = _("Вложение")
        verbose_name_plural = _("Вложения")
