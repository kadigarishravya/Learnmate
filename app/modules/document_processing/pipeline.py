"""Deterministic PDF extraction, cleaning, chunking, and metadata generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class ProcessingError(ValueError):
    pass


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class ProcessedChunk:
    index: int
    text: str
    metadata: dict[str, object]


class Tokenizer(Protocol):
    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]: ...

    def decode(self, token_ids: list[int], skip_special_tokens: bool = True) -> str: ...


def extract_pdf_pages(path: Path) -> list[ExtractedPage]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ProcessingError("PDF processing requires the pypdf package") from exc
    try:
        reader = PdfReader(str(path))
        pages = [ExtractedPage(index + 1, page.extract_text() or "") for index, page in enumerate(reader.pages)]
    except Exception as exc:
        raise ProcessingError("document text extraction failed") from exc
    if not pages or not any(page.text.strip() for page in pages):
        raise ProcessingError("document contains no extractable text")
    return pages


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class TokenChunker:
    def __init__(self, tokenizer: Tokenizer, chunk_size: int = 512, chunk_overlap: int = 80):
        if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk size and overlap must be valid, with overlap smaller than size")
        self.tokenizer = tokenizer
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_pages(self, pages: list[ExtractedPage], document_id: int) -> list[ProcessedChunk]:
        chunks: list[ProcessedChunk] = []
        step = self.chunk_size - self.chunk_overlap
        for page in pages:
            page_text = clean_text(page.text)
            if not page_text:
                continue
            token_ids = self.tokenizer.encode(page_text, add_special_tokens=False)
            for start in range(0, len(token_ids), step):
                chunk_text = self.tokenizer.decode(
                    token_ids[start : start + self.chunk_size], skip_special_tokens=True
                ).strip()
                if chunk_text:
                    chunks.append(
                        ProcessedChunk(
                            index=len(chunks),
                            text=chunk_text,
                            metadata={
                                "document_id": document_id,
                                "chunk_index": len(chunks),
                                "page_number": page.page_number,
                            },
                        )
                    )
                if start + self.chunk_size >= len(token_ids):
                    break
        if not chunks:
            raise ProcessingError("document produced no meaningful chunks")
        return chunks