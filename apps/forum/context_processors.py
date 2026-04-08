from django.contrib.auth import get_user_model

from .dm_utils import unread_dm_count_for
from .ignore_utils import filter_topics_for_viewer
from .models import Category, Notification, Post, Topic
from .permissions import can_moderate

User = get_user_model()

try:
    from constance import config as constance_config
except ImportError:
    constance_config = None


def forum_context(request):
    # Глобальные счётчики и списки для шапки/подвала
    categories = Category.objects.filter(parent__isnull=True).order_by("order", "name").prefetch_related(
        "children",
    )
    post_count = Post.objects.filter(is_removed=False).exclude(topic__is_removed=True).count()
    recent_topics = list(filter_topics_for_viewer(Topic.objects.order_by("-updated_at"), request.user)[:5])
    topic_count = Topic.objects.count()
    user_count = User.objects.count()

    default_meta = "Форум сообщества"
    site_name = default_meta

    if constance_config is not None:
        # Подмена названия и meta description из динамических настроек
        try:
            site_name = constance_config.SITE_NAME or site_name
            default_meta = constance_config.FORUM_DEFAULT_META_DESCRIPTION or default_meta
        except Exception:
            pass

    unread_notifications = 0
    unread_dm = 0
    show_mod_link = False

    if request.user.is_authenticated:
        # Бейджи и ссылка в меню модерации только для авторизованных
        unread_notifications = Notification.objects.filter(recipient=request.user, read_at__isnull=True).count()
        unread_dm = unread_dm_count_for(request.user)
        show_mod_link = can_moderate(request.user)

    return {
        "forum_categories": categories,
        "forum_post_count": post_count,
        "forum_recent_topics": recent_topics,
        "forum_topic_count": topic_count,
        "user_count": user_count,
        "forum_unread_notifications": unread_notifications,
        "forum_unread_dm": unread_dm,
        "forum_show_mod_link": show_mod_link,
        "forum_site_name": site_name,
        "forum_default_meta_description": default_meta,
    }
