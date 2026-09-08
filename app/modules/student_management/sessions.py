"""In-memory Flask server-session state for authenticated students."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass


@dataclass
class SessionRecord:
    student_id: int
    last_activity: float
    turns: list[dict[str, str]]


class SessionManager:
    def __init__(self, inactivity_timeout_seconds: int):
        self._timeout = inactivity_timeout_seconds
        self._sessions: dict[str, SessionRecord] = {}

    def create(self, student_id: int) -> str:
        token = secrets.token_urlsafe(32)
        self._sessions[token] = SessionRecord(student_id, time.monotonic(), [])
        return token

    def get_student_id(self, token: str | None) -> int | None:
        if not token:
            return None
        record = self._sessions.get(token)
        if record is None:
            return None
        now = time.monotonic()
        if now - record.last_activity >= self._timeout:
            self._sessions.pop(token, None)
            return None
        record.last_activity = now
        return record.student_id

    def invalidate(self, token: str | None) -> None:
        if token:
            self._sessions.pop(token, None)

    def get_context(self, token: str | None) -> list[dict[str, str]]:
        if self.get_student_id(token) is None:
            return []
        return list(self._sessions[token].turns)

    def add_turn(self, token: str | None, question: str, response: str) -> None:
        if self.get_student_id(token) is None:
            return
        turns = self._sessions[token].turns
        turns.append({"question": question, "response": response})
        del turns[:-6]

    def clear_context(self, token: str | None) -> None:
        if token in self._sessions:
            self._sessions[token].turns.clear()