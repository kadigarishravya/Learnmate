"""Quiz generation, evaluation, and transient-state orchestration."""

from __future__ import annotations

from datetime import datetime, timezone

from app.modules.adaptive_learning.service import AdaptiveLearningService

VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced"}


class QuizService:
    def __init__(self, settings, state_store, repository, context_provider=None, generator=None, adaptive=None):
        self.settings = settings
        self.state_store = state_store
        self.repository = repository
        self.context_provider = context_provider
        self.generator = generator
        self.adaptive = adaptive or AdaptiveLearningService(settings)

    def create(self, student_id, session_id, topic, difficulty):
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("topic is required")
        if difficulty not in VALID_DIFFICULTIES:
            raise ValueError("invalid difficulty")
        context = self.context_provider(student_id, topic) if self.context_provider else ""
        if not context:
            raise LookupError("uploaded materials do not contain enough information for this topic")
        if self.generator is None:
            raise RuntimeError("Cohere Chat quiz generation is not configured")
        questions = self.generator(context, topic.strip(), difficulty, self.settings.quiz_question_count)
        self._validate_questions(questions)
        state = self.state_store.create(student_id, session_id, topic.strip(), difficulty, questions)
        return state

    def get(self, student_id, session_id, quiz_id):
        return self.state_store.get_owned(quiz_id, student_id, session_id)

    def submit(self, student_id, session_id, quiz_id, answers):
        state = self.get(student_id, session_id, quiz_id)
        if state is None:
            raise LookupError("quiz not found or expired")
        if state.evaluated:
            raise ValueError("quiz has already been submitted")
        if not isinstance(answers, list) or len(answers) != len(state.questions):
            raise ValueError("answers must contain one answer for each question")
        correct = sum(
            answer == question["correct_answer"]
            for answer, question in zip(answers, state.questions)
        )
        score = round(correct * 100 / len(state.questions), 2)
        quiz = self.repository.create_quiz(student_id, state.topic, state.difficulty, score)
        history = self.repository.create_history(
            student_id, state.topic, score, datetime.now(timezone.utc).replace(tzinfo=None)
        )
        state.evaluated = True
        self.state_store.remove(quiz_id)
        return quiz, history, score

    @staticmethod
    def public_questions(state):
        return [
            {key: value for key, value in question.items() if key != "correct_answer"}
            for question in state.questions
        ]

    @staticmethod
    def _validate_questions(questions):
        if not isinstance(questions, list) or not questions:
            raise ValueError("Cohere returned no quiz questions")
        for question in questions:
            if not isinstance(question, dict) or not question.get("question") or "correct_answer" not in question:
                raise ValueError("Cohere returned malformed quiz questions")