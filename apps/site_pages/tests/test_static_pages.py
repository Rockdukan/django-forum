from django.test import TestCase
from django.urls import reverse

from apps.site_pages.models import AboutPage


class AboutPageModelTests(TestCase):
    def test_bleach_strips_script_on_save(self):
        page = AboutPage.get_solo()
        page.content = '<p class="ok">Текст</p><script>alert(1)</script>'
        page.title = "О нас"
        page.save()
        page.refresh_from_db()
        self.assertIn("Текст", page.content)
        self.assertNotIn("script", page.content)


class SoloPageViewTests(TestCase):
    def test_about_fallback_when_solo_empty(self):
        AboutPage.objects.filter(pk=1).update(title="", content="")
        r = self.client.get(reverse("site_pages:about"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "сообщество")

    def test_about_serves_solo_when_filled(self):
        page = AboutPage.get_solo()
        page.title = "Заголовок из БД"
        page.content = "<p>Уникальный текст из админки</p>"
        page.save()
        r = self.client.get(reverse("site_pages:about"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Уникальный текст из админки")

    def test_contacts_privacy_rules_public_urls(self):
        self.assertEqual(self.client.get(reverse("site_pages:contacts")).status_code, 200)
        self.assertEqual(self.client.get(reverse("site_pages:privacy")).status_code, 200)
        self.assertEqual(self.client.get(reverse("site_pages:rules")).status_code, 200)
