"""Feedback validation and ownership service."""

from __future__ import annotations


FEEDBACK_CATEGORIES = {
    1: "Helpful",
    2: "Not helpful",
    3: "Incorrect",
    4: "Too difficult",
    5: "Too simple",
}


class FeedbackService:
    def __init__(self, repository, max_comment_length: int = 2000):
        self.repository = repository
        self.max_comment_length = max_comment_length

    def create(self, student_id, query_id, rating, comments=None):
        if not isinstance(query_id, int) or query_id <= 0:
            raise ValueError("valid query_id is required")
        if rating not in FEEDBACK_CATEGORIES:
            raise ValueError("rating must be between 1 and 5")
        if comments is not None and (not isinstance(comments, str) or len(comments) > self.max_comment_length):
            raise ValueError("comments exceed the configured maximum length")
        if self.repository.get_owned_query(student_id, query_id) is None:
            raise LookupError("query not found")
        return self.repository.create_feedback(student_id, query_id, rating, comments.strip() if comments else None)

    def list(self, student_id):
        return self.repository.list_feedback(student_id)