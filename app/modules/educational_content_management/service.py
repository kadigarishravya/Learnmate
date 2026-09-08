"""Educational document upload, processing, ownership, and cleanup service."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from app.config.settings import Settings
from app.infrastructure.chromadb.document_store import ChromaDocumentStore
from app.infrastructure.sentence_transformers.embeddings import SentenceTransformerEmbedder
from app.modules.document_processing.pipeline import (
    ProcessingError,
    TokenChunker,
    extract_pdf_pages,
)
from app.modules.educational_content_management.storage import (
    LocalDocumentStorage,
    validate_upload,
)

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(
        self,
        settings: Settings,
        repository,
        storage: LocalDocumentStorage | None = None,
        extractor=extract_pdf_pages,
        embedder: SentenceTransformerEmbedder | None = None,
        vector_store: ChromaDocumentStore | None = None,
    ):
        self.settings = settings
        self.repository = repository
        self.storage = storage or LocalDocumentStorage(settings.uploads_path)
        self.extractor = extractor
        self.embedder = embedder or SentenceTransformerEmbedder(settings)
        self.vector_store = vector_store or ChromaDocumentStore(settings)

    def upload(self, student_id: int, file, title: object, subject: object):
        title, subject, extension = validate_upload(
            file,
            title,
            subject,
            self.settings.supported_document_extensions,
            self.settings.max_upload_size_bytes,
        )
        path = self.storage.save(file, extension)
        document = None
        vector_ids: list[str] = []
        try:
            pages = self.extractor(path)
            chunker = TokenChunker(
                self.embedder.tokenizer,
                chunk_size=self.settings.chunk_size,
                chunk_overlap=self.settings.chunk_overlap,
            )
            chunks = chunker.chunk_pages(pages, document_id=0)
            embeddings = self.embedder.embed([chunk.text for chunk in chunks])
            if len(embeddings) != len(chunks):
                raise ProcessingError("embedding generation returned an invalid result")

            document = self.repository.create(
                student_id=student_id,
                title=title,
                subject=subject,
                file_path=str(path),
                upload_date=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            chunks = [
                replace(
                    chunk,
                    metadata={
                        **chunk.metadata,
                        "document_id": document.document_id,
                        "student_id": student_id,
                        "title": title,
                        "subject": subject,
                    },
                )
                for chunk in chunks
            ]
            vector_ids = self.vector_store.add_chunks(document.document_id, chunks, embeddings)
            self.repository.add_chunks(document.document_id, chunks)
            return document
        except Exception as exc:
            if vector_ids:
                try:
                    self.vector_store.delete_vectors(vector_ids)
                except Exception:
                    logger.exception("Failed to clean up vectors for failed document processing")
            if document is not None:
                try:
                    self.repository.delete_owned(student_id, document.document_id)
                except Exception:
                    logger.exception("Failed to clean up relational document after processing failure")
            self.storage.delete(path)
            if isinstance(exc, (ProcessingError, ValueError)):
                raise
            raise ProcessingError("document processing failed") from exc

    def list_documents(self, student_id: int):
        return self.repository.list_owned(student_id)

    def get_document(self, student_id: int, document_id: int):
        return self.repository.get_owned(student_id, document_id)

    def delete_document(self, student_id: int, document_id: int) -> bool:
        document = self.repository.get_owned(student_id, document_id)
        if document is None:
            return False
        self.vector_store.delete_document(document_id)
        deleted = self.repository.delete_owned(student_id, document_id)
        if deleted:
            self.storage.delete(Path(document.file_path))
        return deleted