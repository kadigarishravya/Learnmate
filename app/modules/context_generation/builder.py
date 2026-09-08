"""Grounded context and LangChain prompt-message construction."""

from __future__ import annotations

from app.modules.rag_retrieval.models import RetrievedChunk

NO_CONTEXT_RESPONSE = (
    "The uploaded educational materials do not contain enough information to answer "
    "this question reliably."
)


class ContextBuilder:
    def __init__(self, token_counter=None, max_tokens: int = 6000):
        self.token_counter = token_counter or (lambda text: text.split())
        self.max_tokens = max_tokens

    def select(self, chunks: list[RetrievedChunk]) -> tuple[str, list[dict[str, object]]]:
        context_parts: list[str] = []
        sources: list[dict[str, object]] = []
        seen: set[str] = set()
        used = 0
        for chunk in chunks:
            if chunk.chunk_id in seen:
                continue
            chunk_text = chunk.text.strip()
            if not chunk_text:
                continue
            source = {
                "title": chunk.metadata.get("title"),
                "subject": chunk.metadata.get("subject"),
                "page_number": chunk.metadata.get("page_number"),
            }
            prefix = (
                f"[Source: {source['title'] or 'uploaded material'}; "
                f"Subject: {source['subject'] or 'unknown'}; "
                f"Page: {source['page_number'] or 'unknown'}]\n"
            )
            part = prefix + chunk_text
            size = len(self.token_counter(part))
            if used + size > self.max_tokens:
                break
            context_parts.append(part)
            sources.append(source)
            seen.add(chunk.chunk_id)
            used += size
        return "\n\n".join(context_parts), sources

    def build_messages(self, question, understanding, conversation, context):
        try:
            from langchain_core.prompts import ChatPromptTemplate
        except ImportError as exc:
            raise RuntimeError("LangChain Core is required for context generation") from exc
        previous = "\n".join(
            f"Student: {turn['question']}\nTutor: {turn['response']}" for turn in conversation
        ) or "No previous conversation context."
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are LearnMate, an educational tutor. Answer only from the uploaded "
                        "educational context. If it is insufficient, say so transparently. "
                        "Adapt the response format and difficulty to the query understanding.\n"
                        "Query understanding:\n{understanding}\n"
                        "Conversation context:\n{conversation}\n"
                        "Uploaded educational context:\n{context}"
                    ),
                ),
                ("human", "Student question: {question}"),
            ]
        )
        return [
            {
                "role": {"human": "user", "ai": "assistant"}.get(message.type, message.type),
                "content": message.content,
            }
            for message in prompt.format_messages(
                understanding=understanding.as_prompt_text(),
                conversation=previous,
                context=context,
                question=question,
            )
        ]