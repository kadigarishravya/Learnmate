"""Controlled local storage and upload validation for educational documents."""

from __future__ import annotations

import uuid
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


class DocumentValidationError(ValueError):
    pass


def validate_upload(
    file: FileStorage | None,
    title: object,
    subject: object,
    supported_extensions: tuple[str, ...],
    max_size_bytes: int,
) -> tuple[str, str, str]:
    if file is None or not file.filename:
        raise DocumentValidationError("a document file is required")
    if not isinstance(title, str) or not title.strip():
        raise DocumentValidationError("title is required")
    if not isinstance(subject, str) or not subject.strip():
        raise DocumentValidationError("subject is required")
    filename = secure_filename(file.filename)
    extension = Path(filename).suffix.lower()
    if not filename or extension not in supported_extensions:
        allowed = ", ".join(supported_extensions)
        raise DocumentValidationError(f"unsupported document type; allowed: {allowed}")

    stream = file.stream
    current_position = stream.tell()
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(current_position)
    if size > max_size_bytes:
        raise DocumentValidationError("document exceeds the configured maximum size")
    return title.strip(), subject.strip(), extension


class LocalDocumentStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, file: FileStorage, extension: str) -> Path:
        generated_name = f"{uuid.uuid4().hex}{extension}"
        destination = (self.root / generated_name).resolve()
        if self.root not in destination.parents:
            raise DocumentValidationError("invalid document storage path")
        file.save(destination)
        return destination

    def delete(self, path: Path) -> None:
        resolved = path.resolve()
        if self.root not in resolved.parents:
            raise DocumentValidationError("invalid document storage path")
        resolved.unlink(missing_ok=True)