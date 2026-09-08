"""SQL Server persistence for Document and Document_Chunk."""

from __future__ import annotations

import json
from collections.abc import Callable

from sqlalchemy import select

from app.infrastructure.sql_server.models import Document, DocumentChunk


class DocumentRepository:
    def __init__(self, session_factory: Callable):
        self._session_factory = session_factory

    def create(self, student_id: int, title: str, subject: str, file_path: str, upload_date) -> Document:
        with self._session_factory() as session:
            document = Document(
                student_id=student_id,
                title=title,
                subject=subject,
                file_path=file_path,
                upload_date=upload_date,
            )
            session.add(document)
            session.commit()
            session.refresh(document)
            return document

    def add_chunks(self, document_id: int, chunks) -> None:
        with self._session_factory() as session:
            session.add_all(
                DocumentChunk(
                    document_id=document_id,
                    text=chunk.text,
                    chunk_metadata=json.dumps(chunk.metadata),
                )
                for chunk in chunks
            )
            session.commit()

    def list_owned(self, student_id: int) -> list[Document]:
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(Document)
                    .where(Document.student_id == student_id)
                    .order_by(Document.upload_date.desc())
                )
            )

    def get_owned(self, student_id: int, document_id: int) -> Document | None:
        with self._session_factory() as session:
            return session.scalar(
                select(Document).where(
                    Document.document_id == document_id,
                    Document.student_id == student_id,
                )
            )

    def delete_owned(self, student_id: int, document_id: int) -> bool:
        with self._session_factory() as session:
            document = session.scalar(
                select(Document).where(
                    Document.document_id == document_id,
                    Document.student_id == student_id,
                )
            )
            if document is None:
                return False
            session.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
            session.delete(document)
            session.commit()
            return True