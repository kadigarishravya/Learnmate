import unittest

from app.infrastructure.sql_server.models import Base


class SchemaMetadataTests(unittest.TestCase):
    def test_metadata_contains_exactly_the_documented_entities(self):
        expected = {
            "Student",
            "Document",
            "Document_Chunk",
            "Query",
            "Response",
            "Quiz",
            "Learning_History",
            "Recommendation",
            "Feedback",
        }
        self.assertEqual(set(Base.metadata.tables), expected)
        self.assertEqual(len(Base.metadata.tables), 9)

    def test_documented_fields_are_preserved(self):
        self.assertEqual(
            set(Base.metadata.tables["Student"].columns.keys()),
            {"student_id", "name", "email", "password", "registration_date"},
        )
        self.assertEqual(
            set(Base.metadata.tables["Feedback"].columns.keys()),
            {"feedback_id", "student_id", "query_id", "rating", "comments"},
        )
        self.assertEqual(
            set(Base.metadata.tables["Query"].columns.keys()),
            {"query_id", "student_id", "question", "subject", "timestamp"},
        )
        self.assertEqual(
            set(Base.metadata.tables["Response"].columns.keys()),
            {"response_id", "query_id", "response_text", "model_name", "timestamp"},
        )