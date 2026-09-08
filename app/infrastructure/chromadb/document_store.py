"""Persistent ChromaDB storage for educational document chunks."""

from __future__ import annotations

import json

from app.config.settings import Settings
from app.infrastructure.chromadb.client import create_client
from app.modules.rag_retrieval.models import RetrievedChunk


COLLECTION_NAME = "learnmate_educational_document_chunks"


class ChromaDocumentStore:
    def __init__(self, settings: Settings, collection=None):
        self.settings = settings
        client = create_client(settings)
        self.collection = collection or client.get_or_create_collection(name=COLLECTION_NAME)

    @staticmethod
    def vector_ids(document_id: int, chunk_count: int) -> list[str]:
        return [f"document-{document_id}-chunk-{index}" for index in range(chunk_count)]

    def add_chunks(self, document_id: int, chunks, embeddings: list[list[float]]) -> list[str]:
        ids = self.vector_ids(document_id, len(chunks))
        self.collection.upsert(
            ids=ids,
            documents=[chunk.text for chunk in chunks],
            metadatas=[
                {key: str(value) for key, value in chunk.metadata.items()}
                | {"document_id": str(document_id)}
                for chunk in chunks
            ],
            embeddings=embeddings,
        )
        return ids

    def delete_vectors(self, ids: list[str]) -> None:
        if ids:
            self.collection.delete(ids=ids)

    def delete_document(self, document_id: int) -> None:
        self.collection.delete(where={"document_id": str(document_id)})

    def search(
        self,
        query_embedding: list[float],
        student_id: int,
        top_k: int,
        subject: str | None = None,
    ) -> list[RetrievedChunk]:
        where: dict[str, object] = {"student_id": str(student_id)}
        if subject:
            where = {"$and": [{"student_id": str(student_id)}, {"subject": subject}]}
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [
            RetrievedChunk(
                chunk_id=chunk_id,
                text=text,
                metadata=metadata or {},
                distance=distances[index] if index < len(distances) else None,
            )
            for index, (chunk_id, text, metadata) in enumerate(zip(ids, documents, metadatas))
        ]