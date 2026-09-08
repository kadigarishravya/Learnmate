"""ChromaDB local persistence configuration."""

from __future__ import annotations

from app.config.settings import Settings


def create_client(settings: Settings):
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError(
            "ChromaDB is not installed. Install requirements.txt before initialization."
        ) from exc

    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(settings.chroma_path))


def check_initialization(settings: Settings) -> None:
    client = create_client(settings)
    client.heartbeat()