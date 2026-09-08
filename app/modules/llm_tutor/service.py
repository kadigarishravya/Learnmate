"""Cohere Chat tutor adapter."""

from __future__ import annotations

from app.infrastructure.cohere.client import create_client


class CohereTutor:
    def __init__(self, settings, client=None):
        self.settings = settings
        self.client = client

    @property
    def model_name(self) -> str:
        return self.settings.cohere_chat_model

    def generate(self, messages: list[dict[str, str]]) -> str:
        client = self.client or create_client(self.settings)
        try:
            response = client.chat(
                model=self.settings.cohere_chat_model,
                messages=messages,
            )
            content = response.message.content
            if content and hasattr(content[0], "text"):
                return content[0].text.strip()
            if content and isinstance(content[0], dict):
                return str(content[0].get("text", "")).strip()
        except Exception as exc:
            raise RuntimeError("Cohere Chat request failed") from exc
        raise RuntimeError("Cohere Chat returned no response text")