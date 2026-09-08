import io
import tempfile
import unittest
from pathlib import Path

from werkzeug.datastructures import FileStorage

from app.modules.educational_content_management.storage import (
    DocumentValidationError,
    LocalDocumentStorage,
    validate_upload,
)


class DocumentStorageTests(unittest.TestCase):
    def make_file(self, filename, content=b"pdf"):
        return FileStorage(stream=io.BytesIO(content), filename=filename)

    def test_invalid_extension_is_rejected(self):
        with self.assertRaises(DocumentValidationError):
            validate_upload(self.make_file("notes.txt"), "Notes", "Physics", (".pdf",), 100)

    def test_oversized_file_is_rejected(self):
        with self.assertRaises(DocumentValidationError):
            validate_upload(self.make_file("notes.pdf", b"12345"), "Notes", "Physics", (".pdf",), 4)

    def test_storage_uses_generated_filename_inside_root(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = LocalDocumentStorage(Path(directory))
            path = storage.save(self.make_file("../../unsafe.pdf"), ".pdf")
            self.assertEqual(path.parent, Path(directory).resolve())
            self.assertTrue(path.exists())