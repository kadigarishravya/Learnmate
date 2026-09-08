import time
import unittest
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from app.config.settings import get_settings
from app.modules.quiz_assessment.service import QuizService
from app.modules.quiz_assessment.state import QuizStateStore


@dataclass
class FakeQuiz:
    quiz_id: int
    student_id: int
    topic: str
    difficulty: str
    score: float


@dataclass
class FakeHistory:
    history_id: int


class FakeRepository:
    def __init__(self):
        self.quizzes = []
        self.history = []

    def create_quiz(self, student_id, topic, difficulty, score):
        result = FakeQuiz(len(self.quizzes) + 1, student_id, topic, difficulty, score)
        self.quizzes.append(result)
        return result

    def create_history(self, student_id, topic, score, interaction_date):
        result = FakeHistory(len(self.history) + 1)
        self.history.append((student_id, topic, score, interaction_date))
        return result


def generator(context, topic, difficulty, count):
    return [
        {"question": f"Question {index}", "options": ["A", "B"], "correct_answer": "A"}
        for index in range(count)
    ]


class QuizServiceTests(unittest.TestCase):
    def setUp(self):
        self.settings = replace(get_settings(), quiz_question_count=3)
        self.store = QuizStateStore(1800)
        self.repository = FakeRepository()
        self.service = QuizService(
            self.settings,
            self.store,
            self.repository,
            context_provider=lambda student_id, topic: "grounded context",
            generator=generator,
        )

    def test_quiz_creation_hides_correct_answers_and_is_transient(self):
        state = self.service.create(1, "session-1", "Physics", "beginner")
        public = self.service.public_questions(state)
        self.assertEqual(len(public), 3)
        self.assertNotIn("correct_answer", str(public))
        self.assertIsNotNone(self.store.get_owned(state.quiz_id, 1, "session-1"))

    def test_wrong_student_cannot_access_or_submit(self):
        state = self.service.create(1, "session-1", "Physics", "beginner")
        self.assertIsNone(self.service.get(2, "session-2", state.quiz_id))
        with self.assertRaises(LookupError):
            self.service.submit(2, "session-2", state.quiz_id, ["A"] * 3)

    def test_evaluation_scores_and_clears_transient_state(self):
        state = self.service.create(1, "session-1", "Physics", "beginner")
        quiz, history, score = self.service.submit(1, "session-1", state.quiz_id, ["A", "B", "A"])
        self.assertEqual(score, 66.67)
        self.assertEqual(quiz.score, 66.67)
        self.assertEqual(len(self.repository.history), 1)
        self.assertIsNone(self.store.get_owned(state.quiz_id, 1, "session-1"))

    def test_duplicate_submission_is_rejected(self):
        state = self.service.create(1, "session-1", "Physics", "beginner")
        self.service.submit(1, "session-1", state.quiz_id, ["A"] * 3)
        with self.assertRaises(LookupError):
            self.service.submit(1, "session-1", state.quiz_id, ["A"] * 3)

    def test_insufficient_context_is_rejected(self):
        service = QuizService(
            self.settings, self.store, self.repository,
            context_provider=lambda student_id, topic: "", generator=generator,
        )
        with self.assertRaises(LookupError):
            service.create(1, "session-1", "Unknown", "beginner")

    def test_expired_quiz_is_unavailable(self):
        store = QuizStateStore(0)
        service = QuizService(
            self.settings, store, self.repository,
            context_provider=lambda student_id, topic: "context", generator=generator,
        )
        state = service.create(1, "session-1", "Physics", "beginner")
        self.assertIsNone(store.get_owned(state.quiz_id, 1, "session-1"))