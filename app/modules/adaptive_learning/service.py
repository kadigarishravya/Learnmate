"""Shared simple-hybrid weak-topic logic for Phase 5."""

from __future__ import annotations


class AdaptiveLearningService:
    def __init__(self, settings):
        self.min_quiz_attempts = settings.adaptive_min_quiz_attempts
        self.min_interactions = settings.adaptive_min_interactions
        self.weak_score_threshold = settings.adaptive_weak_score_threshold

    def topic_status(self, quizzes, interactions) -> list[dict]:
        topics = {item.topic for item in quizzes} | {item.topic for item in interactions if item.topic}
        statuses = []
        for topic in sorted(topics):
            topic_quizzes = [item for item in quizzes if item.topic == topic and item.score is not None]
            topic_interactions = [item for item in interactions if item.topic == topic]
            average = (
                sum(item.score for item in topic_quizzes) / len(topic_quizzes)
                if topic_quizzes else None
            )
            eligible = len(topic_quizzes) >= self.min_quiz_attempts or len(topic_interactions) >= self.min_interactions
            weak_by_score = average is not None and len(topic_quizzes) >= self.min_quiz_attempts and average < self.weak_score_threshold
            weak_by_interaction = (
                average is None
                and len(topic_interactions) >= self.min_interactions
                and self._repeated_recent_difficulty(topic_interactions)
            )
            statuses.append({
                "topic": topic,
                "eligible": eligible,
                "weak": weak_by_score or weak_by_interaction,
                "average_score": average,
                "quiz_attempts": len(topic_quizzes),
                "interactions": len(topic_interactions),
                "adaptive_actions": [
                    "revise this topic",
                    "practice additional questions",
                    "request a simpler explanation",
                ] if weak_by_score or weak_by_interaction else [],
            })
        return statuses

    @staticmethod
    def _repeated_recent_difficulty(interactions) -> bool:
        return len(interactions) >= 5 and len({item.interaction_date.date() for item in interactions}) >= 1

    def weak_topics(self, quizzes, interactions) -> list[dict]:
        return [status for status in self.topic_status(quizzes, interactions) if status["weak"]]