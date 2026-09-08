import importlib.util
import unittest


class HealthEndpointTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("flask"), "Flask is not installed")
    def test_health_endpoint(self):
        from app.api.factory import create_app

        client = create_app().test_client()
        response = client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(), {"status": "ok", "service": "learnmate-api"}
        )