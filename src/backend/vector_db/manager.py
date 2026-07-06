"""Provider selection facade for local vector DB backends."""

from __future__ import annotations
from collections.abc import Callable, Sequence
from typing import Any

from backend.core.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    MILVUS_COLLECTION_NAME,
    MILVUS_HOST,
    MILVUS_PORT,
    VECTOR_DB_PROVIDER,
    logger,
)
from backend.vector_db.chroma_store import (
    ChromaVectorStore,
    copy_chroma_document,
    create_or_load_chroma,
    drop_chroma_index,
    get_chroma_index_stats,
    list_chroma_courses,
    load_existing_chroma,
)


FUTURE_PRODUCTION_PROVIDERS = {"milvus", "qdrant", "pgvector"}


def get_vector_db_provider() -> str:
    """Return the configured vector DB provider."""
    return VECTOR_DB_PROVIDER if VECTOR_DB_PROVIDER in {"chroma", *FUTURE_PRODUCTION_PROVIDERS} else "chroma"


def _chroma_unavailable_state(error: Exception | str) -> dict[str, Any]:
    """Return a clear mandatory-Chroma failure payload without fallback."""
    return {
        "provider": "chroma",
        "ready": False,
        "persist_dir": CHROMA_PERSIST_DIR,
        "collection": CHROMA_COLLECTION_NAME,
        "error": str(error),
        "install_hint": (
            "Chroma is mandatory for the hackathon demo. Run `cd src/backend && uv sync --all-extras`, "
            "then start backend from `src` with `uv run --project backend uvicorn backend.main:app --reload --port 8000`."
        ),
    }


def _future_provider_state(provider: str) -> dict[str, Any]:
    """Return an explicit not-ready state for production-only providers."""
    payload: dict[str, Any] = {
        "provider": provider,
        "ready": False,
        "error": (
            f"VECTOR_DB_PROVIDER={provider} is reserved for future production deployment. "
            "Local/dev and hackathon demo mode require VECTOR_DB_PROVIDER=chroma."
        ),
        "install_hint": "Use Chroma locally: VECTOR_DB_PROVIDER=chroma.",
    }
    if provider == "milvus":
        payload.update(
            {
                "host": MILVUS_HOST,
                "port": MILVUS_PORT,
                "collection": MILVUS_COLLECTION_NAME,
            }
        )
    return payload


def health_check() -> dict[str, Any]:
    """Return provider health without calling Gemini."""
    provider = get_vector_db_provider()
    logger.info("[VectorDB] Health check provider=%s", provider)
    if provider == "chroma":
        try:
            return ChromaVectorStore().health_check()
        except Exception as exc:
            logger.error("[VectorDB] Chroma health check failed. No fallback will be used: %s", exc)
            return _chroma_unavailable_state(exc)
    return _future_provider_state(provider)


def create_or_load_vectorstore(
    course_id: str,
    source_paths: str | Sequence[str],
    on_progress: Callable[[int, int, str], None] | None = None,
    user_id: str | None = None,
):
    """Create or load a course-scoped vector store for the selected provider."""
    provider = get_vector_db_provider()
    logger.info("[VectorDB] create_or_load provider=%s course_id=%s", provider, course_id)
    if provider == "chroma":
        return create_or_load_chroma(course_id, source_paths, on_progress=on_progress, user_id=user_id)
    raise RuntimeError(
        f"VECTOR_DB_PROVIDER={provider} is a future production option and is not implemented here. "
        "Use VECTOR_DB_PROVIDER=chroma for local/dev."
    )


def load_existing_vectorstore(course_id: str):
    """Load a course vector store for the selected provider."""
    provider = get_vector_db_provider()
    logger.info("[VectorDB] load_existing provider=%s course_id=%s", provider, course_id)
    if provider == "chroma":
        return load_existing_chroma(course_id)
    logger.error("[VectorDB] Future provider %s requested but is not implemented.", provider)
    return None


def list_vector_courses() -> list[str]:
    """List course IDs known to the selected provider."""
    provider = get_vector_db_provider()
    if provider == "chroma":
        return list_chroma_courses()
    return []


def list_all_vector_courses() -> list[str]:
    """List course IDs from the required local Chroma provider."""
    return sorted(set(list_chroma_courses()))


def drop_vector_index(course_id: str) -> None:
    """Delete course vectors from the selected provider."""
    provider = get_vector_db_provider()
    logger.info("[VectorDB] drop provider=%s course_id=%s", provider, course_id)
    if provider == "chroma":
        drop_chroma_index(course_id)
    else:
        raise RuntimeError(f"Cannot drop vectors for future provider {provider!r}; use Chroma locally.")


def get_index_stats(course_id: str) -> dict[str, Any]:
    """Get preprocessing/vector stats for the selected provider."""
    provider = get_vector_db_provider()
    if provider == "chroma":
        return get_chroma_index_stats(course_id)
    return {"exists": False, **_future_provider_state(provider)}


def copy_vector_index(course_id: str, cached_course_id: str, user_id: str | None = None) -> bool:
    """Copy cached vector data between course IDs for duplicate uploads."""
    provider = get_vector_db_provider()
    logger.info(
        "[VectorDB] copy provider=%s cached_course_id=%s target_course_id=%s",
        provider,
        cached_course_id,
        course_id,
    )
    if provider == "chroma":
        return copy_chroma_document(course_id, cached_course_id, user_id=user_id)
    return False
