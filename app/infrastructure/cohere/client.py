"""Cohere configuration and client creation."""

from __future__ import annotations

from app.config.settings import Settings


def create_client(settings: Settings):
    if not settings.cohere_api_key:
        raise RuntimeError("COHERE_API_KEY is not configured")
    try:
        import cohere
    except ImportError as exc:
        raise RuntimeError("Cohere support requires the cohere package") from exc
    return cohere.ClientV2(api_key=settings.cohere_api_key)


def check_configuration(settings: Settings) -> None:
    if not settings.cohere_api_key:
        raise RuntimeError("COHERE_API_KEY is not configured")