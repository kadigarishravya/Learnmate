import unittest

from app.infrastructure.chromadb.document_store import ChromaDocumentStore
from app.modules.document_processing.pipeline import ProcessedChunk


class FakeCollection:
    def __init__(self):
        self.upserts = []
        self.deletions = []

    def upsert(self, **kwargs):
        self.upserts.append(kwargs)

    def delete(self, **kwargs):
        self.deletions.append(kwargs)


class ChromaStoreTests(unittest.TestCase):
    def test_vector_ids_are_deterministic(self):
        self.assertEqual(
            ChromaDocumentStore.vector_ids(12, 2),
            ["document-12-chunk-0", "document-12-chunk-1"],
        )

    def test_chunk_upsert_and_delete_preserve_document_identity(self):
        collection = FakeCollection()
        store = object.__new__(ChromaDocumentStore)
        store.collection = collection
        chunks = [
            ProcessedChunk(0, "text", {"document_id": 7, "chunk_index": 0, "page_number": 1})
        ]
        ids = store.add_chunks(7, chunks, [[0.0] * 384])
        store.delete_document(7)
        self.assertEqual(ids, ["document-7-chunk-0"])
        self.assertEqual(collection.upserts[0]["ids"], ids)
        self.assertEqual(collection.upserts[0]["metadatas"][0]["document_id"], "7")
        self.assertEqual(collection.deletions, [{"where": {"document_id": "7"}}])