"""Exercise local startup and tutor persistence against a real, fresh SQLite DB."""

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from app.api.factory import create_app
from app.config.settings import get_settings
from app.infrastructure.sql_server.connection import create_session_factory
from app.infrastructure.sql_server.models import Query, Response
from app.infrastructure.sql_server.query_response_repository import QueryResponseRepository
from app.modules.llm_tutor.orchestration import TutorService
from tests.unit.test_tutor_service import FakeEmbedder, FakeReranker, FakeTutor, FakeVectorStore
from app.modules.rag_retrieval.models import RetrievedChunk


class LocalStartupTests(unittest.TestCase):
    def test_fresh_database_registration_and_question_without_subject(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = replace(get_settings(), sqlite_database_path=Path(directory) / "new" / "learnmate.db")
            app = create_app(settings)
            client = app.test_client()
            factory = create_session_factory(settings)
            try:
                credentials = {"email": "student@example.com", "password": "test-password-123"}
                response = client.post("/api/auth/register", json={"name": "Student", **credentials})
                self.assertEqual(response.status_code, 201, response.get_json())
                login = client.post("/api/auth/login", json=credentials)
                self.assertEqual(login.status_code, 200)
                headers = {"X-Session-ID": login.get_json()["session_id"]}
                chunk = RetrievedChunk("chunk-1", "Force equals mass times acceleration.", {"title": "Notes"})
                app.config["LEARNMATE_TUTOR_SERVICE"] = TutorService(
                    settings, QueryResponseRepository(factory),
                    app.config["LEARNMATE_SESSION_MANAGER"], FakeEmbedder(),
                    FakeVectorStore([chunk]), reranker=FakeReranker([chunk]), tutor=FakeTutor(),
                )
                answer = client.post("/api/tutor/query", headers=headers, json={"question": "Explain Newton's second law"})
                self.assertEqual(answer.status_code, 200, answer.get_json())
                self.assertTrue(answer.get_json()["grounded"])
                with factory() as session:
                    self.assertEqual(session.query(Query).one().subject, "General")
                    self.assertEqual(session.query(Response).count(), 1)
            finally:
                factory.kw["bind"].dispose()
                create_session_factory.cache_clear()
