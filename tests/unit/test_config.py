import os
import unittest
from unittest.mock import patch

from app.config.settings import PROJECT_ROOT, get_settings


class SettingsTests(unittest.TestCase):
    def test_relative_storage_paths_are_anchored_to_repository(self):
        with patch.dict(os.environ, {
            "SQLITE_DATABASE_PATH": "storage/custom.db",
            "UPLOADS_PATH": "storage/uploads",
            "CHROMA_PATH": "storage/chroma",
        }):
            settings = get_settings()
        self.assertEqual(settings.sqlite_database_path, PROJECT_ROOT / "storage/custom.db")
        self.assertEqual(settings.uploads_path, PROJECT_ROOT / "storage/uploads")
        self.assertEqual(settings.chroma_path, PROJECT_ROOT / "storage/chroma")

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
