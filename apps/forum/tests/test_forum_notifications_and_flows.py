"""Тесты уведомлений, подписок, жалоб, ЛС и прав доступа к модерации."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.forum.models import (
    Category,
    ContentReport,
    Notification,
    Post,
    PrivateMessage,
    PrivateThread,
    Topic,
    TopicSubscription,
)

User = get_user_model()
from apps.forum.services.mentions import notify_mentions
from apps.forum.services.notifications import notify_topic_subscribers_new_post
from apps.forum.services.report_notify import notify_moderators_new_report


@override_settings(
    FORUM_CAPTCHA_MAX_POSTS=0,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class ReportNotificationsTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Раздел", slug="razdel")
        self.alice = User.objects.create_user("alice", "alice@example.com", "pass12345")
        self.topic = Topic.objects.create(
            title="Тема",
            content="Текст",
            category=self.cat,
            author=self.alice,
        )
        Post.objects.create(topic=self.topic, author=self.alice, content="Первый пост")

    def test_notify_moderators_creates_in_app_notification(self):
        mod = User.objects.create_user("modu", "mod@example.com", "pass12345")
        User.objects.filter(pk=mod.pk).update(role="moderator")

        rep = ContentReport.objects.create(
            reporter=self.alice,
            topic=self.topic,
            reason="Спам в теме",
        )
        notify_moderators_new_report(rep)

        n = Notification.objects.get(recipient=mod)
        self.assertEqual(n.notification_type, Notification.TYPE_REPORT)
        self.assertIn("жалоба", n.message.lower())
        self.assertIn(str(rep.id), n.message)
        self.assertEqual(n.link, reverse("forum:mod_reports"))

    def test_reporter_does_not_get_report_notification(self):
        User.objects.filter(pk=self.alice.pk).update(role="moderator")
        rep = ContentReport.objects.create(
            reporter=self.alice,
            topic=self.topic,
            reason="Тест",
        )
        notify_moderators_new_report(rep)
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.alice,
                notification_type=Notification.TYPE_REPORT,
            ).exists()
        )

    def test_staff_without_moderator_role_gets_notification(self):
        staff = User.objects.create_user("staffu", "staff@example.com", "pass12345", is_staff=True)
        rep = ContentReport.objects.create(
            reporter=self.alice,
            topic=self.topic,
            reason="Нарушение",
        )
        notify_moderators_new_report(rep)
        self.assertTrue(Notification.objects.filter(recipient=staff).exists())

    def test_report_topic_view_notifies_moderator(self):
        mod = User.objects.create_user("mod2", "mod2@example.com", "pass12345")
        User.objects.filter(pk=mod.pk).update(role="moderator")
        reporter = User.objects.create_user("rep", "rep@example.com", "pass12345")

        c = Client()
        c.force_login(reporter)
        url = reverse(
            "forum:report_topic",
            kwargs={"category_slug": self.cat.slug, "topic_slug": self.topic.slug},
        )
        r = c.post(url, {"reason": "Жалоба через форму"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            Notification.objects.filter(recipient=mod, notification_type=Notification.TYPE_REPORT).exists()
        )


@override_settings(
    FORUM_CAPTCHA_MAX_POSTS=0,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class SubscribeAndReplyNotificationsTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Cat", slug="cat")
        self.author = User.objects.create_user("author", "author@example.com", "pass12345")
        self.subscriber = User.objects.create_user("sub", "sub@example.com", "pass12345")
        self.replier = User.objects.create_user("replier", "rep@example.com", "pass12345")
        self.topic = Topic.objects.create(
            title="T1",
            content="Первый",
            category=self.cat,
            author=self.author,
        )
        self.first = Post.objects.create(topic=self.topic, author=self.author, content="Первый")

    def test_subscribe_post_creates_subscription(self):
        c = Client()
        c.force_login(self.subscriber)
        url = reverse(
            "forum:topic_subscribe",
            kwargs={"category_slug": self.cat.slug, "topic_slug": self.topic.slug},
        )
        r = c.post(url)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            TopicSubscription.objects.filter(user=self.subscriber, topic=self.topic).exists()
        )

    def test_new_reply_notifies_subscriber(self):
        TopicSubscription.objects.create(user=self.subscriber, topic=self.topic)
        reply = Post.objects.create(topic=self.topic, author=self.replier, content="Ответ")
        notify_topic_subscribers_new_post(topic=self.topic, post=reply, author=self.replier)

        n = Notification.objects.get(recipient=self.subscriber)
        self.assertEqual(n.notification_type, Notification.TYPE_REPLY)
        self.assertEqual(n.actor_id, self.replier.id)

    def test_author_of_reply_not_notified_for_own_post(self):
        TopicSubscription.objects.create(user=self.replier, topic=self.topic)
        reply = Post.objects.create(topic=self.topic, author=self.replier, content="Свой ответ")
        notify_topic_subscribers_new_post(topic=self.topic, post=reply, author=self.replier)
        self.assertFalse(Notification.objects.filter(recipient=self.replier).exists())


@override_settings(
    FORUM_CAPTCHA_MAX_POSTS=0,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class MentionNotificationsTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="C", slug="c")
        self.actor = User.objects.create_user("actor", "a@a.com", "pass12345")
        self.bob = User.objects.create_user("bob", "b@b.com", "pass12345")
        self.topic = Topic.objects.create(
            title="M",
            content="x",
            category=self.cat,
            author=self.actor,
        )
        self.post = Post.objects.create(topic=self.topic, author=self.actor, content="@bob привет")

    def test_notify_mentions_creates_notification(self):
        notify_mentions(
            body=self.post.content,
            actor=self.actor,
            topic=self.topic,
            post=self.post,
        )
        n = Notification.objects.get(recipient=self.bob)
        self.assertEqual(n.notification_type, Notification.TYPE_MENTION)


@override_settings(
    FORUM_CAPTCHA_MAX_POSTS=0,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class DirectMessageTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user("dma", "a@dm.com", "pass12345")
        self.b = User.objects.create_user("dmb", "b@dm.com", "pass12345")

    def test_compose_creates_thread_message_and_notification(self):
        c = Client()
        c.force_login(self.a)
        url = reverse("forum:dm_compose")
        r = c.post(
            url,
            {"to_username": self.b.username, "message": "Привет из теста"},
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(PrivateMessage.objects.filter(sender=self.a).exists())
        n = Notification.objects.get(recipient=self.b)
        self.assertEqual(n.notification_type, Notification.TYPE_PM)
        self.assertIn(self.a.username, n.message)

    def test_notification_read_redirects_to_thread(self):
        c = Client()
        c.force_login(self.a)
        c.post(
            reverse("forum:dm_compose"),
            {"to_username": self.b.username, "message": "Линк"},
        )
        n = Notification.objects.get(recipient=self.b)
        c.logout()
        c.force_login(self.b)
        read_url = reverse("forum:notification_read", kwargs={"notification_id": n.id})
        r = c.get(read_url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/messages/thread/", r.url)

    def test_dm_inbox_lists_other_username_and_direction(self):
        c = Client()
        c.force_login(self.a)
        c.post(
            reverse("forum:dm_compose"),
            {"to_username": self.b.username, "message": "Привет в inbox"},
        )
        r = c.get(reverse("forum:dm_inbox"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.b.username)
        self.assertContains(r, "Вы:")

    def test_own_profile_shows_dm_block_with_preview(self):
        c = Client()
        c.force_login(self.a)
        c.post(
            reverse("forum:dm_compose"),
            {"to_username": self.b.username, "message": "Для превью в профиле"},
        )
        r = c.get(reverse("forum:user_profile", kwargs={"username": self.a.username}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Личные сообщения")
        self.assertContains(r, self.b.username)

    def test_opening_dm_thread_marks_pm_notification_read(self):
        c = Client()
        c.force_login(self.a)
        c.post(
            reverse("forum:dm_compose"),
            {"to_username": self.b.username, "message": "Сообщение для уведомления"},
        )
        n = Notification.objects.get(recipient=self.b, notification_type=Notification.TYPE_PM)
        self.assertIsNone(n.read_at)
        c.logout()
        c.force_login(self.b)
        thread = PrivateThread.objects.get()
        r = c.get(reverse("forum:dm_thread", kwargs={"thread_id": thread.id}))
        self.assertEqual(r.status_code, 200)
        n.refresh_from_db()
        self.assertIsNotNone(n.read_at)


@override_settings(
    FORUM_CAPTCHA_MAX_POSTS=0,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class ModerationAccessTests(TestCase):
    def test_mod_reports_forbidden_for_regular_user(self):
        u = User.objects.create_user("u1", "u1@x.com", "pass12345")
        c = Client()
        c.force_login(u)
        r = c.get(reverse("forum:mod_reports"))
        self.assertEqual(r.status_code, 403)

    def test_mod_reports_ok_for_moderator(self):
        mod = User.objects.create_user("m1", "m1@x.com", "pass12345")
        User.objects.filter(pk=mod.pk).update(role="moderator")
        c = Client()
        c.force_login(mod)
        r = c.get(reverse("forum:mod_reports"))
        self.assertEqual(r.status_code, 200)


@override_settings(
    FORUM_CAPTCHA_MAX_POSTS=0,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class CreatePostIntegrationTests(TestCase):
    """Отправка ответа через HTTP: подписчик получает уведомление."""
    def setUp(self):
        self.cat = Category.objects.create(name="Forum", slug="forum")
        self.author = User.objects.create_user("op", "op@x.com", "pass12345")
        self.sub = User.objects.create_user("follower", "f@x.com", "pass12345")
        self.replier = User.objects.create_user("replyguy", "rg@x.com", "pass12345")
        self.topic = Topic.objects.create(
            title="Thread",
            content="OP text",
            category=self.cat,
            author=self.author,
        )
        Post.objects.create(topic=self.topic, author=self.author, content="OP text")
        TopicSubscription.objects.create(user=self.sub, topic=self.topic)

    def test_create_post_via_client_notifies_subscriber(self):
        c = Client()
        c.force_login(self.replier)
        url = reverse(
            "forum:create_post",
            kwargs={"category_slug": self.cat.slug, "topic_slug": self.topic.slug},
        )
        r = c.post(
            url,
            {"content": "Ответ через форму", "website": ""},
        )
        self.assertEqual(r.status_code, 302, msg=getattr(r, "content", b"")[:500])
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.sub,
                notification_type=Notification.TYPE_REPLY,
            ).exists()
        )
