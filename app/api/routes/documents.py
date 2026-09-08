"""Authenticated educational document endpoints."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.api.routes.auth import _authenticated_student_id, _student_repository
from app.infrastructure.chromadb.document_store import ChromaDocumentStore
from app.infrastructure.sql_server.connection import create_session_factory
from app.modules.educational_content_management.repository import DocumentRepository
from app.modules.educational_content_management.service import DocumentService
from app.modules.educational_content_management.storage import DocumentValidationError
from app.modules.document_processing.pipeline import ProcessingError


documents_bp = Blueprint("documents", __name__, url_prefix="/api/documents")


def _document_repository() -> DocumentRepository:
    repository = current_app.config.get("LEARNMATE_DOCUMENT_REPOSITORY")
    if repository is not None:
        return repository
    settings = current_app.config["LEARNMATE_SETTINGS"]
    return DocumentRepository(create_session_factory(settings))


def _document_service() -> DocumentService:
    service = current_app.config.get("LEARNMATE_DOCUMENT_SERVICE")
    if service is not None:
        return service
    settings = current_app.config["LEARNMATE_SETTINGS"]
    return DocumentService(
        settings,
        _document_repository(),
        vector_store=ChromaDocumentStore(settings),
    )


def _document_payload(document) -> dict[str, object]:
    return {
        "document_id": document.document_id,
        "student_id": document.student_id,
        "title": document.title,
        "subject": document.subject,
        "upload_date": document.upload_date.isoformat(),
    }


def _require_student_id() -> int | None:
    return _authenticated_student_id()


@documents_bp.post("")
def upload_document():
    student_id = _require_student_id()
    if student_id is None:
        return jsonify({"error": "authentication required"}), 401
    try:
        document = _document_service().upload(
            student_id,
            request.files.get("file"),
            request.form.get("title"),
            request.form.get("subject"),
        )
    except DocumentValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except ProcessingError as exc:
        return jsonify({"error": str(exc)}), 422
    except (RuntimeError, OSError) as exc:
        current_app.logger.error("Document upload infrastructure failure: %s", exc)
        return jsonify({"error": "document processing unavailable"}), 503
    return jsonify({"document": _document_payload(document)}), 201


@documents_bp.get("")
def list_documents():
    student_id = _require_student_id()
    if student_id is None:
        return jsonify({"error": "authentication required"}), 401
    try:
        documents = _document_service().list_documents(student_id)
    except (RuntimeError, OSError) as exc:
        current_app.logger.error("Document listing database failure: %s", exc)
        return jsonify({"error": "database unavailable"}), 503
    return jsonify({"documents": [_document_payload(document) for document in documents]}), 200


@documents_bp.get("/<int:document_id>")
def get_document(document_id: int):
    student_id = _require_student_id()
    if student_id is None:
        return jsonify({"error": "authentication required"}), 401
    document = _document_service().get_document(student_id, document_id)
    if document is None:
        return jsonify({"error": "document not found"}), 404
    return jsonify({"document": _document_payload(document)}), 200


@documents_bp.delete("/<int:document_id>")
def delete_document(document_id: int):
    student_id = _require_student_id()
    if student_id is None:
        return jsonify({"error": "authentication required"}), 401
    try:
        deleted = _document_service().delete_document(student_id, document_id)
    except (RuntimeError, OSError) as exc:
        current_app.logger.error("Document deletion failure: %s", exc)
        return jsonify({"error": "document deletion unavailable"}), 503
    if not deleted:
        return jsonify({"error": "document not found"}), 404
    return jsonify({"status": "deleted"}), 200