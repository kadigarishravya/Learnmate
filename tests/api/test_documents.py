import io
import unittest
from dataclasses import dataclass
from datetime import datetime

from werkzeug.datastructures import FileStorage

from app.api.factory import create_app
from app.config.settings import get_settings


@dataclass
class FakeDocument:
    document_id: int
    student_id: int
    title: str
    subject: str
    file_path: str
    upload_date: datetime


class FakeDocumentService:
    def __init__(self):
        self.documents = {1: FakeDocument(1, 1, "Owned", "Math", "internal", datetime.now())}

    def list_documents(self, student_id):
        return [document for document in self.documents.values() if document.student_id == student_id]

    def get_document(self, student_id, document_id):
        document = self.documents.get(document_id)
        return document if document and document.student_id == student_id else None

    def delete_document(self, student_id, document_id):
        document = self.get_document(student_id, document_id)
        if document is None:
            return False
        del self.documents[document_id]
        return True


class DocumentApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(get_settings())
        self.service = FakeDocumentService()
        self.app.config["LEARNMATE_DOCUMENT_SERVICE"] = self.service
        self.client = self.app.test_client()
        self.session_id = self.app.config["LEARNMATE_SESSION_MANAGER"].create(1)

    def test_unauthenticated_upload_is_rejected(self):
        response = self.client.post("/api/documents")
        self.assertEqual(response.status_code, 401)

    def test_list_and_get_enforce_document_ownership(self):
        own = self.client.get("/api/documents", headers={"X-Session-ID": self.session_id})
        other_session = self.app.config["LEARNMATE_SESSION_MANAGER"].create(2)
        other = self.client.get(
            "/api/documents/1", headers={"X-Session-ID": other_session}
        )
        self.assertEqual(own.status_code, 200)
        self.assertEqual(other.status_code, 404)

    def test_delete_enforces_document_ownership(self):
        other_session = self.app.config["LEARNMATE_SESSION_MANAGER"].create(2)
        response = self.client.delete(
            "/api/documents/1", headers={"X-Session-ID": other_session}
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn(1, self.service.documents)