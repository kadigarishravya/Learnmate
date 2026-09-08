"""Explicit SQL Server schema initialization for the nine documented tables."""

from __future__ import annotations

import logging

from app.config.settings import Settings, get_settings
from app.infrastructure.sql_server.connection import create_engine
from app.infrastructure.sql_server.models import Base

logger = logging.getLogger(__name__)


def initialize_schema(settings: Settings | None = None) -> None:
    """Create the documented tables; this function is never called on import."""
    active_settings = settings or get_settings()
    engine = create_engine(active_settings)
    try:
        Base.metadata.create_all(engine)
        logger.info("LearnMate SQL Server schema initialized")
    finally:
        engine.dispose()


def documented_table_names() -> tuple[str, ...]:
    return tuple(table.name for table in Base.metadata.sorted_tables)