"""SQLite connectivity for LearnMate."""

from __future__ import annotations

import logging
from functools import lru_cache

from app.config.settings import Settings

logger = logging.getLogger(__name__)


def create_engine(settings: Settings):
    try:
        from sqlalchemy import create_engine as sqlalchemy_create_engine
    except ImportError as exc:
        raise RuntimeError(
            "SQLite support requires SQLAlchemy. Install requirements.txt."
        ) from exc

    settings.sqlite_database_path.parent.mkdir(parents=True, exist_ok=True)

    return sqlalchemy_create_engine(
        settings.sqlalchemy_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        hide_parameters=True,
    )


def check_connection(settings: Settings) -> None:
    engine = create_engine(settings)
    try:
        from sqlalchemy import text

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("SQLite connectivity check failed: %s", exc)
        raise RuntimeError(f"SQLite connectivity check failed: {exc}") from exc
    finally:
        engine.dispose()


@lru_cache(maxsize=4)
def create_session_factory(settings: Settings):
    """Return a reusable session factory backed by one SQLite engine."""
    engine = create_engine(settings)

    from sqlalchemy.orm import sessionmaker

    return sessionmaker(bind=engine, expire_on_commit=False)