import unittest
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from app.config.settings import get_settings
from app.modules.adaptive_learning.service import AdaptiveLearningService


@dataclass
class Item:
    topic: str
    score: float | None = None
    interaction_date: datetime = datetime.now()


class AdaptiveLearningTests(unittest.TestCase):
    def setUp(self):
        settings = replace(
            get_settings(), adaptive_min_quiz_attempts=2,
            adaptive_min_interactions=5, adaptive_weak_score_threshold=60,
        )
        self.service = AdaptiveLearningService(settings)

    def test_fewer_than_two_quizzes_is_not_quiz_eligible(self):
        status = self.service.topic_status([Item("Math", 40)], [])[0]
        self.assertFalse(status["eligible"])
        self.assertFalse(status["weak"])

    def test_two_low_quizzes_mark_topic_weak(self):
        status = self.service.topic_status([Item("Math", 40), Item("Math", 50)], [])[0]
        self.assertTrue(status["eligible"])
        self.assertTrue(status["weak"])
        self.assertEqual(status["average_score"], 45)

    def test_two_scores_at_threshold_are_not_weak_by_score(self):
        status = self.service.topic_status([Item("Math", 60), Item("Math", 60)], [])[0]
        self.assertFalse(status["weak"])

    def test_five_interactions_can_mark_topic_weak_without_quiz_score(self):
        interactions = [Item("Math", None, datetime.now() - timedelta(days=index)) for index in range(5)]
        status = self.service.topic_status([], interactions)[0]
        self.assertTrue(status["eligible"])
        self.assertTrue(status["weak"])

    def test_frequently_studied_topic_with_quiz_score_is_not_automatically_weak(self):
        interactions = [Item("Math", None) for _ in range(5)]
        status = self.service.topic_status([Item("Math", 80), Item("Math", 80)], interactions)[0]
        self.assertFalse(status["weak"])

    def test_same_weak_topic_logic_is_used_by_weak_topics(self):
        quizzes = [Item("Math", 50), Item("Math", 50), Item("Physics", 90)]
        self.assertEqual([item["topic"] for item in self.service.weak_topics(quizzes, [])], ["Math"])