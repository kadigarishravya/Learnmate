import os
import unittest
from unittest.mock import patch

from app.config.settings import get_settings


class SettingsTests(unittest.TestCase):
    def test_defaults_use_locked_rag_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = get_settings()
        self.assertEqual(settings.embedding_model, "sentence-transformers/all-MiniLM-L6-v2")
        self.assertEqual(settings.chunk_size, 512)
        self.assertEqual(settings.chunk_overlap, 80)
        self.assertEqual(settings.retrieval_top_k, 8)
        self.assertEqual(settings.rerank_top_n, 4)
        self.assertEqual(settings.context_token_limit, 6000)

    def test_sqlite_database_path_defaults_to_storage_location(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = get_settings()
        self.assertEqual(
            settings.sqlite_database_path.name,
            "learnmate.db",
        )
        self.assertTrue(
            settings.sqlalchemy_url.startswith("sqlite:///")
        )
        self.assertTrue(
            settings.sqlalchemy_url.endswith("storage\\learnmate.db")
        )