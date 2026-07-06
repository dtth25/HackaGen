"""Common vector store contracts for grounded generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence


@dataclass
class VectorSearchResult:
    """One retrieved vector chunk with public-safe text and internal metadata."""

    chunk_id: str
    text: str
    distance: float | None = None
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    source_chunk_id: str | None = None


class VectorStoreInterface(Protocol):
    """Minimal provider interface used by upload/preprocess and RAG retrieval."""

    def health_check(self) -> dict[str, Any]:
        """Return provider readiness and operational details."""

    def add_chunks(
        self,
        document_id: str,
        chunks: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        metadata: Sequence[Mapping[str, Any]] | None = None,
    ) -> int:
        """Persist chunk texts, embeddings, and metadata for one document."""

    def similarity_search(
        self,
        query_embedding: Sequence[float],
        document_id: str | None = None,
        user_id: str | None = None,
        top_k: int = 8,
    ) -> list[VectorSearchResult]:
        """Retrieve top_k chunks for a query embedding."""

    def get_document_chunks(self, document_id: str) -> list[VectorSearchResult]:
        """Return all stored chunks for a document."""

    def delete_document(self, document_id: str) -> None:
        """Delete all chunks for one document."""

    def document_exists(self, document_id: str) -> bool:
        """Return whether a document has at least one stored chunk."""

    def count_chunks(self, document_id: str | None = None) -> int:
        """Count all chunks or chunks for a single document."""
