"""Sentence Transformer embedding generation adapter."""

from __future__ import annotations

from app.config.settings import Settings
from app.infrastructure.sentence_transformers.model import load_embedding_model


class SentenceTransformerEmbedder:
    def __init__(self, settings: Settings, model=None):
        self.settings = settings
        self._model = model

    @property
    def model(self):
        if self._model is None:
            self._model = load_embedding_model(self.settings)
        return self._model

    @property
    def tokenizer(self):
        return self.model.tokenizer

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return vectors.tolist()