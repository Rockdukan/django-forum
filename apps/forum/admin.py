from django.contrib import admin

from .admin_extras import LucusChangelistDateHierarchyAdminMixin
from .models import (
    Category,
    ContentReport,
    Notification,
    Poll,
    PollOption,
    Post,
    PostAttachment,
    PostRevision,
    PrivateMessage,
    PrivateThread,
    PrivateThreadParticipant,
    Tag,
    Topic,
    TopicRevision,
    TopicSubscription,
    TopicBookmark,
)


class ForumModelAdmin(LucusChangelistDateHierarchyAdminMixin, admin.ModelAdmin):
    """Changelist под Lucus: иерархия дат, без цифр приоритета мультисортировки в <th>."""


@admin.register(Tag)
class TagAdmin(ForumModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(ForumModelAdmin):
    list_display = ("name", "slug", "parent", "order", "created_at", "get_topic_count")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("created_at", "parent")
    ordering = ("order", "name")
    raw_id_fields = ("parent",)


class PollOptionInline(admin.TabularInline):
    model = PollOption
    extra = 0


@admin.register(Poll)
class PollAdmin(ForumModelAdmin):
    list_display = ("question", "topic", "created_at")
    raw_id_fields = ("topic",)
    search_fields = ("question", "topic__title")
    inlines = [PollOptionInline]


@admin.register(TopicBookmark)
class TopicBookmarkAdmin(ForumModelAdmin):
    list_display = ("user", "topic", "created_at")
    raw_id_fields = ("user", "topic")


@admin.register(Topic)
class TopicAdmin(ForumModelAdmin):
    def get_queryset(self, request):
        # В админке нужны и мягко удалённые темы
        return Topic.all_objects.select_related("category", "author")

    filter_horizontal = ("tags",)

    list_display = (
        "title",
        "category",
        "author",
        "created_at",
        "is_sticky",
        "is_closed",
        "is_removed",
        "views",
    )
    list_filter = ("category", "is_sticky", "is_closed", "is_removed", "created_at")
    search_fields = ("title", "content", "author__username")
    raw_id_fields = ("author", "removed_by")
    date_hierarchy = "created_at"
    list_editable = ("is_sticky", "is_closed")


@admin.register(Post)
class PostAdmin(ForumModelAdmin):
    def get_queryset(self, request):
        # Жадная загрузка для колонок списка и поиска
        return super().get_queryset(request).select_related("topic", "author")

    list_display = ("id", "topic", "author", "created_at", "is_removed", "is_hidden", "get_like_count")
    list_filter = ("created_at", "is_removed", "is_hidden", "topic__category")
    search_fields = ("content", "author__username", "topic__title")
    raw_id_fields = ("author", "topic", "removed_by", "hidden_by")
    date_hierarchy = "created_at"


@admin.register(TopicRevision)
class TopicRevisionAdmin(ForumModelAdmin):
    list_display = ("topic", "editor", "created_at")
    raw_id_fields = ("topic", "editor")


@admin.register(PostRevision)
class PostRevisionAdmin(ForumModelAdmin):
    list_display = ("post", "editor", "created_at")
    raw_id_fields = ("post", "editor")


@admin.register(TopicSubscription)
class TopicSubscriptionAdmin(ForumModelAdmin):
    list_display = ("user", "topic", "created_at")
    raw_id_fields = ("user", "topic")


@admin.register(Notification)
class NotificationAdmin(ForumModelAdmin):
    list_display = ("recipient", "notification_type", "message", "read_at", "created_at")
    list_filter = ("notification_type", "read_at")
    raw_id_fields = ("recipient", "actor", "topic", "post")


@admin.register(PrivateThread)
class PrivateThreadAdmin(ForumModelAdmin):
    list_display = ("id", "subject", "updated_at")


@admin.register(PrivateThreadParticipant)
class PrivateThreadParticipantAdmin(ForumModelAdmin):
    list_display = ("thread", "user", "last_read_at")
    raw_id_fields = ("thread", "user")


@admin.register(PrivateMessage)
class PrivateMessageAdmin(ForumModelAdmin):
    list_display = ("thread", "sender", "created_at")
    raw_id_fields = ("thread", "sender")


@admin.register(ContentReport)
class ContentReportAdmin(ForumModelAdmin):
    list_display = ("id", "reporter", "status", "topic", "post", "created_at")
    list_filter = ("status", "created_at")
    raw_id_fields = ("reporter", "topic", "post", "reported_user", "resolved_by")


@admin.register(PostAttachment)
class PostAttachmentAdmin(ForumModelAdmin):
    list_display = ("post", "original_name", "uploaded_at")
    raw_id_fields = ("post",)
