import unittest
from dataclasses import replace

from app.config.settings import get_settings
from app.modules.query_understanding.models import QueryUnderstanding
from app.modules.query_understanding.service import QueryUnderstandingService


class QueryUnderstandingTests(unittest.TestCase):
    def setUp(self):
        self.settings = replace(get_settings(), cohere_api_key=None)
        self.service = QueryUnderstandingService(self.settings)

    def test_obvious_intent_subject_and_topic(self):
        result = self.service.analyze(
            "Explain Newton's second law in simple words with an example in physics",
            [],
        )
        self.assertEqual(result.intent, "explanation")
        self.assertEqual(result.subject, "Physics")
        self.assertEqual(result.topic, "newton's second law")
        self.assertEqual(result.difficulty, "beginner")
        self.assertEqual(result.expected_response_type, "explanation")

    def test_ambiguous_values_remain_unknown_without_cohere(self):
        result = self.service.analyze("Can you help me with this?", [])
        self.assertIsNone(result.intent)
        self.assertIsNone(result.subject)
        self.assertIsNone(result.topic)
        self.assertIsNone(result.difficulty)

    def test_follow_up_uses_previous_context(self):
        result = self.service.analyze(
            "Explain it more simply", [{"question": "What is photosynthesis?", "response": "..."}]
        )
        self.assertEqual(result.context, "What is photosynthesis?")

    def test_runtime_object_has_only_q3_attributes(self):
        fields = set(QueryUnderstanding.__dataclass_fields__)
        self.assertEqual(
            fields,
            {
                "intent",
                "subject",
                "topic",
                "context",
                "expected_response_type",
                "difficulty",
                "confidence",
            },
        )