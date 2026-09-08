"""Authenticated RAG tutor endpoint."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.api.routes.auth import _authenticated_student_id
from app.infrastructure.chromadb.document_store import ChromaDocumentStore
from app.infrastructure.sentence_transformers.embeddings import SentenceTransformerEmbedder
from app.infrastructure.sql_server.connection import create_session_factory
from app.infrastructure.sql_server.query_response_repository import QueryResponseRepository
from app.modules.context_generation.builder import NO_CONTEXT_RESPONSE
from app.modules.llm_tutor.orchestration import TutorService
from app.modules.student_management.sessions import SessionManager


tutor_bp = Blueprint("tutor", __name__, url_prefix="/api/tutor")


def _tutor_service() -> TutorService:
    service = current_app.config.get("LEARNMATE_TUTOR_SERVICE")
    if service is not None:
        return service
    settings = current_app.config["LEARNMATE_SETTINGS"]
    repository = QueryResponseRepository(create_session_factory(settings))
    embedder = SentenceTransformerEmbedder(settings)
    return TutorService(
        settings,
        repository,
        current_app.config["LEARNMATE_SESSION_MANAGER"],
        embedder,
        ChromaDocumentStore(settings),
    )


@tutor_bp.post("/query")
def query_tutor():
    student_id = _authenticated_student_id()
    if student_id is None:
        return jsonify({"error": "authentication required"}), 401
    session_id = request.headers.get("X-Session-ID")
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload.get("question"), str) or not payload["question"].strip():
        return jsonify({"error": "question is required"}), 400
    try:
        result = _tutor_service().answer(student_id, session_id, payload.get("question"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        current_app.logger.error("Tutor processing failure: %s", exc)
        return jsonify({"error": str(exc)}), 503
    return jsonify(
        {
            "query_id": result.query_id,
            "response_id": result.response_id,
            "response": result.response_text,
            "grounded": result.grounded,
            "sources": result.sources,
        }
    ), 200


@tutor_bp.delete("/context")
def clear_tutor_context():
    student_id = _authenticated_student_id()
    if student_id is None:
        return jsonify({"error": "authentication required"}), 401
    session_id = request.headers.get("X-Session-ID")
    current_app.config["LEARNMATE_SESSION_MANAGER"].clear_context(session_id)
    return jsonify({"status": "context_cleared"}), 200