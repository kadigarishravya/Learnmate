"""Authenticated Tavily web search endpoint."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from app.api.routes.auth import _authenticated_student_id
from app.infrastructure.google_web_search.client import TavilyWebSearchClient


web_search_bp = Blueprint("web_search", __name__, url_prefix="/api/web-search")


@web_search_bp.get("")
def web_search():
    if _authenticated_student_id() is None:
        return jsonify({"error": "authentication required"}), 401

    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "search query is required"}), 400

    settings = current_app.config["LEARNMATE_SETTINGS"]
    if not settings.tavily_configured:
        return jsonify(
            {
                "error": "Tavily web search is not configured",
                "required_configuration": ["TAVILY_API_KEY"],
            }
        ), 503

    page_size = request.args.get("page_size", default=5, type=int) or 5
    try:
        results = TavilyWebSearchClient(settings).search(
            query=query,
            page_size=page_size,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        current_app.logger.error("Web search failure: %s", exc)
        return jsonify({"error": str(exc)}), 503

    return jsonify({"query": query, "results": results}), 200
