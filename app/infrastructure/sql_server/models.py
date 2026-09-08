"""SQLAlchemy models for the nine documented LearnMate entities."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "Student"
    __table_args__ = (UniqueConstraint("email", name="UQ_Student_email"),)

    student_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Document(Base):
    __tablename__ = "Document"

    document_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("Student.student_id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    upload_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class DocumentChunk(Base):
    __tablename__ = "Document_Chunk"

    chunk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("Document.document_id"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[str] = mapped_column("metadata", Text, nullable=False)


class Query(Base):
    __tablename__ = "Query"

    query_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("Student.student_id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Response(Base):
    __tablename__ = "Response"

    response_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_id: Mapped[int] = mapped_column(ForeignKey("Query.query_id"), nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Quiz(Base):
    __tablename__ = "Quiz"

    quiz_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("Student.student_id"), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)


class LearningHistory(Base):
    __tablename__ = "Learning_History"

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("Student.student_id"), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    interaction_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Recommendation(Base):
    __tablename__ = "Recommendation"

    recommendation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("Student.student_id"), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)


class Feedback(Base):
    __tablename__ = "Feedback"

    feedback_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("Student.student_id"), nullable=False)
    query_id: Mapped[int] = mapped_column(ForeignKey("Query.query_id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)