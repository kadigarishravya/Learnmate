"""Student authentication endpoints."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.infrastructure.sql_server.connection import create_session_factory
from app.modules.student_management.auth import (
    AuthService,
    DuplicateEmailError,
    InvalidCredentialsError,
    ValidationError,
)
from app.modules.student_management.repository import StudentRepository
from app.modules.student_management.sessions import SessionManager


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
SESSION_HEADER = "X-Session-ID"


def _session_manager() -> SessionManager:
    return current_app.config["LEARNMATE_SESSION_MANAGER"]


def _student_repository() -> StudentRepository:
    repository = current_app.config.get("LEARNMATE_STUDENT_REPOSITORY")
    if repository is not None:
        return repository
    settings = current_app.config["LEARNMATE_SETTINGS"]
    return StudentRepository(create_session_factory(settings))


def _auth_service() -> AuthService:
    return AuthService(_student_repository())


def _profile(student) -> dict[str, object]:
    return {
        "student_id": student.student_id,
        "name": student.name,
        "email": student.email,
        "registration_date": student.registration_date.isoformat(),
    }


def _authenticated_student_id() -> int | None:
    return _session_manager().get_student_id(request.headers.get(SESSION_HEADER))


@auth_bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    try:
        student = _auth_service().register(
            payload.get("name"), payload.get("email"), payload.get("password")
        )
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except DuplicateEmailError as exc:
        return jsonify({"error": str(exc)}), 409
    except (RuntimeError, OSError) as exc:
        current_app.logger.error("Student registration database failure: %s", exc)
        return jsonify({"error": "database unavailable"}), 503
    return jsonify({"student": _profile(student)}), 201


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    try:
        student = _auth_service().authenticate(payload.get("email"), payload.get("password"))
    except InvalidCredentialsError:
        return jsonify({"error": "invalid credentials"}), 401
    except (RuntimeError, OSError) as exc:
        current_app.logger.error("Student login database failure: %s", exc)
        return jsonify({"error": "database unavailable"}), 503
    token = _session_manager().create(student.student_id)
    return jsonify({"student": _profile(student), "session_id": token}), 200


@auth_bp.post("/logout")
def logout():
    _session_manager().invalidate(request.headers.get(SESSION_HEADER))
    return jsonify({"status": "logged_out"}), 200


@auth_bp.get("/me")
def get_me():
    student_id = _authenticated_student_id()
    if student_id is None:
        return jsonify({"error": "authentication required"}), 401
    try:
        student = _auth_service().get_profile(student_id)
    except (RuntimeError, OSError) as exc:
        current_app.logger.error("Student profile database failure: %s", exc)
        return jsonify({"error": "database unavailable"}), 503
    if student is None:
        return jsonify({"error": "authentication required"}), 401
    return jsonify({"student": _profile(student)}), 200


@auth_bp.put("/me")
def update_me():
    student_id = _authenticated_student_id()
    if student_id is None:
        return jsonify({"error": "authentication required"}), 401
    payload = request.get_json(silent=True) or {}
    try:
        student = _auth_service().update_profile(
            student_id, payload.get("name"), payload.get("email")
        )
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except DuplicateEmailError as exc:
        return jsonify({"error": str(exc)}), 409
    except (RuntimeError, OSError) as exc:
        current_app.logger.error("Student profile update database failure: %s", exc)
        return jsonify({"error": "database unavailable"}), 503
    if student is None:
        return jsonify({"error": "authentication required"}), 401
    return jsonify({"student": _profile(student)}), 200