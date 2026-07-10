"""Vector Store service wrapper around ChromaDB."""

import logging
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import chromadb

logger = logging.getLogger(__name__)


class Document(BaseModel):
    """Document chunk with content and metadata."""
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VectorStore:
    """Wrapper around ChromaDB for storing and retrieving course document chunks."""

    def __init__(self, collection_name: str, persist_directory: str):
        self.collection_name = collection_name
        self.persist_directory = persist_directory

        os.makedirs(persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_documents(self, documents: List[Document], course_id: str) -> None:
        """Add document chunks to ChromaDB collection with course_id metadata."""
        if not documents:
            return

        ids = []
        contents = []
        metadatas = []

        for idx, doc in enumerate(documents):
            # Ensure each document has a unique ID and course_id in metadata
            chunk_id = doc.metadata.get("chunk_id", f"{course_id}_chunk_{idx}")
            ids.append(str(chunk_id))
            contents.append(doc.content)

            meta = dict(doc.metadata)
            meta["course_id"] = str(course_id)
            # Convert any complex types or None in metadata to string/int/float/bool for ChromaDB compatibility
            clean_meta = {}
            for k, v in meta.items():
                if v is None:
                    clean_meta[k] = ""
                elif isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
            metadatas.append(clean_meta)

        # Use upsert to prevent duplicate ID errors on re-processing
        self.collection.upsert(
            ids=ids,
            documents=contents,
            metadatas=metadatas
        )
        logger.info(
            f"Added {len(documents)} chunks for course {course_id} to collection {self.collection_name}"
        )

    def search(self, query: str, course_id: str, k: int = 10) -> List[Document]:
        """Search for top-k relevant chunks for a specific course."""
        if not query or not query.strip():
            return []

        # Check if course has any documents first
        stats = self.get_course_stats(course_id)
        if stats.get("chunk_count", 0) == 0:
            return []

        # Ensure k is not larger than total chunks for this course
        n_results = min(k, stats["chunk_count"])
        if n_results <= 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where={"course_id": str(course_id)}
        )

        documents = []
        if results and "documents" in results and results["documents"]:
            docs_list = results["documents"][0]
            metas_list = (
                results["metadatas"][0]
                if "metadatas" in results and results["metadatas"]
                else [{}] * len(docs_list)
            )
            for content, meta in zip(docs_list, metas_list):
                documents.append(Document(content=content, metadata=meta or {}))

        return documents

    def delete_course(self, course_id: str) -> None:
        """Delete all document chunks belonging to a course."""
        try:
            self.collection.delete(where={"course_id": str(course_id)})
            logger.info(f"Deleted vector chunks for course {course_id}")
        except Exception as e:
            logger.warning(f"Error deleting chunks for course {course_id}: {e}")

    def get_course_stats(self, course_id: str) -> dict:
        """Get statistics about stored chunks for a course."""
        try:
            res = self.collection.get(where={"course_id": str(course_id)})
            count = len(res["ids"]) if res and "ids" in res else 0
            return {
                "course_id": str(course_id),
                "chunk_count": count,
                "collection_name": self.collection_name,
            }
        except Exception as e:
            logger.warning(f"Error getting stats for course {course_id}: {e}")
            return {
                "course_id": str(course_id),
                "chunk_count": 0,
                "collection_name": self.collection_name,
            }

    def get_course_chunks(self, course_id: str, chunk_ids: Optional[List[str]] = None) -> List[Document]:
        """Get all stored chunks for a course, optionally filtered by chunk_ids."""
        try:
            res = self.collection.get(where={"course_id": str(course_id)})
            documents = []
            if res and "ids" in res and res["ids"]:
                ids_list = res["ids"]
                docs_list = res.get("documents", [""] * len(ids_list))
                metas_list = res.get("metadatas", [{}] * len(ids_list))

                target_ids = set(chunk_ids) if chunk_ids else None
                for cid, content, meta in zip(ids_list, docs_list, metas_list):
                    meta_dict = meta or {}
                    meta_dict["chunk_id"] = cid
                    if target_ids is None or cid in target_ids:
                        documents.append(Document(content=content or "", metadata=meta_dict))
            return documents
        except Exception as e:
            logger.warning(f"Error getting chunks for course {course_id}: {e}")
            return []


# Singleton instance
_vector_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get singleton VectorStore instance."""
    global _vector_store_instance
    if _vector_store_instance is None:
        from app.core.config import settings
        _vector_store_instance = VectorStore(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )
    return _vector_store_instance
