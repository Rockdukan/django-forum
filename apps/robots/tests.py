from django.test import TestCase


class RobotsTxtTests(TestCase):
    def test_robots_returns_plain_text(self):
        r = self.client.get("/robots.txt")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/plain", r["Content-Type"])
        self.assertIn(b"User-agent", r.content)
