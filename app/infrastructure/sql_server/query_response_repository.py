"""SQL Server persistence for the documented Query and Response entities."""

from __future__ import annotations

from collections.abc import Callable

from app.infrastructure.sql_server.models import Query, Response


class QueryResponseRepository:
    def __init__(self, session_factory: Callable):
        self._session_factory = session_factory

    def create_query(self, student_id: int, question: str, subject: str | None, timestamp) -> Query:
        with self._session_factory() as session:
            query = Query(student_id=student_id, question=question, subject=subject, timestamp=timestamp)
            session.add(query)
            session.commit()
            session.refresh(query)
            return query

    def create_response(self, query_id: int, response_text: str, model_name: str, timestamp) -> Response:
        with self._session_factory() as session:
            response = Response(
                query_id=query_id,
                response_text=response_text,
                model_name=model_name,
                timestamp=timestamp,
            )
            session.add(response)
            session.commit()
            session.refresh(response)
            return response