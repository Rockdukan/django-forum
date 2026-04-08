from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class SitePagesSoloAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "adm_solo",
            "adm_solo@example.com",
            "pass12345",
            is_staff=True,
            is_superuser=True,
        )

    def test_about_solo_changelist_opens(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("admin:site_pages_aboutpage_changelist"), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "О нас")

    def test_rules_solo_in_admin_index_sidebar_models_exist(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("admin:index"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Правила")
