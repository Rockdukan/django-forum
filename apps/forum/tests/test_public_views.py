from django.contrib.auth import get_user_model

User = get_user_model()
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.forum.models import Category, Post, Topic


@override_settings(
    FORUM_CAPTCHA_MAX_POSTS=0,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class ForumPublicViewsTests(TestCase):
    def test_index(self):
        r = self.client.get(reverse("forum:index"))
        self.assertEqual(r.status_code, 200)

    def test_search_get(self):
        r = self.client.get(reverse("forum:search"), {"q": ""})
        self.assertEqual(r.status_code, 200)

    def test_search_with_query(self):
        r = self.client.get(reverse("forum:search"), {"q": "тест"})
        self.assertEqual(r.status_code, 200)

    def test_sitemap_xml(self):
        r = self.client.get("/sitemap.xml")
        self.assertEqual(r.status_code, 200)
        self.assertIn("xml", r["Content-Type"])

    def test_category_detail(self):
        cat = Category.objects.create(name="Раздел", slug="razdel")
        r = self.client.get(reverse("forum:category_detail", kwargs={"slug": cat.slug}))
        self.assertEqual(r.status_code, 200)

    def test_topic_detail(self):
        cat = Category.objects.create(name="C", slug="c")
        user = User.objects.create_user("author_pub", "ap@x.com", "pass12345")
        topic = Topic.objects.create(title="Тема", content="Текст", category=cat, author=user)
        Post.objects.create(topic=topic, author=user, content="Текст")
        r = self.client.get(
            reverse(
                "forum:topic_detail",
                kwargs={"category_slug": cat.slug, "topic_slug": topic.slug},
            )
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Тема")
