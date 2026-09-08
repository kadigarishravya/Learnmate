"""Explicit command for creating the nine documented SQL Server tables."""

from app.infrastructure.sql_server.schema import initialize_schema


if __name__ == "__main__":
    initialize_schema()