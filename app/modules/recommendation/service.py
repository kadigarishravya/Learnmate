"""Deterministic recommendations derived from Adaptive Learning and owned data."""

from __future__ import annotations


class RecommendationService:
    def __init__(self, adaptive_service, repository, document_repository=None):
        self.adaptive = adaptive_service
        self.repository = repository
        self.document_repository = document_repository

    def generate(self, student_id: int) -> list:
        quizzes = self.repository.list_quizzes(student_id)
        interactions = self.repository.list_history(student_id)
        if hasattr(self.repository, "list_tutor_interactions"):
            interactions = interactions + [
                type("Interaction", (), {"topic": item.subject, "interaction_date": item.timestamp})()
                for item in self.repository.list_tutor_interactions(student_id)
            ]
        weak_topics = self.adaptive.weak_topics(quizzes, interactions)
        documents = self.document_repository.list_owned(student_id) if self.document_repository else []
        existing = self.repository.list_recommendations(student_id)
        created = []
        for status in weak_topics:
            topic = status["topic"]
            document = next(
                (item for item in documents if item.subject and item.subject.lower() == topic.lower()),
                None,
            )
            material_text = (
                f"Review your uploaded material '{document.title}'. "
                if document else
                "No relevant uploaded material was found for this topic. Upload study material for this topic. "
            )
            text = (
                f"Revise {topic}. {material_text}Then practice additional questions, "
                "request a simpler explanation if needed, and reattempt a quiz after improvement."
            )
            if any(item.topic == topic and item.recommendation_text == text for item in existing + created):
                continue
            created.append(self.repository.create_recommendation(student_id, topic, text))
        return created

    def list(self, student_id):
        return self.repository.list_recommendations(student_id)