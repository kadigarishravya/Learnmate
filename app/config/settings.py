"""Centralized environment-backed configuration for LearnMate."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    flask_host: str
    flask_port: int
    flask_debug: bool
    sqlite_database_path: Path
    cohere_api_key: str | None
    cohere_rerank_model: str
    cohere_chat_model: str
    google_web_search_api_key: str | None
    google_web_search_client_id: str | None
    uploads_path: Path
    supported_document_extensions: tuple[str, ...]
    max_upload_size_bytes: int
    chroma_path: Path
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    retrieval_top_k: int
    rerank_top_n: int
    similarity_threshold: float | None
    rerank_threshold: float | None
    context_token_limit: int
    session_inactivity_timeout_seconds: int
    quiz_question_count: int
    quiz_state_timeout_seconds: int
    adaptive_min_quiz_attempts: int
    adaptive_min_interactions: int
    adaptive_weak_score_threshold: float
    feedback_comments_max_length: int

    @property
    def cohere_configured(self) -> bool:
        return bool(self.cohere_api_key)

    @property
    def google_web_search_configured(self) -> bool:
        return bool(self.google_web_search_api_key and self.google_web_search_client_id)

    @property
    def sqlalchemy_url(self) -> str:
        return f"sqlite:///{self.sqlite_database_path}"


def get_settings() -> Settings:
    return Settings(
        flask_host=os.getenv("FLASK_HOST", "127.0.0.1"),
        flask_port=int(os.getenv("FLASK_PORT", "5000")),
        flask_debug=_env_bool("FLASK_DEBUG", False),
        sqlite_database_path=Path(
            os.getenv("SQLITE_DATABASE_PATH", str(PROJECT_ROOT / "storage" / "learnmate.db"))
        ),
        cohere_api_key=os.getenv("COHERE_API_KEY") or None,
        cohere_rerank_model=os.getenv("COHERE_RERANK_MODEL", "rerank-v3.5"),
        cohere_chat_model=os.getenv("COHERE_CHAT_MODEL", "command-a-03-2025"),
        google_web_search_api_key=os.getenv("GOOGLE_WEB_SEARCH_API_KEY") or None,
        google_web_search_client_id=os.getenv("GOOGLE_WEB_SEARCH_CLIENT_ID") or None,
        uploads_path=Path(os.getenv("UPLOADS_PATH", str(PROJECT_ROOT / "storage" / "uploads"))),
        supported_document_extensions=tuple(
            extension.strip().lower()
            for extension in os.getenv("SUPPORTED_DOCUMENT_EXTENSIONS", ".pdf").split(",")
            if extension.strip()
        ),
        max_upload_size_bytes=int(os.getenv("MAX_UPLOAD_SIZE_BYTES", "10485760")),
        chroma_path=Path(os.getenv("CHROMA_PATH", str(PROJECT_ROOT / "storage" / "chroma"))),
        embedding_model=os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ),
        chunk_size=int(os.getenv("CHUNK_SIZE", "512")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "80")),
        retrieval_top_k=int(os.getenv("RETRIEVAL_TOP_K", "8")),
        rerank_top_n=int(os.getenv("RERANK_TOP_N", "4")),
        similarity_threshold=(
            float(os.environ["SIMILARITY_THRESHOLD"])
            if os.getenv("SIMILARITY_THRESHOLD")
            else None
        ),
        rerank_threshold=(
            float(os.environ["RERANK_THRESHOLD"])
            if os.getenv("RERANK_THRESHOLD")
            else None
        ),
        context_token_limit=int(os.getenv("CONTEXT_TOKEN_LIMIT", "6000")),
        session_inactivity_timeout_seconds=int(
            os.getenv("SESSION_INACTIVITY_TIMEOUT_SECONDS", "1800")
        ),
        quiz_question_count=int(os.getenv("QUIZ_QUESTION_COUNT", "5")),
        quiz_state_timeout_seconds=int(os.getenv("QUIZ_STATE_TIMEOUT_SECONDS", "1800")),
        adaptive_min_quiz_attempts=int(os.getenv("ADAPTIVE_MIN_QUIZ_ATTEMPTS", "2")),
        adaptive_min_interactions=int(os.getenv("ADAPTIVE_MIN_INTERACTIONS", "5")),
        adaptive_weak_score_threshold=float(os.getenv("ADAPTIVE_WEAK_SCORE_THRESHOLD", "60")),
        feedback_comments_max_length=int(os.getenv("FEEDBACK_COMMENTS_MAX_LENGTH", "2000")),
    )
