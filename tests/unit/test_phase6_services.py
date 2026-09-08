import unittest
from dataclasses import dataclass
from datetime import datetime

from app.modules.feedback.service import FeedbackService
from app.modules.learning_analytics.service import LearningAnalyticsService
from app.modules.recommendation.service import RecommendationService


@dataclass
class Item:
    topic: str
    score: float | None = None
    interaction_date: datetime = datetime(2026, 1, 1)


@dataclass
class Recommendation:
    recommendation_id: int
    topic: str
    recommendation_text: str


@dataclass
class Feedback:
    feedback_id: int
    query_id: int
    rating: int
    comments: str | None


class Repository:
    def __init__(self):
        self.created = []
        self.feedback = []
        self.recommendations = []
        self.query_ids = {3}

    def list_quizzes(self, student_id):
        return [Item("Math", 40), Item("Math", 50)]

    def list_history(self, student_id):
        return []

    def list_tutor_interactions(self, student_id):
        return []

    def list_recommendations(self, student_id):
        return self.recommendations

    def create_recommendation(self, student_id, topic, recommendation_text):
        result = Recommendation(len(self.recommendations) + 1, topic, recommendation_text)
        self.recommendations.append(result)
        return result

    def get_owned_query(self, student_id, query_id):
        return object() if query_id in self.query_ids else None

    def create_feedback(self, student_id, query_id, rating, comments):
        result = Feedback(len(self.feedback) + 1, query_id, rating, comments)
        self.feedback.append(result)
        return result

    def list_feedback(self, student_id):
        return self.feedback


class Adaptive:
    def weak_topics(self, quizzes, interactions):
        return [{"topic": "Math", "weak": True}]

    def topic_status(self, quizzes, interactions):
        return [{"topic": "Math", "weak": True}]


class RecommendationTests(unittest.TestCase):
    def test_weak_topic_recommendation_uses_deterministic_fallback_and_deduplicates(self):
        repository = Repository()
        service = RecommendationService(Adaptive(), repository, document_repository=None)
        first = service.generate(1)
        second = service.generate(1)
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertIn("No relevant uploaded material", first[0].recommendation_text)


class AnalyticsTests(unittest.TestCase):
    def test_analytics_has_topic_metrics_and_category_counts_not_average_rating(self):
        service = LearningAnalyticsService(Adaptive())
        result = service.summarize(
            [Item("Math", 40), Item("Math", 50)],
            [Item("Math", None)],
            [object(), object()],
            [object()],
            [Feedback(1, 3, 1, None), Feedback(2, 3, 3, "wrong")],
        )
        self.assertEqual(result["average_quiz_score"], 45)
        self.assertEqual(result["feedback_category_counts"]["Helpful"], 1)
        self.assertEqual(result["feedback_category_counts"]["Incorrect"], 1)
        self.assertNotIn("average_rating", result)

    def test_empty_analytics_uses_empty_values(self):
        result = LearningAnalyticsService(Adaptive()).summarize([], [], [], [], [])
        self.assertEqual(result["total_evaluated_quizzes"], 0)
        self.assertIsNone(result["average_quiz_score"])
        self.assertEqual(result["topic_performance"], [])


class FeedbackTests(unittest.TestCase):
    def test_valid_feedback_and_optional_comments(self):
        repository = Repository()
        result = FeedbackService(repository).create(1, 3, 1, "Helpful answer")
        self.assertEqual(result.rating, 1)

    def test_invalid_rating_and_cross_student_query_are_rejected(self):
        service = FeedbackService(Repository())
        with self.assertRaises(ValueError):
            service.create(1, 3, 6)
        with self.assertRaises(LookupError):
            service.create(1, 999, 1)