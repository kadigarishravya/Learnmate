"""Recommendation, analytics, and feedback endpoints."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.api.routes.auth import _authenticated_student_id
from app.infrastructure.sql_server.connection import create_session_factory
from app.infrastructure.sql_server.quiz_repository import QuizRepository
from app.modules.adaptive_learning.service import AdaptiveLearningService
from app.modules.educational_content_management.repository import DocumentRepository
from app.modules.feedback.service import FeedbackService
from app.modules.learning_analytics.service import LearningAnalyticsService
from app.modules.recommendation.service import RecommendationService


phase6_bp = Blueprint("phase6", __name__, url_prefix="/api")


def _repository():
    repository = current_app.config.get("LEARNMATE_PHASE6_REPOSITORY")
    if repository is not None:
        return repository
    settings = current_app.config["LEARNMATE_SETTINGS"]
    return QuizRepository(create_session_factory(settings))


def _services():
    settings = current_app.config["LEARNMATE_SETTINGS"]
    repository = _repository()
    adaptive = AdaptiveLearningService(settings)
    recommendation = current_app.config.get("LEARNMATE_RECOMMENDATION_SERVICE")
    if recommendation is None:
        document_repository = DocumentRepository(create_session_factory(settings))
        recommendation = RecommendationService(adaptive, repository, document_repository)
    analytics = current_app.config.get("LEARNMATE_ANALYTICS_SERVICE") or LearningAnalyticsService(adaptive)
    feedback = current_app.config.get("LEARNMATE_FEEDBACK_SERVICE") or FeedbackService(
        repository, settings.feedback_comments_max_length
    )
    return repository, recommendation, analytics, feedback


def _require_student():
    student_id = _authenticated_student_id()
    if student_id is None:
        return None, (jsonify({"error": "authentication required"}), 401)
    return student_id, None


def _recommendation(item):
    return {
        "recommendation_id": item.recommendation_id,
        "topic": item.topic,
        "recommendation_text": item.recommendation_text,
    }


@phase6_bp.get("/recommendations")
def list_recommendations():
    student_id, error = _require_student()
    if error:
        return error
    try:
        _, service, _, _ = _services()
        return jsonify({"recommendations": [_recommendation(item) for item in service.list(student_id)]})
    except Exception as exc:
        current_app.logger.error("Recommendation listing failure: %s", exc)
        return jsonify({"error": "recommendations unavailable"}), 503


@phase6_bp.post("/recommendations/generate")
def generate_recommendations():
    student_id, error = _require_student()
    if error:
        return error
    try:
        _, service, _, _ = _services()
        created = service.generate(student_id)
        return jsonify({"recommendations": [_recommendation(item) for item in created]}), 201
    except Exception as exc:
        current_app.logger.error("Recommendation generation failure: %s", exc)
        return jsonify({"error": "recommendation generation failed"}), 503


@phase6_bp.get("/recommendations/adaptive")
def adaptive_recommendations():
    student_id, error = _require_student()
    if error:
        return error
    try:
        repository, _, _, _ = _services()
        settings = current_app.config["LEARNMATE_SETTINGS"]
        adaptive = AdaptiveLearningService(settings)
        histories = repository.list_history(student_id)
        if hasattr(repository, "list_tutor_interactions"):
            histories += [
                type("Interaction", (), {"topic": item.subject, "interaction_date": item.timestamp})()
                for item in repository.list_tutor_interactions(student_id)
            ]
        return jsonify({"topics": adaptive.topic_status(repository.list_quizzes(student_id), histories)})
    except Exception as exc:
        current_app.logger.error("Adaptive recommendation status failure: %s", exc)
        return jsonify({"error": "adaptive status unavailable"}), 503


@phase6_bp.get("/analytics")
def analytics():
    student_id, error = _require_student()
    if error:
        return error
    try:
        repository, _, service, _ = _services()
        return jsonify({"analytics": service.summarize(
            repository.list_quizzes(student_id),
            repository.list_history(student_id),
            repository.list_queries(student_id),
            repository.list_recommendations(student_id),
            repository.list_feedback(student_id),
        )})
    except Exception as exc:
        current_app.logger.error("Analytics failure: %s", exc)
        return jsonify({"error": "analytics unavailable"}), 503


@phase6_bp.post("/feedback")
def create_feedback():
    student_id, error = _require_student()
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    try:
        _, _, _, service = _services()
        feedback = service.create(student_id, payload.get("query_id"), payload.get("rating"), payload.get("comments"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        current_app.logger.error("Feedback creation failure: %s", exc)
        return jsonify({"error": "feedback unavailable"}), 503
    return jsonify({"feedback_id": feedback.feedback_id, "rating": feedback.rating}), 201


@phase6_bp.get("/feedback/queries")
def feedback_queries():
    student_id, error = _require_student()
    if error:
        return error
    try:
        repository, _, _, _ = _services()
        responses = {item.query_id: item for item in repository.list_responses(student_id)}
        return jsonify({"queries": [
            {"query_id": item.query_id, "question": item.question,
             "response": responses.get(item.query_id).response_text if responses.get(item.query_id) else None}
            for item in repository.list_queries(student_id)
        ]})
    except Exception as exc:
        current_app.logger.error("Feedback query listing failure: %s", exc)
        return jsonify({"error": "query history unavailable"}), 503


@phase6_bp.get("/feedback")
def list_feedback():
    student_id, error = _require_student()
    if error:
        return error
    try:
        _, _, _, service = _services()
        return jsonify({"feedback": [
            {"feedback_id": item.feedback_id, "query_id": item.query_id, "rating": item.rating, "comments": item.comments}
            for item in service.list(student_id)
        ]})
    except Exception as exc:
        current_app.logger.error("Feedback listing failure: %s", exc)
        return jsonify({"error": "feedback unavailable"}), 503