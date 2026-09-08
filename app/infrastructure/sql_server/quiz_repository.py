"""SQL Server persistence for Quiz and Learning_History."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select

from app.infrastructure.sql_server.models import (
    Feedback,
    LearningHistory,
    Query,
    Quiz,
    Recommendation,
    Response,
)


class QuizRepository:
    def __init__(self, session_factory: Callable):
        self._session_factory = session_factory

    def create_quiz(self, student_id, topic, difficulty, score):
        with self._session_factory() as session:
            quiz = Quiz(student_id=student_id, topic=topic, difficulty=difficulty, score=score)
            session.add(quiz)
            session.commit()
            session.refresh(quiz)
            return quiz

    def create_history(self, student_id, topic, score, interaction_date):
        with self._session_factory() as session:
            history = LearningHistory(
                student_id=student_id,
                topic=topic,
                score=score,
                interaction_date=interaction_date,
            )
            session.add(history)
            session.commit()
            session.refresh(history)
            return history

    def list_quizzes(self, student_id, topic=None):
        with self._session_factory() as session:
            statement = select(Quiz).where(Quiz.student_id == student_id)
            if topic:
                statement = statement.where(Quiz.topic == topic)
            return list(session.scalars(statement.order_by(Quiz.quiz_id)))

    def list_history(self, student_id, topic=None):
        with self._session_factory() as session:
            statement = select(LearningHistory).where(LearningHistory.student_id == student_id)
            if topic:
                statement = statement.where(LearningHistory.topic == topic)
            return list(session.scalars(statement.order_by(LearningHistory.interaction_date)))

    def list_tutor_interactions(self, student_id, topic=None):
        with self._session_factory() as session:
            statement = select(Query).where(
                Query.student_id == student_id,
                Query.subject.is_not(None),
            )
            if topic:
                statement = statement.where(Query.subject == topic)
            return list(session.scalars(statement.order_by(Query.timestamp)))

    def list_recommendations(self, student_id):
        with self._session_factory() as session:
            return list(session.scalars(
                select(Recommendation).where(Recommendation.student_id == student_id)
            ))

    def create_recommendation(self, student_id, topic, recommendation_text):
        with self._session_factory() as session:
            recommendation = Recommendation(
                student_id=student_id, topic=topic, recommendation_text=recommendation_text
            )
            session.add(recommendation)
            session.commit()
            session.refresh(recommendation)
            return recommendation

    def list_feedback(self, student_id):
        with self._session_factory() as session:
            return list(session.scalars(select(Feedback).where(Feedback.student_id == student_id)))

    def create_feedback(self, student_id, query_id, rating, comments):
        with self._session_factory() as session:
            feedback = Feedback(
                student_id=student_id, query_id=query_id, rating=rating, comments=comments
            )
            session.add(feedback)
            session.commit()
            session.refresh(feedback)
            return feedback

    def get_owned_query(self, student_id, query_id):
        with self._session_factory() as session:
            return session.scalar(select(Query).where(
                Query.student_id == student_id, Query.query_id == query_id
            ))

    def list_queries(self, student_id):
        with self._session_factory() as session:
            return list(session.scalars(select(Query).where(Query.student_id == student_id)))

    def list_responses(self, student_id):
        with self._session_factory() as session:
            statement = select(Response).join(Query, Response.query_id == Query.query_id).where(
                Query.student_id == student_id
            )
            return list(session.scalars(statement))