import io
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from werkzeug.datastructures import FileStorage

from app.config.settings import get_settings
from app.modules.document_processing.pipeline import ExtractedPage, ProcessingError
from app.modules.educational_content_management.service import DocumentService
from app.modules.educational_content_management.storage import LocalDocumentStorage


@dataclass
class FakeDocument:
    document_id: int
    student_id: int
    title: str
    subject: str
    file_path: str
    upload_date: datetime


class FakeDocumentRepository:
    def __init__(self):
        self.documents = {}
        self.chunks = {}
        self.next_id = 1

    def create(self, student_id, title, subject, file_path, upload_date):
        document = FakeDocument(self.next_id, student_id, title, subject, file_path, upload_date)
        self.documents[self.next_id] = document
        self.next_id += 1
        return document

    def add_chunks(self, document_id, chunks):
        self.chunks[document_id] = chunks

    def list_owned(self, student_id):
        return [document for document in self.documents.values() if document.student_id == student_id]

    def get_owned(self, student_id, document_id):
        document = self.documents.get(document_id)
        return document if document and document.student_id == student_id else None

    def delete_owned(self, student_id, document_id):
        document = self.get_owned(student_id, document_id)
        if document is None:
            return False
        self.documents.pop(document_id)
        self.chunks.pop(document_id, None)
        return True


class FakeEmbedder:
    class Tokenizer:
        def encode(self, text, add_special_tokens=False):
            return text.split()

        def decode(self, token_ids, skip_special_tokens=True):
            return " ".join(token_ids)

    tokenizer = Tokenizer()

    def embed(self, texts):
        return [[0.0] * 384 for _ in texts]


class FakeVectorStore:
    def __init__(self):
        self.added = {}
        self.deleted = []

    def add_chunks(self, document_id, chunks, embeddings):
        ids = [f"document-{document_id}-chunk-{index}" for index in range(len(chunks))]
        self.added[document_id] = (ids, embeddings)
        return ids

    def delete_vectors(self, ids):
        self.deleted.extend(ids)

    def delete_document(self, document_id):
        self.deleted.append(f"document-{document_id}")


class DocumentServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        settings = get_settings()
        settings = settings.__class__(**{**settings.__dict__, "uploads_path": Path(self.directory.name)})
        self.repository = FakeDocumentRepository()
        self.vector_store = FakeVectorStore()
        self.service = DocumentService(
            settings,
            self.repository,
            storage=LocalDocumentStorage(Path(self.directory.name)),
            extractor=lambda path: [ExtractedPage(1, "one two three")],
            embedder=FakeEmbedder(),
            vector_store=self.vector_store,
        )

    def tearDown(self):
        self.directory.cleanup()

    def make_file(self, name="lesson.pdf"):
        return FileStorage(stream=io.BytesIO(b"document"), filename=name)

    def test_upload_persists_chunks_and_vectors(self):
        document = self.service.upload(4, self.make_file(), "Lesson", "Science")
        self.assertEqual(document.student_id, 4)
        self.assertEqual(len(self.repository.chunks[document.document_id]), 1)
        self.assertEqual(self.repository.chunks[document.document_id][0].metadata["document_id"], 1)
        self.assertEqual(len(self.vector_store.added[document.document_id][1][0]), 384)

    def test_processing_failure_does_not_report_success_or_leave_file(self):
        self.service.extractor = lambda path: (_ for _ in ()).throw(ProcessingError("no text"))
        with self.assertRaises(ProcessingError):
            self.service.upload(4, self.make_file(), "Broken", "Science")
        self.assertEqual(self.repository.documents, {})
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])

    def test_delete_removes_owned_document_and_vectors(self):
        document = self.service.upload(4, self.make_file(), "Lesson", "Science")
        self.assertTrue(self.service.delete_document(4, document.document_id))
        self.assertIsNone(self.repository.get_owned(4, document.document_id))
        self.assertIn(f"document-{document.document_id}", self.vector_store.deleted)

    def test_other_student_cannot_delete_document(self):
        document = self.service.upload(4, self.make_file(), "Lesson", "Science")
        self.assertFalse(self.service.delete_document(5, document.document_id))
        self.assertIsNotNone(self.repository.get_owned(4, document.document_id))