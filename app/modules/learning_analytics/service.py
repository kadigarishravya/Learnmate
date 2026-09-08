"""Runtime analytics computed from documented LearnMate entities."""

from __future__ import annotations


FEEDBACK_CATEGORIES = {
    1: "Helpful",
    2: "Not helpful",
    3: "Incorrect",
    4: "Too difficult",
    5: "Too simple",
}


class LearningAnalyticsService:
    def __init__(self, adaptive_service):
        self.adaptive = adaptive_service

    def summarize(self, quizzes, histories, queries, recommendations, feedback):
        scores = [item.score for item in quizzes if item.score is not None]
        interactions = [item for item in histories if item.topic]
        statuses = self.adaptive.topic_status(quizzes, interactions)
        topic_performance = []
        topics = sorted({item.topic for item in quizzes} | {item.topic for item in histories})
        for topic in topics:
            topic_scores = [item.score for item in quizzes if item.topic == topic and item.score is not None]
            topic_history = [item for item in histories if item.topic == topic]
            topic_performance.append({
                "topic": topic,
                "quiz_attempts": len(topic_scores),
                "average_score": sum(topic_scores) / len(topic_scores) if topic_scores else None,
                "best_score": max(topic_scores) if topic_scores else None,
                "recent_score": topic_scores[-1] if topic_scores else None,
                "learning_history_activity": len(topic_history),
            })
        feedback_counts = {label: 0 for label in FEEDBACK_CATEGORIES.values()}
        for item in feedback:
            if item.rating in FEEDBACK_CATEGORIES:
                feedback_counts[FEEDBACK_CATEGORIES[item.rating]] += 1
        return {
            "total_evaluated_quizzes": len(scores),
            "average_quiz_score": sum(scores) / len(scores) if scores else None,
            "highest_quiz_score": max(scores) if scores else None,
            "learning_interaction_count": len(queries),
            "topics_studied": sorted({item.topic for item in histories if item.topic}),
            "topic_performance": topic_performance,
            "weak_topics": [item for item in statuses if item["weak"]],
            "recent_learning_activity": [
                {"topic": item.topic, "interaction_date": item.interaction_date.isoformat()}
                for item in sorted(histories, key=lambda value: value.interaction_date, reverse=True)[:10]
            ],
            "recommendation_count": len(recommendations),
            "feedback_category_counts": feedback_counts,
        }