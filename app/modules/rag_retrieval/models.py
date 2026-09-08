"""Runtime retrieval models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    text: str
    metadata: dict
    distance: float | None = None
    rerank_score: float | None = None