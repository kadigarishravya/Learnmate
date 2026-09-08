"""Student persistence operations backed by SQL Server."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select

from app.infrastructure.sql_server.models import Student


class StudentRepository:
    def __init__(self, session_factory: Callable):
        self._session_factory = session_factory

    def find_by_email(self, email: str) -> Student | None:
        with self._session_factory() as session:
            return session.scalar(select(Student).where(Student.email == email))

    def get(self, student_id: int) -> Student | None:
        with self._session_factory() as session:
            return session.get(Student, student_id)

    def create(self, name: str, email: str, password_hash: str, registration_date) -> Student:
        with self._session_factory() as session:
            student = Student(
                name=name,
                email=email,
                password=password_hash,
                registration_date=registration_date,
            )
            session.add(student)
            session.commit()
            session.refresh(student)
            return student

    def update_profile(self, student_id: int, name: str, email: str) -> Student | None:
        with self._session_factory() as session:
            student = session.get(Student, student_id)
            if student is None:
                return None
            student.name = name
            student.email = email
            session.commit()
            session.refresh(student)
            return student