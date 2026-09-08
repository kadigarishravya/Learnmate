"""Runtime-only Q3 query-understanding model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QueryUnderstanding:
    intent: str | None = None
    subject: str | None = None
    topic: str | None = None
    context: str | None = None
    expected_response_type: str | None = None
    difficulty: str | None = None
    confidence: dict[str, str] | None = None

    def as_prompt_text(self) -> str:
        values = {
            "intent": self.intent,
            "subject": self.subject,
            "topic": self.topic,
            "context": self.context,
            "expected_response_type": self.expected_response_type,
            "difficulty": self.difficulty,
        }
        return "\n".join(f"{key}: {value or 'unknown'}" for key, value in values.items())