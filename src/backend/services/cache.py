"""Cache provider abstractions for document and embedding reuse."""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Protocol

from backend.core.config import CACHE_DIR, CACHE_PROVIDER, DOCUMENT_CACHE_ENABLED, EMBEDDING_CACHE_DIR, logger


class CacheProvider(Protocol):
    """Small cache contract that can later move to Redis."""

    def get(self, key: str, default: Any = None) -> Any:
        """Return a cached value."""

    def set(self, key: str, value: Any) -> None:
        """Store a cached value."""

    def delete(self, key: str) -> None:
        """Delete a cached value."""

    def get_document_hash(self, file_hash: str) -> str | None:
        """Return cached document_id/course_id for a file hash."""

    def set_document_hash(self, file_hash: str, document_id: str) -> None:
        """Cache document_id/course_id for a file hash."""

    def get_embedding(self, chunk_hash: str, model: str) -> list[float] | None:
        """Return cached embedding vector for a chunk hash."""

    def set_embedding(self, chunk_hash: str, model: str, embedding: list[float]) -> None:
        """Cache embedding vector for a chunk hash."""

    def health_check(self) -> dict[str, Any]:
        """Return provider readiness."""


class LocalJsonCache:
    """Thread-safe JSON cache for local/dev mode."""

    provider = "local"

    def __init__(
        self,
        cache_dir: str = CACHE_DIR,
        embedding_cache_dir: str = EMBEDDING_CACHE_DIR,
        enabled: bool = DOCUMENT_CACHE_ENABLED,
    ):
        self.cache_dir = cache_dir
        self.embedding_cache_dir = embedding_cache_dir
        self.enabled = enabled
        self.cache_path = os.path.join(self.cache_dir, "provider_cache.json")
        self._lock = threading.Lock()
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.embedding_cache_dir, exist_ok=True)

    def _read_all(self) -> dict[str, Any]:
        if not os.path.exists(self.cache_path):
            return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.warning("[Cache] Could not read local cache %s: %s", self.cache_path, exc)
            return {}

    def _write_all(self, data: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        if not self.enabled:
            return default
        with self._lock:
            return self._read_all().get(key, default)

    def set(self, key: str, value: Any) -> None:
        if not self.enabled:
            return
        with self._lock:
            data = self._read_all()
            data[key] = value
            self._write_all(data)

    def delete(self, key: str) -> None:
        with self._lock:
            data = self._read_all()
            data.pop(key, None)
            self._write_all(data)

    def get_document_hash(self, file_hash: str) -> str | None:
        hashes = self.get("document_hashes", {})
        if isinstance(hashes, dict):
            value = hashes.get(file_hash)
            return str(value) if value else None
        return None

    def set_document_hash(self, file_hash: str, document_id: str) -> None:
        hashes = self.get("document_hashes", {})
        if not isinstance(hashes, dict):
            hashes = {}
        hashes[file_hash] = document_id
        self.set("document_hashes", hashes)

    def _embedding_path(self, chunk_hash: str, model: str) -> str:
        model_key = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in model)[:120]
        return os.path.join(self.embedding_cache_dir, model_key, chunk_hash[:2], f"{chunk_hash}.json")

    def get_embedding(self, chunk_hash: str, model: str) -> list[float] | None:
        if not self.enabled:
            return None
        path = self._embedding_path(chunk_hash, model)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            vector = data.get("embedding") if isinstance(data, dict) else None
            return [float(value) for value in vector] if isinstance(vector, list) else None
        except Exception as exc:
            logger.warning("[Cache] Could not read embedding cache %s: %s", path, exc)
            return None

    def set_embedding(self, chunk_hash: str, model: str, embedding: list[float]) -> None:
        if not self.enabled:
            return
        path = self._embedding_path(chunk_hash, model)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"chunk_hash": chunk_hash, "model": model, "embedding": embedding}, f)

    def health_check(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "ready": os.path.isdir(self.cache_dir),
            "enabled": self.enabled,
            "cache_dir": self.cache_dir,
            "embedding_cache_dir": self.embedding_cache_dir,
        }


def get_cache_provider(provider: str | None = None) -> CacheProvider:
    """Return the configured cache provider."""
    selected = (provider or CACHE_PROVIDER or "local").strip().lower()
    if selected == "local":
        return LocalJsonCache()
    if selected == "redis":
        raise NotImplementedError(
            "CACHE_PROVIDER=redis is planned for production but not implemented yet. "
            "Use CACHE_PROVIDER=local for local/dev mode."
        )
    raise ValueError(f"Unknown CACHE_PROVIDER={selected!r}.")
