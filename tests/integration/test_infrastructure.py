import os
import gc
import shutil
import tempfile
import unittest
from unittest.mock import patch
from dataclasses import replace
from pathlib import Path

from app.config.settings import get_settings
from app.infrastructure.chromadb.client import check_initialization
from app.infrastructure.chromadb.document_store import ChromaDocumentStore
from app.infrastructure.cohere.client import check_configuration
from app.infrastructure.sql_server.connection import check_connection
from app.infrastructure.sql_server.connection import create_engine
from app.infrastructure.sentence_transformers.embeddings import SentenceTransformerEmbedder
from app.modules.document_processing.pipeline import ProcessedChunk


class InfrastructureTests(unittest.TestCase):
    @unittest.skipUnless(os.getenv("RUN_SQL_SERVER_TESTS") == "1", "SQL Server integration disabled")
    def test_sql_server_connection(self):
        check_connection(get_settings())

    @unittest.skipUnless(os.getenv("RUN_SQL_SERVER_TESTS") == "1", "SQL Server integration disabled")
    def test_sql_server_has_exact_documented_tables(self):
        from sqlalchemy import inspect

        engine = create_engine(get_settings())
        try:
            actual = set(inspect(engine).get_table_names())
        finally:
            engine.dispose()
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
        self.assertEqual(actual, expected)

    @unittest.skipUnless(os.getenv("RUN_CHROMA_TESTS") == "1", "ChromaDB integration disabled")
    def test_chromadb_initialization(self):
        check_initialization(get_settings())

    @unittest.skipUnless(os.getenv("RUN_CHROMA_TESTS") == "1", "ChromaDB integration disabled")
    def test_chromadb_persists_document_chunk(self):
        directory = tempfile.mkdtemp()
        try:
            settings = replace(get_settings(), chroma_path=Path(directory))
            store = ChromaDocumentStore(settings)
            chunks = [ProcessedChunk(0, "persistent text", {"document_id": 4, "chunk_index": 0})]
            ids = store.add_chunks(4, chunks, [[0.0] * 384])
            result = store.collection.get(ids=ids)
            self.assertEqual(result["ids"], ids)
            self.assertEqual(result["documents"], ["persistent text"])
            store.delete_document(4)
            self.assertEqual(store.collection.get(ids=ids)["ids"], [])
        finally:
            del store
            gc.collect()
            shutil.rmtree(directory, ignore_errors=True)

    @unittest.skipUnless(
        os.getenv("RUN_EMBEDDING_TESTS") == "1", "Sentence Transformer integration disabled"
    )
    def test_sentence_transformer_generates_384_dimension_embedding(self):
        embedder = SentenceTransformerEmbedder(get_settings())
        vectors = embedder.embed(["LearnMate embedding validation"])
        self.assertEqual(len(vectors), 1)
        self.assertEqual(len(vectors[0]), 384)

    def test_cohere_configuration_fails_clearly_when_missing(self):
        with patch.dict(os.environ, {"COHERE_API_KEY": ""}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "COHERE_API_KEY"):
                check_configuration(get_settings())