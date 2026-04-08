from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.forum.models import Category, Topic


class ForumStaticSitemap(Sitemap):
    priority = 0.9
    changefreq = "weekly"

    def items(self):
        # Имена маршрутов «статических» страниц сайта и главной форума
        return [
            "forum:index",
            "site_pages:about",
            "site_pages:rules",
            "site_pages:privacy",
            "site_pages:contacts",
        ]

    def location(self, item):
        # Разрешение имени view в абсолютный URL для sitemap.xml
        return reverse(item)


class ForumCategorySitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        # Все разделы форума для индексации
        return Category.objects.all().order_by("order", "name")

    def lastmod(self, obj):
        # В качестве даты изменения — создание раздела (фиксированное поле)
        return obj.created_at


class ForumTopicSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.7
    limit = 2000

    def items(self):
        # Темы по убыванию активности; limit задан на уровне класса Sitemap
        return Topic.objects.select_related("category").order_by("-updated_at")

    def lastmod(self, obj):
        return obj.updated_at


sitemaps = {
    "static": ForumStaticSitemap,
    "forum_categories": ForumCategorySitemap,
    "forum_topics": ForumTopicSitemap,
}
