"""RSS-ленты последних тем и разделов."""
from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404
from django.utils.feedgenerator import Atom1Feed
from django.utils.html import strip_tags

from .models import Category, Topic


class LatestTopicsFeed(Feed):
    """Последние темы на форуме (RSS 2.0)."""
    title = "Последние темы форума"
    link = "/"
    description = "Недавно созданные темы"

    def items(self):
        return Topic.objects.filter(is_removed=False).select_related("category", "author").order_by("-created_at")[:40]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return strip_tags(item.content)[:500]

    def item_pubdate(self, item):
        return item.created_at

    def item_link(self, item):
        return item.get_absolute_url()


class LatestTopicsAtomFeed(LatestTopicsFeed):
    """Последние темы (Atom)."""
    feed_type = Atom1Feed
    subtitle = LatestTopicsFeed.description


class CategoryTopicsFeed(Feed):
    """Темы в разделе и его подфорумах."""
    description_template = None

    def get_object(self, request, slug):
        return get_object_or_404(Category, slug=slug)

    def title(self, obj):
        return f"Форум: {obj.name}"

    def link(self, obj):
        return obj.get_absolute_url()

    def description(self, obj):
        return strip_tags(obj.description)[:500] if obj.description else obj.name

    def items(self, obj):
        return (
            Topic.objects.filter(is_removed=False, category_id__in=obj.subtree_ids())
            .select_related("category", "author")
            .order_by("-created_at")[:40]
        )

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return strip_tags(item.content)[:500]

    def item_pubdate(self, item):
        return item.created_at

    def item_link(self, item):
        return item.get_absolute_url()


class CategoryTopicsAtomFeed(CategoryTopicsFeed):
    """Темы раздела (Atom)."""
    feed_type = Atom1Feed

    def subtitle(self, obj):
        """Возвращает подзаголовок ленты Atom (как описание категории)."""
        return self.description(obj)
