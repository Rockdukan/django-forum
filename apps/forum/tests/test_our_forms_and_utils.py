"""Тесты на код проекта: формы форума, валидации, утилиты (не сторонние библиотеки)."""
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.forum.forms import ContentReportForm, PostForm, attachment_allowed, validate_attachment_list
from django.contrib.auth import get_user_model

from apps.forum.models import Category, ContentReport, Notification, Post, Topic, TopicSubscription

User = get_user_model()


@override_settings(
    FORUM_CAPTCHA_MAX_POSTS=3,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class CaptchaIfNewUserTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="C", slug="c")
        self.author = User.objects.create_user("cap_author", "ca@x.com", "pass12345")
        self.topic = Topic.objects.create(title="T", content="x", category=self.cat, author=self.author)

    def test_regular_user_has_captcha_until_three_posts(self):
        u = User.objects.create_user("cap_new", "cn@x.com", "pass12345")
        self.assertIn("captcha", PostForm(user=u).fields)

        for i in range(3):
            Post.objects.create(topic=self.topic, author=u, content=f"p{i}")
        self.assertNotIn("captcha", PostForm(user=u).fields)

    def test_moderator_profile_no_captcha(self):
        u = User.objects.create_user("cap_mod", "cm@x.com", "pass12345")
        User.objects.filter(pk=u.pk).update(role="moderator")
        u.refresh_from_db()
        self.assertNotIn("captcha", PostForm(user=u).fields)

    def test_admin_profile_no_captcha(self):
        u = User.objects.create_user("cap_adm", "cad@x.com", "pass12345")
        User.objects.filter(pk=u.pk).update(role="admin")
        u.refresh_from_db()
        self.assertNotIn("captcha", PostForm(user=u).fields)

    def test_is_staff_no_captcha(self):
        u = User.objects.create_user("cap_stf", "cs@x.com", "pass12345", is_staff=True)
        self.assertNotIn("captcha", PostForm(user=u).fields)

    def test_superuser_no_captcha(self):
        u = User.objects.create_user("cap_su", "csu@x.com", "pass12345", is_superuser=True)
        self.assertNotIn("captcha", PostForm(user=u).fields)


@override_settings(
    FORUM_CAPTCHA_MAX_POSTS=0,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class PostFormHoneypotTests(TestCase):
    def test_honeypot_filled_rejects_form(self):
        user = User.objects.create_user("u1", "u1@x.com", "pass12345")
        form = PostForm({"content": "Текст", "website": "http://spam.com"}, user=user)
        self.assertFalse(form.is_valid())

    def test_honeypot_empty_accepts_form(self):
        user = User.objects.create_user("u2", "u2@x.com", "pass12345")
        form = PostForm({"content": "Нормальный ответ", "website": ""}, user=user)
        self.assertTrue(form.is_valid())


class AttachmentUtilsTests(TestCase):
    def test_attachment_allowed_pdf(self):
        self.assertTrue(attachment_allowed("application/pdf", "doc.pdf"))

    def test_attachment_rejects_bad_extension(self):
        self.assertFalse(attachment_allowed("application/octet-stream", "x.exe"))


class ValidateAttachmentListTests(TestCase):
    def test_too_many_files_raises(self):
        files = [SimpleUploadedFile(f"f{i}.txt", b"x", content_type="text/plain") for i in range(10)]

        with self.assertRaises(forms.ValidationError):
            validate_attachment_list(files)


class ContentReportFormTests(TestCase):
    def test_valid_reason(self):
        form = ContentReportForm({"reason": "Нарушение правил"})
        self.assertTrue(form.is_valid())

    def test_empty_reason_invalid(self):
        form = ContentReportForm({"reason": ""})
        self.assertFalse(form.is_valid())


@override_settings(
    FORUM_CAPTCHA_MAX_POSTS=0,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class ReportPostViewTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="C", slug="c")
        self.author = User.objects.create_user("aut", "a@x.com", "pass12345")
        self.topic = Topic.objects.create(title="T", content="x", category=self.cat, author=self.author)
        self.post = Post.objects.create(topic=self.topic, author=self.author, content="Пост")
        self.reporter = User.objects.create_user("rep2", "r2@x.com", "pass12345")
        self.mod = User.objects.create_user("mod3", "m3@x.com", "pass12345")
        User.objects.filter(pk=self.mod.pk).update(role="moderator")

    def test_report_post_creates_report_and_mod_notification(self):
        c = Client()
        c.force_login(self.reporter)
        url = reverse("forum:report_post", kwargs={"post_id": self.post.id})
        r = c.post(url, {"reason": "Жалоба на пост"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(ContentReport.objects.filter(post=self.post).exists())
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.mod,
                notification_type=Notification.TYPE_REPORT,
            ).exists()
        )


@override_settings(
    FORUM_CAPTCHA_MAX_POSTS=0,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class TopicUnsubscribeTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="C", slug="c")
        self.user = User.objects.create_user("subu", "su@x.com", "pass12345")
        self.author = User.objects.create_user("au", "au@x.com", "pass12345")
        self.topic = Topic.objects.create(title="T", content="x", category=self.cat, author=self.author)
        Post.objects.create(topic=self.topic, author=self.author, content="x")

    def test_unsubscribe_removes_row(self):
        TopicSubscription.objects.create(user=self.user, topic=self.topic)
        c = Client()
        c.force_login(self.user)
        url = reverse(
            "forum:topic_unsubscribe",
            kwargs={"category_slug": self.cat.slug, "topic_slug": self.topic.slug},
        )
        r = c.post(url)
        self.assertEqual(r.status_code, 302)
        self.assertFalse(TopicSubscription.objects.filter(user=self.user, topic=self.topic).exists())
