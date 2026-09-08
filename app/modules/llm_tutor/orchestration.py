"""End-to-end Phase 4 tutor orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.modules.context_generation.builder import ContextBuilder, NO_CONTEXT_RESPONSE
from app.modules.query_understanding.service import QueryUnderstandingService
from app.modules.rag_retrieval.service import CohereReranker


@dataclass(frozen=True)
class TutorResult:
    query_id: int
    response_id: int | None
    response_text: str
    model_name: str | None
    grounded: bool
    sources: list[dict[str, object]]


class TutorService:
    def __init__(
        self,
        settings,
        query_response_repository,
        session_manager,
        embedder,
        vector_store,
        understanding: QueryUnderstandingService | None = None,
        reranker: CohereReranker | None = None,
        context_builder: ContextBuilder | None = None,
        tutor=None,
    ):
        self.settings = settings
        self.repository = query_response_repository
        self.session_manager = session_manager
        self.embedder = embedder
        self.vector_store = vector_store
        self.understanding = understanding or QueryUnderstandingService(settings)
        self.reranker = reranker or CohereReranker(settings)
        self.context_builder = context_builder or ContextBuilder(
            token_counter=lambda text: self.embedder.tokenizer.encode(
                text, add_special_tokens=False
            ),
            max_tokens=settings.context_token_limit,
        )
        self.tutor = tutor

    def answer(self, student_id: int, session_id: str, question: object) -> TutorResult:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question is required")
        question = question.strip()
        conversation = self.session_manager.get_context(session_id)
        understanding = self.understanding.analyze(question, conversation)
        try:
            query = self.repository.create_query(
                student_id=student_id,
                question=question,
                subject=understanding.subject,
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        except Exception as exc:
            raise RuntimeError(f"Query persistence failed: {exc}") from exc 
        retrieval_query = self._retrieval_query(question, understanding)
        try:
            query_embedding = self.embedder.embed([retrieval_query])[0]
        except Exception as exc:
            raise RuntimeError("query embedding generation failed") from exc
        try:
            candidates = self.vector_store.search(
                query_embedding=query_embedding,
                student_id=student_id,
                top_k=self.settings.retrieval_top_k,
                subject=understanding.subject,
            )
        except Exception as exc:
            raise RuntimeError("Chroma retrieval failed") from exc
        reranked = self.reranker.rerank(retrieval_query, candidates)
        context, sources = self.context_builder.select(reranked)
        if not context:
            self.session_manager.add_turn(session_id, question, NO_CONTEXT_RESPONSE)
            return TutorResult(
                query_id=query.query_id,
                response_id=None,
                response_text=NO_CONTEXT_RESPONSE,
                model_name=None,
                grounded=False,
                sources=[],
            )

        if self.tutor is None:
            from app.modules.llm_tutor.service import CohereTutor

            self.tutor = CohereTutor(self.settings)
        messages = self.context_builder.build_messages(
            question, understanding, conversation, context
        )
        response_text = self.tutor.generate(messages)
        try:
            response = self.repository.create_response(
                query_id=query.query_id,
                response_text=response_text,
                model_name=self.tutor.model_name,
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        except Exception as exc:
            raise RuntimeError(f"Query persistence failed: {exc}") from exc
        self.session_manager.add_turn(session_id, question, response_text)
        return TutorResult(
            query_id=query.query_id,
            response_id=response.response_id,
            response_text=response_text,
            model_name=self.tutor.model_name,
            grounded=True,
            sources=sources,
        )

    @staticmethod
    def _retrieval_query(question, understanding) -> str:
        additions = [
            value
            for value in (understanding.subject, understanding.topic, understanding.context)
            if value
        ]
        return question if not additions else f"{question}\nRelevant focus: {'; '.join(additions)}"