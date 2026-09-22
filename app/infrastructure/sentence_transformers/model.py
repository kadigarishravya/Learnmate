"""Configuration and lazy loading for the approved embedding model."""

from __future__ import annotations

from functools import lru_cache

from app.config.settings import Settings


def load_embedding_model(settings: Settings):
    return _load_embedding_model(settings.embedding_model)


@lru_cache(maxsize=2)
def _load_embedding_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Sentence Transformers is not installed. Install requirements.txt first."
        ) from exc
    return SentenceTransformer(model_name)


def check_configuration(settings: Settings) -> str:
    if not settings.embedding_model:
        raise RuntimeError("EMBEDDING_MODEL is not configured")
    return settings.embedding_model
