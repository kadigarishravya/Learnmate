"""Hybrid deterministic and Cohere-backed query understanding."""

from __future__ import annotations

import re

from app.infrastructure.cohere.client import create_client
from app.modules.query_understanding.models import QueryUnderstanding


class QueryUnderstandingService:
    SUBJECTS = {
        "physics": "Physics",
        "biology": "Biology",
        "chemistry": "Chemistry",
        "mathematics": "Mathematics",
        "math": "Mathematics",
        "history": "History",
        "computer science": "Computer Science",
        "programming": "Computer Science",
    }

    def __init__(self, settings, cohere_client=None):
        self.settings = settings
        self.cohere_client = cohere_client

    def analyze(self, question: str, conversation: list[dict[str, str]]) -> QueryUnderstanding:
        lowered = question.lower().strip()
        intent = None
        response_type = None
        if re.search(r"\b(what is|define|definition of)\b", lowered):
            intent, response_type = "definition", "concise definition"
        elif re.search(r"\b(explain|how does|why does|why is)\b", lowered):
            intent, response_type = "explanation", "explanation"
        elif re.search(r"\b(example|for instance)\b", lowered):
            intent, response_type = "example", "examples"
        elif re.search(r"\b(summarize|summary|main points)\b", lowered):
            intent, response_type = "summary", "summary"
        elif re.search(r"\b(solve|calculate|work out|step[- ]by[- ]step)\b", lowered):
            intent, response_type = "solution", "step-by-step solution"

        subject = next(
            value for key, value in self.SUBJECTS.items() if re.search(rf"\b{re.escape(key)}\b", lowered)
        ) if any(re.search(rf"\b{re.escape(key)}\b", lowered) for key in self.SUBJECTS) else None
        topic = self._topic(lowered, intent)
        difficulty = None
        if re.search(r"\b(simple|simply|beginner|easy)\b", lowered):
            difficulty = "beginner"
        elif re.search(r"\b(advanced|technical|detailed)\b", lowered):
            difficulty = "advanced"

        context = None
        if conversation and not topic and re.search(r"\b(it|this|that|they|them|its)\b", lowered):
            context = conversation[-1]["question"]

        result = QueryUnderstanding(
            intent=intent,
            subject=subject,
            topic=topic,
            context=context,
            expected_response_type=response_type,
            difficulty=difficulty,
            confidence={"intent": "high" if intent else "unknown"},
        )
        if any(value is not None for value in (intent, subject, topic, difficulty)):
            return result
        return self._ambiguous_fallback(question, conversation, result)

    @staticmethod
    def _topic(lowered: str, intent: str | None) -> str | None:
        patterns = [r"(?:what is|define|definition of|explain)\s+(.+?)(?:\s+in simple|\s+with an example|\?|$)"]
        if intent:
            for pattern in patterns:
                match = re.search(pattern, lowered)
                if match:
                    value = match.group(1).strip(" .?")
                    if value and value.split()[0] not in {"it", "this", "that", "they", "them", "its"}:
                        return value
        match = re.search(r"\b(?:about|on|regarding)\s+([a-z][a-z0-9 -]{2,60})", lowered)
        return match.group(1).strip(" .?") if match else None

    def _ambiguous_fallback(self, question, conversation, current):
        if not self.settings.cohere_api_key:
            return current
        client = self.cohere_client or create_client(self.settings)
        try:
            response = client.chat(
                model=self.settings.cohere_chat_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Return only JSON fields intent, subject, topic, context, expected_response_type, difficulty. Use null when unknown.",
                    },
                    {"role": "user", "content": question},
                ],
            )
            text = response.message.content[0].text
        except Exception as exc:
            raise RuntimeError("Cohere query-understanding request failed") from exc
        import json

        values = json.loads(text)
        return QueryUnderstanding(
            intent=values.get("intent"),
            subject=values.get("subject"),
            topic=values.get("topic"),
            context=values.get("context"),
            expected_response_type=values.get("expected_response_type"),
            difficulty=values.get("difficulty"),
            confidence={"source": "cohere"},
        )