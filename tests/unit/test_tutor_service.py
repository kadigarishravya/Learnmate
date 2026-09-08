import unittest
from dataclasses import dataclass, replace
from datetime import datetime

from app.config.settings import get_settings
from app.modules.llm_tutor.orchestration import TutorService
from app.modules.rag_retrieval.models import RetrievedChunk
from app.modules.student_management.sessions import SessionManager


@dataclass
class FakeQuery:
    query_id: int


@dataclass
class FakeResponse:
    response_id: int


class FakeQueryResponseRepository:
    def __init__(self):
        self.queries = []
        self.responses = []

    def create_query(self, **kwargs):
        self.queries.append(kwargs)
        return FakeQuery(len(self.queries))

    def create_response(self, **kwargs):
        self.responses.append(kwargs)
        return FakeResponse(len(self.responses))


class FakeEmbedder:
    class Tokenizer:
        def encode(self, text, add_special_tokens=False):
            return text.split()

    tokenizer = Tokenizer()

    def __init__(self, error=False):
        self.error = error
        self.inputs = []

    def embed(self, texts):
        if self.error:
            raise RuntimeError("embedding failed")
        self.inputs.extend(texts)
        return [[0.0] * 384 for _ in texts]


class FakeVectorStore:
    def __init__(self, chunks):
        self.chunks = chunks
        self.arguments = None

    def search(self, **kwargs):
        self.arguments = kwargs
        return self.chunks


class FakeReranker:
    def __init__(self, chunks):
        self.chunks = chunks
        self.query = None

    def rerank(self, query, candidates):
        self.query = query
        return self.chunks


class FakeTutor:
    model_name = "test-configured-model"

    def __init__(self):
        self.messages = []

    def generate(self, messages):
        self.messages.append(messages)
        return "Grounded tutor response"


class TutorServiceTests(unittest.TestCase):
    def setUp(self):
        self.settings = replace(get_settings(), cohere_api_key="test-key")
        self.sessions = SessionManager(1800)
        self.session_id = self.sessions.create(7)
        self.repository = FakeQueryResponseRepository()
        self.chunk = RetrievedChunk(
            "document-1-chunk-0",
            "Newton's second law relates force, mass, and acceleration.",
            {"title": "Physics", "subject": "Physics", "page_number": "2", "student_id": "7"},
        )
        self.embedder = FakeEmbedder()
        self.vector = FakeVectorStore([self.chunk])
        self.reranker = FakeReranker([self.chunk])
        self.tutor = FakeTutor()
        self.service = TutorService(
            self.settings,
            self.repository,
            self.sessions,
            self.embedder,
            self.vector,
            reranker=self.reranker,
            tutor=self.tutor,
        )

    def test_query_response_persistence_and_student_scoped_retrieval(self):
        result = self.service.answer(7, self.session_id, "Explain physics force")
        self.assertEqual(result.response_text, "Grounded tutor response")
        self.assertTrue(result.grounded)
        self.assertEqual(self.repository.queries[0]["student_id"], 7)
        self.assertEqual(self.repository.responses[0]["query_id"], 1)
        self.assertEqual(self.repository.responses[0]["model_name"], "test-configured-model")
        self.assertEqual(self.vector.arguments["student_id"], 7)
        self.assertEqual(self.vector.arguments["top_k"], 8)

    def test_second_turn_receives_previous_context(self):
        self.service.answer(7, self.session_id, "Explain Newton's second law")
        self.service.answer(7, self.session_id, "Explain it simply")
        self.assertIn("Newton's second law", self.tutor.messages[-1][0]["content"])

    def test_no_chunks_returns_transparent_non_grounded_response(self):
        self.service.vector_store.chunks = []
        self.service.reranker.chunks = []
        result = self.service.answer(7, self.session_id, "What is unknown topic?")
        self.assertFalse(result.grounded)
        self.assertIsNone(result.response_id)
        self.assertIn("do not contain enough information", result.response_text)
        self.assertEqual(self.repository.responses, [])

    def test_embedding_failure_does_not_generate_response(self):
        self.service.embedder = FakeEmbedder(error=True)
        with self.assertRaises(RuntimeError):
            self.service.answer(7, self.session_id, "Explain this")
        self.assertEqual(self.repository.responses, [])

    def test_chroma_failure_does_not_generate_response(self):
        class BrokenVector:
            def search(self, **kwargs):
                raise RuntimeError("Chroma failure")

        self.service.vector_store = BrokenVector()
        with self.assertRaises(RuntimeError):
            self.service.answer(7, self.session_id, "Explain physics")
        self.assertEqual(self.repository.responses, [])

    def test_query_database_failure_does_not_generate_response(self):
        class BrokenRepository(FakeQueryResponseRepository):
            def create_query(self, **kwargs):
                raise RuntimeError("database failure")

        self.service.repository = BrokenRepository()
        with self.assertRaises(RuntimeError):
            self.service.answer(7, self.session_id, "Explain physics")

    def test_six_turn_limit_and_clear_context(self):
        for index in range(7):
            self.sessions.add_turn(self.session_id, f"q{index}", f"a{index}")
        context = self.sessions.get_context(self.session_id)
        self.assertEqual(len(context), 6)
        self.assertEqual(context[0]["question"], "q1")
        self.sessions.clear_context(self.session_id)
        self.assertEqual(self.sessions.get_context(self.session_id), [])

    def test_logout_invalidation_clears_context(self):
        self.sessions.add_turn(self.session_id, "q", "a")
        self.sessions.invalidate(self.session_id)
        self.assertEqual(self.sessions.get_context(self.session_id), [])