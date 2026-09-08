import unittest

from app.api.factory import create_app
from app.config.settings import get_settings
from app.modules.quiz_assessment.service import QuizService
from app.modules.quiz_assessment.state import QuizStateStore


def generator(context, topic, difficulty, count):
    return [{"question": "Q", "options": ["A"], "correct_answer": "A"}]


class FakeRepository:
    def create_quiz(self, student_id, topic, difficulty, score):
        return type("Quiz", (), {"quiz_id": 1, "topic": topic, "difficulty": difficulty, "score": score})()

    def create_history(self, student_id, topic, score, interaction_date):
        return type("History", (), {"history_id": 1})()

    def list_quizzes(self, student_id, topic=None):
        return []

    def list_history(self, student_id, topic=None):
        return []


class QuizApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(get_settings())
        service = QuizService(
            get_settings(), QuizStateStore(1800), FakeRepository(),
            context_provider=lambda student_id, topic: "context", generator=generator,
        )
        self.app.config["LEARNMATE_QUIZ_SERVICE"] = service
        self.client = self.app.test_client()
        self.session = self.app.config["LEARNMATE_SESSION_MANAGER"].create(1)

    def test_unauthenticated_creation_is_rejected(self):
        response = self.client.post("/api/quizzes", json={"topic": "Math", "difficulty": "beginner"})
        self.assertEqual(response.status_code, 401)

    def test_creation_does_not_expose_answers_and_client_student_id_is_ignored(self):
        response = self.client.post(
            "/api/quizzes",
            json={"topic": "Math", "difficulty": "beginner", "student_id": 999},
            headers={"X-Session-ID": self.session},
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("correct_answer", str(response.get_json()))

    def test_invalid_submission_is_rejected(self):
        response = self.client.post(
            "/api/quizzes/123/submit",
            json={"answers": []},
            headers={"X-Session-ID": self.session},
        )
        self.assertEqual(response.status_code, 404)