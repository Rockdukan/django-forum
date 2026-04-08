"""Регистрация, вход/выход (allauth), темы, ответы, уведомления, лайки — наш код."""
from allauth.account.models import EmailAddress
from captcha.models import CaptchaStore
from django.contrib.auth import get_user_model

User = get_user_model()
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.forum.models import Category, Notification, Post, Topic, TopicSubscription


def captcha_fields(prefix: str = "captcha") -> dict[str, str]:
    key = CaptchaStore.generate_key()
    store = CaptchaStore.objects.get(hashkey=key)
    return {f"{prefix}_0": key, f"{prefix}_1": store.response}


def ensure_verified_email(user: User) -> None:
    EmailAddress.objects.update_or_create(
        user=user,
        email=user.email.lower(),
        defaults={"verified": True, "primary": True},
    )


@override_settings(
    FORUM_CAPTCHA_MAX_POSTS=0,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class ForumRegisterTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)

    def test_register_post_creates_user_and_session(self):
        url = reverse("forum:register")
        data = {
            "username": "newforumuser",
            "email": "newforumuser@example.com",
            "password1": "complex-pass-xyz-99",
            "password2": "complex-pass-xyz-99",
            **captcha_fields(),
        }
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse("forum:index"))
        user = User.objects.get(username="newforumuser")
        self.assertEqual(user.email, "newforumuser@example.com")
        self.assertIn("_auth_user_id", self.client.session)

    def test_register_duplicate_username_shows_error(self):
        User.objects.create_user("taken", "a@a.com", "pass12345")
        url = reverse("forum:register")
        data = {
            "username": "taken",
            "email": "other@example.com",
            "password1": "complex-pass-xyz-99",
            "password2": "complex-pass-xyz-99",
            **captcha_fields(),
        }
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(email="other@example.com").exists())

    def test_register_duplicate_email_rejected(self):
        User.objects.create_user("u1", "same@example.com", "pass12345")
        url = reverse("forum:register")
        data = {
            "username": "othername",
            "email": "same@example.com",
            "password1": "complex-pass-xyz-99",
            "password2": "complex-pass-xyz-99",
            **captcha_fields(),
        }
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(User.objects.filter(email__iexact="same@example.com").count(), 1)


@override_settings(
    FORUM_CAPTCHA_MAX_POSTS=0,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class AllauthLoginLogoutTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.user = User.objects.create_user("logintest", "logintest@example.com", "secret-pass-88")
        ensure_verified_email(self.user)

    def test_login_post_redirects_home(self):
        r = self.client.post(
            reverse("account_login"),
            {"login": "logintest", "password": "secret-pass-88"},
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn(r.url or "", ("/", "http://testserver/", reverse("forum:index")))

    def test_login_with_email_succeeds(self):
        r = self.client.post(
            reverse("account_login"),
            {"login": "logintest@example.com", "password": "secret-pass-88"},
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn(r.url or "", ("/", "http://testserver/", reverse("forum:index")))

    def test_login_bad_password_stays_on_form(self):
        r = self.client.post(
            reverse("account_login"),
            {"login": "logintest", "password": "wrong"},
        )
        self.assertEqual(r.status_code, 200)

    def test_logout_post_clears_session(self):
        cat = Category.objects.create(name="Tmp", slug="tmpcat")
        self.client.login(username="logintest", password="secret-pass-88")
        r = self.client.post(reverse("account_logout"))
        self.assertEqual(r.status_code, 302)
        r2 = self.client.get(reverse("forum:create_topic", kwargs={"category_slug": cat.slug}))
        self.assertEqual(r2.status_code, 302)


@override_settings(
    FORUM_CAPTCHA_MAX_POSTS=0,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class TopicAndPostFlowTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.client = Client(enforce_csrf_checks=False)
        self.cat = Category.objects.create(name="Раздел", slug="razdel")
        self.author = User.objects.create_user("topicauthor", "ta@example.com", "pass12345")
        ensure_verified_email(self.author)
        self.client.login(username="topicauthor", password="pass12345")

    def test_create_topic_post_redirects_to_topic(self):
        url = reverse("forum:create_topic", kwargs={"category_slug": self.cat.slug})
        data = {
            "title": "Новая тема из теста",
            "content": "Текст первого сообщения",
            "forum": str(self.cat.pk),
            "website": "",
        }
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 302)
        topic = Topic.objects.get(title="Новая тема из теста")
        self.assertEqual(topic.author_id, self.author.id)
        self.assertTrue(TopicSubscription.objects.filter(user=self.author, topic=topic).exists())
        self.assertTrue(Post.objects.filter(topic=topic, author=self.author).exists())

    def test_create_topic_first_post_mention_notification(self):
        other = User.objects.create_user("mentioned", "m@example.com", "pass12345")
        ensure_verified_email(other)
        url = reverse("forum:create_topic", kwargs={"category_slug": self.cat.slug})
        data = {
            "title": "Тема с упоминанием",
            "content": "Привет @mentioned как дела",
            "forum": str(self.cat.pk),
            "website": "",
        }
        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            Notification.objects.filter(recipient=other, notification_type=Notification.TYPE_MENTION).exists()
        )

    def test_edit_topic_post(self):
        topic = Topic.objects.create(
            title="Старое",
            content="Старый текст",
            category=self.cat,
            author=self.author,
        )
        Post.objects.create(topic=topic, author=self.author, content="Старый текст")
        url = reverse(
            "forum:edit_topic",
            kwargs={"category_slug": self.cat.slug, "topic_slug": topic.slug},
        )
        r = self.client.post(
            url,
            {
                "title": "Новое название",
                "content": "Новый текст первого поста",
                "website": "",
            },
        )
        self.assertEqual(r.status_code, 302)
        topic.refresh_from_db()
        self.assertEqual(topic.title, "Новое название")


@override_settings(
    FORUM_CAPTCHA_MAX_POSTS=0,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class NotificationReadTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.user = User.objects.create_user("notifuser", "nu@example.com", "pass12345")
        self.other = User.objects.create_user("actor", "ac@example.com", "pass12345")
        self.n = Notification.objects.create(
            recipient=self.user,
            actor=self.other,
            notification_type=Notification.TYPE_PM,
            message="Тест",
            link="/notifications/",
        )

    def test_notification_read_sets_read_at(self):
        self.client.login(username="notifuser", password="pass12345")
        url = reverse("forum:notification_read", kwargs={"notification_id": self.n.id})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 302)
        self.n.refresh_from_db()
        self.assertIsNotNone(self.n.read_at)

    def test_notifications_list_requires_login(self):
        r = self.client.get(reverse("forum:notifications"))
        self.assertEqual(r.status_code, 302)


@override_settings(
    FORUM_CAPTCHA_MAX_POSTS=0,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class LikePostTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.cat = Category.objects.create(name="C", slug="c")
        self.user = User.objects.create_user("liker", "l@example.com", "pass12345")
        self.author = User.objects.create_user("poster", "p@example.com", "pass12345")
        self.topic = Topic.objects.create(title="T", content="x", category=self.cat, author=self.author)
        self.post = Post.objects.create(topic=self.topic, author=self.author, content="Пост")
        self.client.login(username="liker", password="pass12345")

    def test_like_post_json(self):
        url = reverse("forum:like_post", kwargs={"post_id": self.post.id})
        r = self.client.post(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("status"), "success")
        self.assertTrue(self.post.liked_by.filter(id=self.user.id).exists())
