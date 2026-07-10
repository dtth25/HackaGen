"""Vector Store service wrapper around ChromaDB."""

import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import chromadb

logger = logging.getLogger(__name__)


class Document(BaseModel):
    """Document chunk with content and metadata."""
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GeminiEmbeddingFunction:
    """Chroma embedding function routing chunk/query embedding through Gemini's
    text-embedding API instead of Chroma's bundled English-centric MiniLM default —
    content and queries here are Vietnamese, and generation is already 100% Gemini.

    Uses asymmetric embedding (RETRIEVAL_DOCUMENT for indexing, RETRIEVAL_QUERY for
    search via embed_query) since Gemini's embedding model is trained for this and it
    improves retrieval quality. Batches requests, rate-limits client-side, retries with
    backoff, and caches by content hash so re-processing unchanged chunks costs no quota.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        batch_size: int,
        batch_delay: float,
        max_retries: int,
        max_retry_delay: float,
        requests_per_minute: int,
        cache_dir: str,
    ):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._batch_size = max(1, batch_size)
        self._batch_delay = max(0.0, batch_delay)
        self._max_retries = max(1, max_retries)
        self._max_retry_delay = max(1.0, max_retry_delay)
        self._min_interval = 60.0 / requests_per_minute if requests_per_minute > 0 else 0.0
        self._last_call_time = 0.0
        self._cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def name(self) -> str:
        return "gemini"

    def __call__(self, input: List[str]) -> List[List[float]]:
        return self._embed(list(input), task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, input: List[str]) -> List[List[float]]:
        return self._embed(list(input), task_type="RETRIEVAL_QUERY")

    def _cache_path(self, text: str, task_type: str) -> str:
        h = hashlib.sha256(f"{self._model}:{task_type}:{text}".encode("utf-8")).hexdigest()
        return os.path.join(self._cache_dir, f"{h}.json")

    def _load_cache(self, text: str, task_type: str) -> Optional[List[float]]:
        path = self._cache_path(text, task_type)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def _save_cache(self, text: str, task_type: str, vector: List[float]) -> None:
        path = self._cache_path(text, task_type)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(vector, f)
        except Exception as e:
            logger.warning(f"Failed to write embedding cache entry: {e}")

    def _rate_limit(self) -> None:
        if self._min_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_call_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call_time = time.monotonic()

    def _embed_batch_with_retry(self, texts: List[str], task_type: str) -> List[List[float]]:
        from google.genai import types

        delay = 1.0
        last_exc: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 1):
            try:
                self._rate_limit()
                response = self._client.models.embed_content(
                    model=self._model,
                    contents=texts,
                    config=types.EmbedContentConfig(task_type=task_type),
                )
                return [list(e.values) for e in response.embeddings]
            except Exception as e:
                last_exc = e
                logger.warning(f"Gemini embedding batch attempt {attempt}/{self._max_retries} failed: {e}")
                if attempt < self._max_retries:
                    time.sleep(min(delay, self._max_retry_delay))
                    delay *= 2
        raise RuntimeError(f"Gemini embedding failed after {self._max_retries} attempts: {last_exc}")

    def _embed(self, texts: List[str], task_type: str) -> List[List[float]]:
        results: List[Optional[List[float]]] = [None] * len(texts)
        to_fetch: List[int] = []
        for i, text in enumerate(texts):
            cached = self._load_cache(text, task_type)
            if cached is not None:
                results[i] = cached
            else:
                to_fetch.append(i)

        for start in range(0, len(to_fetch), self._batch_size):
            idx_batch = to_fetch[start : start + self._batch_size]
            batch_texts = [texts[i] for i in idx_batch]
            vectors = self._embed_batch_with_retry(batch_texts, task_type)
            for i, vec in zip(idx_batch, vectors):
                results[i] = vec
                self._save_cache(texts[i], task_type, vec)
            if self._batch_delay and start + self._batch_size < len(to_fetch):
                time.sleep(self._batch_delay)

        return results  # type: ignore[return-value]


def _build_embedding_function() -> Optional[GeminiEmbeddingFunction]:
    """Build the configured embedding function, or None to let Chroma fall back to its
    bundled default (used in tests / when Gemini embedding isn't configured)."""
    if "PYTEST_CURRENT_TEST" in os.environ:
        return None
    from app.core.config import settings

    if getattr(settings, "EMBEDDING_PROVIDER", "default") != "gemini":
        return None
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key or api_key in ("test_gemini_key", "mock_key", "") or api_key.startswith("test_"):
        return None
    try:
        return GeminiEmbeddingFunction(
            api_key=api_key,
            model=settings.GEMINI_EMBEDDING_MODEL,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            batch_delay=settings.EMBEDDING_BATCH_DELAY,
            max_retries=settings.EMBEDDING_MAX_RETRIES,
            max_retry_delay=settings.EMBEDDING_MAX_RETRY_DELAY,
            requests_per_minute=settings.EMBEDDING_REQUESTS_PER_MINUTE,
            cache_dir=settings.EMBEDDING_CACHE_DIR,
        )
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini embedding function, falling back to Chroma default: {e}")
        return None


class VectorStore:
    """Wrapper around ChromaDB for storing and retrieving course document chunks."""

    def __init__(self, collection_name: str, persist_directory: str, embedding_function: Optional[Any] = None):
        self.collection_name = collection_name
        self.persist_directory = persist_directory

        os.makedirs(persist_directory, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_directory)
        ef = embedding_function if embedding_function is not None else _build_embedding_function()
        if ef is not None:
            self.collection = self.client.get_or_create_collection(name=collection_name, embedding_function=ef)
        else:
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

    def search(self, query: str, course_id: str, k: int = 10, max_distance: Optional[float] = None) -> List[Document]:
        """Search for top-k relevant chunks for a specific course. When max_distance is set,
        chunks beyond that Chroma distance (lower = more similar) are dropped even if it means
        returning fewer than k results, instead of padding with irrelevant tail matches."""
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
            distances_list = (
                results["distances"][0]
                if "distances" in results and results["distances"]
                else [None] * len(docs_list)
            )
            for content, meta, distance in zip(docs_list, metas_list, distances_list):
                if max_distance is not None and distance is not None and distance > max_distance:
                    continue
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
