import unittest

from app.api.factory import create_app
from app.config.settings import get_settings


class Phase6ApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(get_settings())
        self.client = self.app.test_client()

    def test_phase6_endpoints_require_authentication(self):
        for method, path in [
            ("get", "/api/recommendations"),
            ("post", "/api/recommendations/generate"),
            ("get", "/api/recommendations/adaptive"),
            ("get", "/api/analytics"),
            ("post", "/api/feedback"),
            ("get", "/api/feedback"),
        ]:
            response = getattr(self.client, method)(path)
            self.assertEqual(response.status_code, 401, path)