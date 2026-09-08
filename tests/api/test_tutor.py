import unittest

from app.api.factory import create_app
from app.config.settings import get_settings


class TutorApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(get_settings())
        self.client = self.app.test_client()
        self.session_id = self.app.config["LEARNMATE_SESSION_MANAGER"].create(11)

    def test_unauthenticated_query_is_rejected(self):
        response = self.client.post("/api/tutor/query", json={"question": "Explain this"})
        self.assertEqual(response.status_code, 401)

    def test_empty_question_is_rejected_before_processing(self):
        response = self.client.post(
            "/api/tutor/query",
            json={"question": ""},
            headers={"X-Session-ID": self.session_id},
        )
        self.assertEqual(response.status_code, 400)

    def test_context_clear_requires_authenticated_session(self):
        response = self.client.delete("/api/tutor/context")
        self.assertEqual(response.status_code, 401)