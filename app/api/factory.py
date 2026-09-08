"""Flask application factory for the LearnMate API."""

from __future__ import annotations

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from app.api.routes.auth import auth_bp
from app.api.routes.documents import documents_bp
from app.api.routes.phase6 import phase6_bp
from app.api.routes.quizzes import quizzes_bp
from app.api.routes.tutor import tutor_bp
from app.api.routes.web_search import web_search_bp
from app.common.logging_config import configure_logging
from app.config.settings import Settings, get_settings
from app.modules.student_management.sessions import SessionManager


def create_app(settings: Settings | None = None) -> Flask:
    configure_logging()
    app = Flask(__name__)
    active_settings = settings or get_settings()
    app.config["LEARNMATE_SETTINGS"] = active_settings
    app.config["LEARNMATE_SESSION_MANAGER"] = SessionManager(
        active_settings.session_inactivity_timeout_seconds
    )
    app.register_blueprint(auth_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(tutor_bp)
    app.register_blueprint(quizzes_bp)
    app.register_blueprint(phase6_bp)
    app.register_blueprint(web_search_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "learnmate-api"})

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        if isinstance(error, HTTPException):
            return error
        app.logger.exception("Unhandled API error")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

    return app
