# Vector database package
"""
Vector database abstraction layer.
Currently using Milvus (Docker-based) for scalable vector search.
"""

from backend.vector_db.milvus_manager import (
    create_or_load_milvus,
    load_existing_milvus,
    list_milvus_courses,
    get_collection_stats,
    _drop_collection,
)

__all__ = [
    "create_or_load_milvus",
    "load_existing_milvus",
    "list_milvus_courses",
    "get_collection_stats",
    "_drop_collection",
]
