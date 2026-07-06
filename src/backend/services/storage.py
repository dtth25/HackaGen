"""File storage provider abstractions.

Local filesystem storage is the default. Cloud object storage providers are
declared here as extension points so production storage can be added without
rewriting upload and output flows.
"""

from __future__ import annotations

import os
import re
import shutil
import time
from typing import Any, Protocol, Sequence

from backend.core.config import LOCAL_OUTPUT_DIR, STORAGE_PROVIDER, UPLOAD_DIR, logger


class FileStorage(Protocol):
    """Minimal file storage contract for uploads and generated outputs."""

    def save_upload(self, document_id: str, filename: str, content: bytes, index: int | None = None) -> str:
        """Persist an uploaded file and return its local/provider path."""

    def get_upload(self, path: str) -> bytes:
        """Read a stored upload by path."""

    def save_output(self, document_id: str, relative_path: str, content: bytes) -> str:
        """Persist a generated output artifact and return its path."""

    def get_output(self, path: str) -> bytes:
        """Read a generated output by path."""

    def delete_document_files(self, document_id: str, generated_paths: Sequence[str] | None = None) -> None:
        """Delete uploads and generated artifacts for one document."""

    def health_check(self) -> dict[str, Any]:
        """Return provider readiness."""


def _safe_filename(filename: str) -> str:
    safe = re.sub(r"[^\w\-.]", "_", filename or "upload")
    return safe[:180] or "upload"


class LocalFileStorage:
    """Local filesystem implementation used for development and hackathon demo."""

    provider = "local"

    def __init__(self, upload_dir: str = UPLOAD_DIR, output_dir: str = LOCAL_OUTPUT_DIR):
        self.upload_dir = upload_dir
        self.output_dir = output_dir
        os.makedirs(self.upload_dir, exist_ok=True)
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)

    def _document_upload_dir(self, document_id: str) -> str:
        return os.path.join(self.upload_dir, document_id)

    def save_upload(self, document_id: str, filename: str, content: bytes, index: int | None = None) -> str:
        document_dir = self._document_upload_dir(document_id)
        os.makedirs(document_dir, exist_ok=True)
        prefix = f"{index:02d}_" if index is not None else ""
        file_path = os.path.join(document_dir, f"{prefix}{int(time.time())}_{_safe_filename(filename)}")
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(
            "[Storage] Saved upload provider=local document_id=%s filename=%s size_bytes=%d path=%s",
            document_id,
            filename,
            len(content),
            os.path.abspath(file_path),
        )
        return file_path

    def get_upload(self, path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    def save_output(self, document_id: str, relative_path: str, content: bytes) -> str:
        base_dir = self.output_dir or "."
        file_path = os.path.join(base_dir, document_id, relative_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(
            "[Storage] Saved output provider=local document_id=%s relative_path=%s size_bytes=%d",
            document_id,
            relative_path,
            len(content),
        )
        return file_path

    def get_output(self, path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    def delete_document_files(self, document_id: str, generated_paths: Sequence[str] | None = None) -> None:
        upload_dir = self._document_upload_dir(document_id)
        if os.path.isdir(upload_dir):
            shutil.rmtree(upload_dir, ignore_errors=True)
            logger.info("[Storage] Deleted upload directory document_id=%s path=%s", document_id, upload_dir)

        for path in generated_paths or []:
            if not path or not os.path.exists(path):
                continue
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                logger.info("[Storage] Deleted generated artifact document_id=%s path=%s", document_id, path)
            except Exception as exc:
                logger.warning("[Storage] Failed to delete artifact document_id=%s path=%s error=%s", document_id, path, exc)

    def health_check(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "ready": os.path.isdir(self.upload_dir) and (not self.output_dir or os.path.isdir(self.output_dir)),
            "upload_dir": self.upload_dir,
            "output_dir": self.output_dir,
        }


def get_file_storage(
    provider: str | None = None,
    upload_dir: str | None = None,
    output_dir: str | None = None,
) -> FileStorage:
    """Return the configured file storage provider."""
    selected = (provider or STORAGE_PROVIDER or "local").strip().lower()
    if selected == "local":
        return LocalFileStorage(upload_dir=upload_dir or UPLOAD_DIR, output_dir=output_dir or LOCAL_OUTPUT_DIR)
    if selected in {"s3", "cloudflare_r2", "r2"}:
        raise NotImplementedError(
            f"STORAGE_PROVIDER={selected} is planned for production but not implemented yet. "
            "Use STORAGE_PROVIDER=local for local/dev mode."
        )
    raise ValueError(f"Unknown STORAGE_PROVIDER={selected!r}.")
