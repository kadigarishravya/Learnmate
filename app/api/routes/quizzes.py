"""Authenticated quiz and adaptive-learning endpoints."""

from __future__ import annotations

import json

from flask import Blueprint, current_app, jsonify, request

from app.api.routes.auth import _authenticated_student_id
from app.infrastructure.chromadb.document_store import ChromaDocumentStore
from app.infrastructure.cohere.client import create_client
from app.infrastructure.sentence_transformers.embeddings import SentenceTransformerEmbedder
from app.infrastructure.sql_server.connection import create_session_factory
from app.infrastructure.sql_server.quiz_repository import QuizRepository
from app.modules.adaptive_learning.service import AdaptiveLearningService
from app.modules.context_generation.builder import ContextBuilder
from app.modules.query_understanding.models import QueryUnderstanding
from app.modules.quiz_assessment.service import QuizService
from app.modules.quiz_assessment.state import QuizStateStore
from app.modules.rag_retrieval.service import CohereReranker


quizzes_bp = Blueprint("quizzes", __name__, url_prefix="/api/quizzes")


def _repository():
    repository = current_app.config.get("LEARNMATE_QUIZ_REPOSITORY")
    if repository is not None:
        return repository
    settings = current_app.config["LEARNMATE_SETTINGS"]
    return QuizRepository(create_session_factory(settings))


def _context_provider(student_id: int, topic: str) -> str:
    settings = current_app.config["LEARNMATE_SETTINGS"]
    embedder = SentenceTransformerEmbedder(settings)
    vector_store = ChromaDocumentStore(settings)
    query_embedding = embedder.embed([topic])[0]
    candidates = vector_store.search(query_embedding, student_id, settings.retrieval_top_k)
    reranked = CohereReranker(settings).rerank(topic, candidates)
    context, _ = ContextBuilder(
        token_counter=lambda value: embedder.tokenizer.encode(value, add_special_tokens=False),
        max_tokens=settings.context_token_limit,
    ).select(reranked)
    return context


def _generator(context, topic, difficulty, count):
    settings = current_app.config["LEARNMATE_SETTINGS"]
    client = create_client(settings)
    prompt = (
        f"Create exactly {count} quiz questions about {topic} at {difficulty} difficulty. "
        "Use only the supplied uploaded educational context. Return JSON only as an array "
        "of objects with question, options (array), correct_answer.\nContext:\n" + context
    )
    try:
        response = client.chat(
            model=settings.cohere_chat_model,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.message.content[0].text
        return json.loads(text)
    except Exception as exc:
        raise RuntimeError("Cohere Chat quiz generation failed") from exc


def _service() -> QuizService:
    service = current_app.config.get("LEARNMATE_QUIZ_SERVICE")
    if service is not None:
        return service
    settings = current_app.config["LEARNMATE_SETTINGS"]
    store = current_app.config.setdefault(
        "LEARNMATE_QUIZ_STATE_STORE", QuizStateStore(settings.quiz_state_timeout_seconds)
    )
    return QuizService(
        settings,
        store,
        _repository(),
        context_provider=_context_provider,
        generator=_generator,
        adaptive=AdaptiveLearningService(settings),
    )


def _session_id() -> str | None:
    return request.headers.get("X-Session-ID")


@quizzes_bp.post("")
def create_quiz():
    student_id = _authenticated_student_id()
    if student_id is None:
        return jsonify({"error": "authentication required"}), 401
    payload = request.get_json(silent=True) or {}
    try:
        state = _service().create(student_id, _session_id(), payload.get("topic"), payload.get("difficulty"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 422
    except RuntimeError as exc:
        current_app.logger.error("Quiz generation failure: %s", exc)
        return jsonify({"error": str(exc)}), 503
    return jsonify({
        "quiz_id": state.quiz_id,
        "topic": state.topic,
        "difficulty": state.difficulty,
        "questions": _service().public_questions(state),
    }), 201


@quizzes_bp.get("/<int:quiz_id>")
def get_quiz(quiz_id: int):
    student_id = _authenticated_student_id()
    if student_id is None:
        return jsonify({"error": "authentication required"}), 401
    state = _service().get(student_id, _session_id(), quiz_id)
    if state is None:
        return jsonify({"error": "quiz not found or expired"}), 404
    return jsonify({
        "quiz_id": state.quiz_id,
        "topic": state.topic,
        "difficulty": state.difficulty,
        "questions": _service().public_questions(state),
    }), 200


@quizzes_bp.post("/<int:quiz_id>/submit")
def submit_quiz(quiz_id: int):
    student_id = _authenticated_student_id()
    if student_id is None:
        return jsonify({"error": "authentication required"}), 401
    payload = request.get_json(silent=True) or {}
    try:
        quiz, history, score = _service().submit(
            student_id, _session_id(), quiz_id, payload.get("answers")
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except RuntimeError as exc:
        current_app.logger.error("Quiz persistence failure: %s", exc)
        return jsonify({"error": "quiz result persistence failed"}), 503
    return jsonify({
        "quiz_id": quiz.quiz_id,
        "topic": quiz.topic,
        "difficulty": quiz.difficulty,
        "score": score,
        "history_id": history.history_id,
    }), 200


@quizzes_bp.get("/adaptive/status")
def adaptive_status():
    student_id = _authenticated_student_id()
    if student_id is None:
        return jsonify({"error": "authentication required"}), 401
    repository = _repository()
    try:
        quiz_history = repository.list_history(student_id)
        tutor_interactions = [
            type("Interaction", (), {"topic": item.subject, "interaction_date": item.timestamp})()
            for item in repository.list_tutor_interactions(student_id)
        ]
        statuses = AdaptiveLearningService(current_app.config["LEARNMATE_SETTINGS"]).topic_status(
            repository.list_quizzes(student_id), quiz_history + tutor_interactions
        )
    except Exception as exc:
        current_app.logger.error("Adaptive status failure: %s", exc)
        return jsonify({"error": "adaptive status unavailable"}), 503
    return jsonify({"topics": statuses}), 200