"""Chroma retrieval followed by Cohere reranking."""

from __future__ import annotations

from dataclasses import replace

from app.infrastructure.cohere.client import create_client
from app.modules.rag_retrieval.models import RetrievedChunk


class CohereReranker:
    def __init__(self, settings, client=None):
        self.settings = settings
        self.client = client

    def rerank(self, query: str, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not candidates:
            return []
        client = self.client or create_client(self.settings)
        try:
            response = client.rerank(
                model=self.settings.cohere_rerank_model,
                query=query,
                documents=[candidate.text for candidate in candidates],
                top_n=self.settings.rerank_top_n,
            )
        except Exception as exc:
            raise RuntimeError("Cohere Rerank request failed") from exc
        selected: list[RetrievedChunk] = []
        for result in response.results[: self.settings.rerank_top_n]:
            index = getattr(result, "index", None)
            score = getattr(result, "relevance_score", None)
            if isinstance(result, dict):
                index = result.get("index")
                score = result.get("relevance_score")
            if isinstance(index, int) and 0 <= index < len(candidates):
                selected.append(replace(candidates[index], rerank_score=score))
        return selected