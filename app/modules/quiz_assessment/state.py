"""Transient server-side quiz state; never persisted in SQL Server."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass


@dataclass
class QuizState:
    quiz_id: int
    student_id: int
    session_id: str
    topic: str
    difficulty: str
    questions: list[dict]
    created_at: float
    evaluated: bool = False


class QuizStateStore:
    def __init__(self, timeout_seconds: int):
        self.timeout_seconds = timeout_seconds
        self._states: dict[int, QuizState] = {}

    def create(self, student_id, session_id, topic, difficulty, questions) -> QuizState:
        quiz_id = secrets.randbits(63)
        while quiz_id in self._states:
            quiz_id = secrets.randbits(63)
        state = QuizState(quiz_id, student_id, session_id, topic, difficulty, questions, time.monotonic())
        self._states[quiz_id] = state
        return state

    def get_owned(self, quiz_id: int, student_id: int, session_id: str) -> QuizState | None:
        state = self._states.get(quiz_id)
        if state is None:
            return None
        if time.monotonic() - state.created_at >= self.timeout_seconds:
            self._states.pop(quiz_id, None)
            return None
        if state.student_id != student_id or state.session_id != session_id:
            return None
        return state

    def remove(self, quiz_id: int) -> None:
        self._states.pop(quiz_id, None)

    def cleanup_expired(self) -> None:
        now = time.monotonic()
        for quiz_id, state in list(self._states.items()):
            if now - state.created_at >= self.timeout_seconds:
                self._states.pop(quiz_id, None)