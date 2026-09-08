import unittest
from dataclasses import replace
from types import SimpleNamespace

from app.config.settings import get_settings
from app.modules.context_generation.builder import ContextBuilder
from app.infrastructure.chromadb.document_store import ChromaDocumentStore
from app.modules.query_understanding.models import QueryUnderstanding
from app.modules.rag_retrieval.models import RetrievedChunk
from app.modules.rag_retrieval.service import CohereReranker


class FakeRerankClient:
    def __init__(self):
        self.arguments = None

    def rerank(self, **kwargs):
        self.arguments = kwargs
        return SimpleNamespace(
            results=[SimpleNamespace(index=1, relevance_score=0.9), SimpleNamespace(index=0, relevance_score=0.8)]
        )


class FakeCollection:
    def query(self, **kwargs):
        self.query_arguments = kwargs
        return {
            "ids": [["chunk-1"]],
            "documents": [["owned text"]],
            "metadatas": [[{"student_id": "4"}]],
            "distances": [[0.1]],
        }


class RagComponentTests(unittest.TestCase):
    def test_rerank_uses_configured_top_n_and_candidates(self):
        settings = replace(get_settings(), cohere_api_key="test-key", rerank_top_n=4)
        client = FakeRerankClient()
        reranker = CohereReranker(settings, client=client)
        candidates = [
            RetrievedChunk("a", "first", {"title": "A"}),
            RetrievedChunk("b", "second", {"title": "B"}),
        ]
        selected = reranker.rerank("question", candidates)
        self.assertEqual(client.arguments["top_n"], 4)
        self.assertEqual(client.arguments["documents"], ["first", "second"])
        self.assertEqual([chunk.chunk_id for chunk in selected], ["b", "a"])

    def test_chroma_search_filters_by_authenticated_student_and_top_k(self):
        collection = FakeCollection()
        store = object.__new__(ChromaDocumentStore)
        store.collection = collection
        chunks = store.search([0.0] * 384, student_id=4, top_k=8)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(collection.query_arguments["n_results"], 8)
        self.assertEqual(collection.query_arguments["where"], {"student_id": "4"})

    def test_context_is_deduplicated_and_bounded(self):
        builder = ContextBuilder(token_counter=lambda text: text.split(), max_tokens=8)
        chunks = [
            RetrievedChunk("a", "one two", {"title": "A", "subject": "Math", "page_number": 1}),
            RetrievedChunk("a", "duplicate", {"title": "A"}),
            RetrievedChunk("b", "three four five six seven", {"title": "B"}),
        ]
        context, sources = builder.select(chunks)
        self.assertIn("one two", context)
        self.assertEqual(len(sources), 1)

    def test_langchain_messages_include_question_context_and_user_role(self):
        builder = ContextBuilder(token_counter=lambda text: text.split(), max_tokens=100)
        messages = builder.build_messages(
            "What is it?",
            QueryUnderstanding(context="photosynthesis"),
            [{"question": "What is photosynthesis?", "response": "A process."}],
            "[Source: Biology; Subject: Biology; Page: 1]\nPhotosynthesis is...",
        )
        self.assertEqual(messages[-1]["role"], "user")
        self.assertIn("What is it?", messages[-1]["content"])
        self.assertIn("photosynthesis", messages[0]["content"])

    def test_missing_cohere_key_is_controlled(self):
        settings = replace(get_settings(), cohere_api_key=None)
        reranker = CohereReranker(settings)
        with self.assertRaisesRegex(RuntimeError, "COHERE_API_KEY"):
            reranker.rerank("question", [RetrievedChunk("a", "text", {})])

    def test_cohere_failure_is_controlled(self):
        class BrokenClient:
            def rerank(self, **kwargs):
                raise RuntimeError("provider failure")

        settings = replace(get_settings(), cohere_api_key="test-key")
        reranker = CohereReranker(settings, client=BrokenClient())
        with self.assertRaisesRegex(RuntimeError, "Cohere Rerank request failed"):
            reranker.rerank("question", [RetrievedChunk("a", "text", {})])