import json

from django.test import TestCase


class HealthcheckTests(TestCase):
    def test_healthz(self):
        r = self.client.get("/healthz")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content.decode())
        self.assertEqual(data.get("status"), "ok")

    def test_readyz(self):
        r = self.client.get("/readyz")
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content.decode())
        self.assertEqual(data.get("status"), "ready")
