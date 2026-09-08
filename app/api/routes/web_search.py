"""Authenticated Google web search endpoint."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.api.routes.auth import _authenticated_student_id
from app.infrastructure.google_web_search.client import GoogleWebSearchClient


web_search_bp = Blueprint("web_search", __name__, url_prefix="/api/web-search")


@web_search_bp.get("")
def web_search():
    if _authenticated_student_id() is None:
        return jsonify({"error": "authentication required"}), 401

    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "search query is required"}), 400

    settings = current_app.config["LEARNMATE_SETTINGS"]
    if not settings.google_web_search_configured:
        return jsonify(
            {
                "error": "Google web search is not configured",
                "required_configuration": [
                    "GOOGLE_WEB_SEARCH_API_KEY",
                    "GOOGLE_WEB_SEARCH_CLIENT_ID",
                ],
            }
        ), 503

    try:
        results = GoogleWebSearchClient(settings).search(
            query=query,
            user_ip=request.remote_addr or "127.0.0.1",
            page_size=request.args.get("page_size", default=5, type=int),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        current_app.logger.error("Web search failure: %s", exc)
        return jsonify({"error": str(exc)}), 503

    return jsonify({"query": query, "results": results}), 200
