"""Vector database abstraction layer for grounded generation."""

from backend.vector_db.base import VectorSearchResult, VectorStoreInterface
from backend.vector_db.manager import (
    copy_vector_index,
    create_or_load_vectorstore,
    drop_vector_index,
    get_index_stats,
    get_vector_db_provider,
    health_check,
    list_all_vector_courses,
    list_vector_courses,
    load_existing_vectorstore,
)

__all__ = [
    "VectorSearchResult",
    "VectorStoreInterface",
    "copy_vector_index",
    "create_or_load_vectorstore",
    "drop_vector_index",
    "get_index_stats",
    "get_vector_db_provider",
    "health_check",
    "list_all_vector_courses",
    "list_vector_courses",
    "load_existing_vectorstore",
]
