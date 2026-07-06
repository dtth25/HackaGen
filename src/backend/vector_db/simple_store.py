"""Legacy dependency-light persistent local vector store.

This provider is intentionally small: it stores chunk text, metadata, and real
embedding vectors in JSON files, then performs cosine similarity in-process.
It is kept for migration reference and direct legacy tests only. The hackathon
local/dev path is Chroma and must not silently fall back to this store.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.core.config import (
    BATCH_SIZE,
    DOCUMENT_CHUNK_OVERLAP,
    DOCUMENT_CHUNK_SIZE,
    EMBEDDING_REQUESTS_PER_MINUTE,
    INDEX_DIR,
    SIMPLE_VECTOR_DIR,
    get_embeddings,
    logger,
)
from backend.services.doc_processor import analyze_document_quality, get_text_from_any_file
from backend.vector_db.base import VectorSearchResult, VectorStoreInterface
from backend.vector_db.faiss_manager import _batch_embed_texts, _coerce_source_paths, _dedupe_splits


def _safe_document_id(document_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(document_id or "")).strip("_")


def _simple_doc_path(document_id: str, persist_dir: str = SIMPLE_VECTOR_DIR) -> str:
    return os.path.join(persist_dir, f"{_safe_document_id(document_id)}.json")


def _simple_meta_path(course_id: str) -> str:
    return os.path.join(INDEX_DIR, f"simple_{course_id}.json")


def _source_chunk_id(metadata: Mapping[str, Any], fallback_index: int) -> str:
    raw = metadata.get("source_chunk_id") or metadata.get("chunk_id") or fallback_index
    return str(raw) if str(raw).startswith("chunk_") else f"chunk_{raw}"


def _clean_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in dict(metadata or {}).items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            clean[str(key)] = value
        else:
            clean[str(key)] = json.dumps(value, ensure_ascii=False)[:2000]
    return clean


def _cosine_score(query: Sequence[float], vector: Sequence[float]) -> float:
    dot = 0.0
    query_norm = 0.0
    vector_norm = 0.0
    for q_value, v_value in zip(query, vector, strict=False):
        q = float(q_value)
        v = float(v_value)
        dot += q * v
        query_norm += q * q
        vector_norm += v * v
    if query_norm <= 0.0 or vector_norm <= 0.0:
        return 0.0
    return dot / (math.sqrt(query_norm) * math.sqrt(vector_norm))


class SimpleLocalVectorStore(VectorStoreInterface):
    """Persistent JSON vector store with real embeddings and cosine retrieval."""

    def __init__(self, persist_dir: str = SIMPLE_VECTOR_DIR):
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)

    def health_check(self) -> dict[str, Any]:
        try:
            os.makedirs(self.persist_dir, exist_ok=True)
            documents = [
                name for name in os.listdir(self.persist_dir)
                if name.endswith(".json") and os.path.isfile(os.path.join(self.persist_dir, name))
            ]
            return {
                "provider": "simple",
                "ready": True,
                "persist_dir": self.persist_dir,
                "document_count": len(documents),
                "chunk_count": self.count_chunks(),
            }
        except Exception as exc:
            logger.exception("[SimpleVector] Health check failed: %s", exc)
            return {"provider": "simple", "ready": False, "persist_dir": self.persist_dir, "error": str(exc)}

    def _load_payload(self, document_id: str) -> dict[str, Any] | None:
        path = _simple_doc_path(document_id, self.persist_dir)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("[SimpleVector] Could not read document %s: %s", document_id, exc)
            return None

    def _save_payload(self, document_id: str, payload: Mapping[str, Any]) -> None:
        os.makedirs(self.persist_dir, exist_ok=True)
        path = _simple_doc_path(document_id, self.persist_dir)
        tmp_path = f"{path}.{os.getpid()}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp_path, path)

    def _iter_payloads(self):
        if not os.path.isdir(self.persist_dir):
            return
        for name in os.listdir(self.persist_dir):
            if not name.endswith(".json"):
                continue
            path = os.path.join(self.persist_dir, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    yield json.load(f)
            except Exception as exc:
                logger.warning("[SimpleVector] Ignoring unreadable vector file %s: %s", path, exc)

    def add_chunks(
        self,
        document_id: str,
        chunks: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        metadata: Sequence[Mapping[str, Any]] | None = None,
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunk count ({len(chunks)}) does not match embedding count ({len(embeddings)}).")

        metadatas = list(metadata or [{} for _ in chunks])
        if len(metadatas) != len(chunks):
            raise ValueError("Metadata count must match chunk count.")

        items: list[dict[str, Any]] = []
        created_at = time.time()
        for index, (chunk, vector, raw_meta) in enumerate(zip(chunks, embeddings, metadatas, strict=False)):
            text = " ".join(str(chunk or "").split())
            if not text:
                continue
            meta = _clean_metadata(raw_meta)
            meta["document_id"] = document_id
            meta.setdefault("chunk_id", index)
            meta.setdefault("source_chunk_id", _source_chunk_id(meta, index))
            meta.setdefault("chunk_type", "content")
            meta.setdefault("created_at", created_at)
            items.append(
                {
                    "id": f"{document_id}:{index:06d}",
                    "text": text,
                    "embedding": [float(value) for value in vector],
                    "metadata": meta,
                }
            )

        self._save_payload(
            document_id,
            {
                "document_id": document_id,
                "provider": "simple",
                "created_at": created_at,
                "updated_at": time.time(),
                "chunks": items,
            },
        )
        logger.info("[SimpleVector] Stored %d chunks for document_id=%s", len(items), document_id)
        return len(items)

    def similarity_search(
        self,
        query_embedding: Sequence[float],
        document_id: str | None = None,
        user_id: str | None = None,
        top_k: int = 8,
    ) -> list[VectorSearchResult]:
        payloads = [self._load_payload(document_id)] if document_id else list(self._iter_payloads() or [])
        scored: list[VectorSearchResult] = []
        for payload in payloads:
            if not payload:
                continue
            for index, item in enumerate(payload.get("chunks") or []):
                metadata = dict(item.get("metadata") or {})
                if user_id and metadata.get("user_id") != user_id:
                    continue
                vector = item.get("embedding") or []
                score = _cosine_score(query_embedding, vector)
                chunk_id = str(metadata.get("chunk_id", index))
                source_id = str(metadata.get("source_chunk_id") or _source_chunk_id(metadata, index))
                scored.append(
                    VectorSearchResult(
                        chunk_id=chunk_id,
                        text=str(item.get("text") or ""),
                        distance=1.0 - score,
                        score=score,
                        metadata=metadata,
                        source_chunk_id=source_id,
                    )
                )

        scored.sort(key=lambda item: item.score if item.score is not None else -1.0, reverse=True)
        results = scored[: max(1, int(top_k or 8))]
        logger.info("[SimpleVector] Retrieved %d chunks document_id=%s top_k=%d", len(results), document_id or "*", top_k)
        return results

    def get_document_chunks(self, document_id: str) -> list[VectorSearchResult]:
        payload = self._load_payload(document_id)
        if not payload:
            return []
        chunks: list[VectorSearchResult] = []
        for index, item in enumerate(payload.get("chunks") or []):
            metadata = dict(item.get("metadata") or {})
            chunk_id = str(metadata.get("chunk_id", index))
            source_id = str(metadata.get("source_chunk_id") or _source_chunk_id(metadata, index))
            chunks.append(
                VectorSearchResult(
                    chunk_id=chunk_id,
                    text=str(item.get("text") or ""),
                    metadata=metadata,
                    source_chunk_id=source_id,
                )
            )
        return chunks

    def delete_document(self, document_id: str) -> None:
        path = _simple_doc_path(document_id, self.persist_dir)
        if os.path.exists(path):
            os.remove(path)
            logger.info("[SimpleVector] Deleted document_id=%s", document_id)

    def document_exists(self, document_id: str) -> bool:
        payload = self._load_payload(document_id)
        return bool(payload and payload.get("chunks"))

    def count_chunks(self, document_id: str | None = None) -> int:
        if document_id:
            payload = self._load_payload(document_id)
            return len(payload.get("chunks") or []) if payload else 0
        total = 0
        for payload in self._iter_payloads() or []:
            total += len(payload.get("chunks") or [])
        return total

    def copy_document(self, source_document_id: str, target_document_id: str) -> int:
        source = self._load_payload(source_document_id)
        if not source or not source.get("chunks"):
            return 0
        copied: list[dict[str, Any]] = []
        for index, item in enumerate(source.get("chunks") or []):
            metadata = dict(item.get("metadata") or {})
            metadata["document_id"] = target_document_id
            metadata["cached_from"] = source_document_id
            metadata["chunk_id"] = index
            metadata["source_chunk_id"] = _source_chunk_id(metadata, index)
            copied.append(
                {
                    "id": f"{target_document_id}:{index:06d}",
                    "text": str(item.get("text") or ""),
                    "embedding": [float(value) for value in item.get("embedding") or []],
                    "metadata": metadata,
                }
            )
        self._save_payload(
            target_document_id,
            {
                "document_id": target_document_id,
                "provider": "simple",
                "created_at": source.get("created_at") or time.time(),
                "updated_at": time.time(),
                "cached_from": source_document_id,
                "chunks": copied,
            },
        )
        return len(copied)


class SimpleCourseVectorStore:
    """LangChain-like adapter scoped to a single course/document."""

    def __init__(self, document_id: str, store: SimpleLocalVectorStore | None = None):
        self.document_id = document_id
        self.store = store or SimpleLocalVectorStore()
        self.embeddings = get_embeddings()

    def as_retriever(self, search_kwargs: Mapping[str, Any] | None = None):
        return _SimpleRetriever(self, dict(search_kwargs or {}))


class _SimpleRetriever:
    def __init__(self, vectorstore: SimpleCourseVectorStore, search_kwargs: dict[str, Any]):
        self.vectorstore = vectorstore
        self.search_kwargs = search_kwargs

    def invoke(self, query: str, *args, **kwargs) -> list[Document]:
        top_k = int(self.search_kwargs.get("k") or self.search_kwargs.get("top_k") or 8)
        query_vector = self.vectorstore.embeddings.embed_query(str(query or ""))
        results = self.vectorstore.store.similarity_search(
            query_embedding=query_vector,
            document_id=self.vectorstore.document_id,
            top_k=top_k,
        )
        docs: list[Document] = []
        for result in results:
            metadata = dict(result.metadata or {})
            metadata["chunk_id"] = result.chunk_id
            metadata["source_chunk_id"] = result.source_chunk_id or _source_chunk_id(metadata, 0)
            if result.distance is not None:
                metadata["distance"] = result.distance
            if result.score is not None:
                metadata["score"] = result.score
            docs.append(Document(page_content=result.text, metadata=metadata))
        return docs


def create_or_load_simple(
    course_id: str,
    source_paths: str | Sequence[str],
    on_progress: Callable[[int, int, str], None] | None = None,
) -> SimpleCourseVectorStore:
    """Create or load a SimpleLocalVectorStore-backed course vector store."""
    store = SimpleLocalVectorStore()
    meta_path = _simple_meta_path(course_id)
    if store.document_exists(course_id):
        logger.info("[Course %s] Found existing Simple vectors, loading adapter...", course_id)
        if not os.path.exists(meta_path):
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "course_id": course_id,
                        "provider": "simple",
                        "persist_dir": SIMPLE_VECTOR_DIR,
                        "num_chunks": store.count_chunks(course_id),
                        "restored_from_simple": True,
                        "created_at": time.time(),
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        return SimpleCourseVectorStore(course_id, store)

    paths = _coerce_source_paths(source_paths)
    if not paths:
        raise ValueError("No upload files were provided.")

    logger.info("[Course %s] Building new Simple vector document from %s file(s)...", course_id, len(paths))
    step_times: dict[str, float] = {}
    t_total = time.perf_counter()

    t_extract = time.perf_counter()
    if on_progress:
        on_progress(0, 100, "Dang trich xuat van ban...")

    valid_docs: list[Document] = []
    file_stats: list[dict[str, Any]] = []
    total_pages = 0
    total_extracted_chars = 0
    total_file_size_bytes = 0

    for doc_index, path in enumerate(paths):
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")

        def _doc_progress(current, total, message):
            if on_progress:
                file_pct = (doc_index / max(len(paths), 1)) * 30
                page_pct = (current / max(total, 1)) * (30 / max(len(paths), 1))
                on_progress(int(file_pct + page_pct), 100, message)

        file_docs = get_text_from_any_file(path, on_progress=_doc_progress)
        filename = os.path.basename(path)
        file_size_bytes = os.path.getsize(path)
        file_pages = max([int(doc.metadata.get("pdf_total_pages", 0) or 0) for doc in file_docs] or [0])
        if file_pages == 0 and file_docs:
            file_pages = len(file_docs)
        file_chars = sum(int(doc.metadata.get("text_chars", len(doc.page_content)) or 0) for doc in file_docs)
        total_file_size_bytes += file_size_bytes
        total_pages += file_pages
        total_extracted_chars += file_chars
        file_stats.append(
            {
                "filename": filename,
                "size_bytes": file_size_bytes,
                "pages": file_pages,
                "documents": len(file_docs),
                "extracted_chars": file_chars,
            }
        )
        for doc in file_docs:
            doc.metadata["doc_id"] = doc_index
            doc.metadata["source_file"] = filename
            doc.metadata["course_id"] = course_id
        valid_docs.extend(file_docs)

    if not valid_docs:
        raise ValueError("File contains no valid text content.")

    step_times["extract_text"] = round(time.perf_counter() - t_extract, 2)
    logger.info(
        "[Course %s] Text extraction: %.2fs (files=%d, size=%d bytes, pages=%d, chars=%d, docs=%d)",
        course_id,
        step_times["extract_text"],
        len(paths),
        total_file_size_bytes,
        total_pages,
        total_extracted_chars,
        len(valid_docs),
    )

    doc_quality_report = analyze_document_quality(course_id, paths[0], valid_docs)

    t_chunk = time.perf_counter()
    if on_progress:
        on_progress(30, 100, "Dang phan manh tai lieu...")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=DOCUMENT_CHUNK_SIZE,
        chunk_overlap=DOCUMENT_CHUNK_OVERLAP,
        separators=["\n# ", "\n## ", "\n### ", "\nChuong ", "\nBai ", "\n\n", "\n", ". ", " ", ""],
    )
    raw_splits = text_splitter.split_documents(valid_docs)
    chunks_before_filter = len(raw_splits)
    splits = _dedupe_splits(raw_splits)
    num_chunks = len(splits)
    if num_chunks == 0:
        raise ValueError("File contains no usable text chunks after preprocessing.")

    for idx, doc in enumerate(splits):
        doc.metadata["chunk_id"] = idx
        doc.metadata["source_chunk_id"] = f"chunk_{idx}"
        doc.metadata["course_id"] = course_id
        doc.metadata["document_id"] = course_id
        doc.metadata.setdefault("source_file", os.path.basename(paths[0]))
        doc.metadata.setdefault("chunk_type", "content")
        if "page" not in doc.metadata:
            doc.metadata["page"] = idx // 5 + 1

    step_times["chunking"] = round(time.perf_counter() - t_chunk, 2)
    logger.info(
        "[Course %s] Chunking: %.2fs chunks_before=%d chunks_after=%d chunk_size=%d overlap=%d",
        course_id,
        step_times["chunking"],
        chunks_before_filter,
        num_chunks,
        DOCUMENT_CHUNK_SIZE,
        DOCUMENT_CHUNK_OVERLAP,
    )

    t_embed = time.perf_counter()
    if on_progress:
        on_progress(35, 100, "Dang tao vector chi muc...")

    embeddings_model = get_embeddings()
    texts = [doc.page_content for doc in splits]
    embedding_stats: dict[str, Any] = {}

    def _embed_progress(current, total, message):
        if on_progress:
            pct = 35 + int((current / max(total, 1)) * 55)
            on_progress(pct, 100, message)

    all_vectors = _batch_embed_texts(
        texts,
        embeddings_model,
        batch_size=BATCH_SIZE,
        on_progress=_embed_progress,
        stats=embedding_stats,
    )
    step_times["embedding"] = round(time.perf_counter() - t_embed, 2)
    logger.info(
        "[Course %s] Embedding: %.2fs (requests=%d, batches=%d, cache_hits=%d, retries=%d)",
        course_id,
        step_times["embedding"],
        embedding_stats.get("embedding_requests_sent", 0),
        embedding_stats.get("embedding_api_batches", 0),
        embedding_stats.get("embedding_cache_hits", 0),
        embedding_stats.get("embedding_retry_count", 0),
    )

    t_insert = time.perf_counter()
    if on_progress:
        on_progress(90, 100, "Dang luu chunks vao Simple Vector DB...")
    metadatas = [doc.metadata for doc in splits]
    inserted = store.add_chunks(course_id, texts, all_vectors, metadatas)
    step_times["simple_insert"] = round(time.perf_counter() - t_insert, 2)
    step_times["vector_insert"] = step_times["simple_insert"]
    total_time = round(time.perf_counter() - t_total, 2)

    os.makedirs(INDEX_DIR, exist_ok=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "course_id": course_id,
                "provider": "simple",
                "persist_dir": SIMPLE_VECTOR_DIR,
                "num_chunks": inserted,
                "num_chunks_before_filter": chunks_before_filter,
                "num_documents": len(paths),
                "source_files": [os.path.basename(path) for path in paths],
                "file_stats": file_stats,
                "total_file_size_bytes": total_file_size_bytes,
                "num_pages": total_pages,
                "num_extracted_chars": total_extracted_chars,
                "embedding_batch_size": BATCH_SIZE,
                "num_embedding_batches": embedding_stats.get(
                    "embedding_api_batches",
                    (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE,
                ),
                "embedding_requests_sent": embedding_stats.get("embedding_requests_sent", len(texts)),
                "embedding_cache_hits": embedding_stats.get("embedding_cache_hits", 0),
                "embedding_cache_misses": embedding_stats.get("embedding_cache_misses", len(texts)),
                "embedding_duplicate_hits": embedding_stats.get("embedding_duplicate_hits", 0),
                "embedding_retry_count": embedding_stats.get("embedding_retry_count", 0),
                "embedding_rate_limit_per_minute": embedding_stats.get(
                    "embedding_rate_limit_per_minute",
                    EMBEDDING_REQUESTS_PER_MINUTE,
                ),
                "embedding_throttle_sleep_seconds": embedding_stats.get("embedding_throttle_sleep_seconds", 0.0),
                "chunk_size": DOCUMENT_CHUNK_SIZE,
                "chunk_overlap": DOCUMENT_CHUNK_OVERLAP,
                "created_at": time.time(),
                "step_times": step_times,
                "total_preprocess_seconds": total_time,
                "document_quality_report": doc_quality_report,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    if on_progress:
        on_progress(100, 100, "Hoan thanh!")

    logger.info(
        "[Course %s] Simple vectors saved. Total: %.2fs (files=%d, pages=%d, chars=%d, chunks=%d)",
        course_id,
        total_time,
        len(paths),
        total_pages,
        total_extracted_chars,
        inserted,
    )
    return SimpleCourseVectorStore(course_id, store)


def load_existing_simple(course_id: str) -> SimpleCourseVectorStore | None:
    try:
        store = SimpleLocalVectorStore()
        if not store.document_exists(course_id):
            logger.warning("[Restore] Simple document '%s' not found.", course_id)
            return None
        logger.info("[Restore] Loaded Simple document '%s'.", course_id)
        return SimpleCourseVectorStore(course_id, store)
    except Exception as exc:
        logger.error("[Restore] Failed to load Simple document '%s': %s", course_id, exc)
        return None


def list_simple_courses() -> list[str]:
    courses: list[str] = []
    if not os.path.exists(INDEX_DIR):
        return courses
    for fname in os.listdir(INDEX_DIR):
        if fname.startswith("simple_") and fname.endswith(".json"):
            courses.append(fname[len("simple_") : -len(".json")])
    return sorted(courses)


def drop_simple_index(course_id: str) -> None:
    store = SimpleLocalVectorStore()
    store.delete_document(course_id)
    meta_path = _simple_meta_path(course_id)
    if os.path.exists(meta_path):
        os.remove(meta_path)


def get_simple_index_stats(course_id: str) -> dict[str, Any]:
    meta_path = _simple_meta_path(course_id)
    meta: dict[str, Any] = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    store = SimpleLocalVectorStore()
    exists = store.document_exists(course_id)
    chunk_count = store.count_chunks(course_id) if exists else 0
    return {
        "exists": exists,
        "provider": "simple",
        "persist_dir": SIMPLE_VECTOR_DIR,
        "num_chunks": meta.get("num_chunks") or chunk_count,
        "num_chunks_before_filter": meta.get("num_chunks_before_filter"),
        "num_pages": meta.get("num_pages"),
        "num_extracted_chars": meta.get("num_extracted_chars"),
        "total_file_size_bytes": meta.get("total_file_size_bytes"),
        "embedding_batch_size": meta.get("embedding_batch_size"),
        "num_embedding_batches": meta.get("num_embedding_batches"),
        "embedding_requests_sent": meta.get("embedding_requests_sent"),
        "embedding_cache_hits": meta.get("embedding_cache_hits"),
        "embedding_cache_misses": meta.get("embedding_cache_misses"),
        "embedding_retry_count": meta.get("embedding_retry_count"),
        "embedding_rate_limit_per_minute": meta.get("embedding_rate_limit_per_minute"),
        "embedding_throttle_sleep_seconds": meta.get("embedding_throttle_sleep_seconds"),
        "step_times": meta.get("step_times"),
        "total_preprocess_seconds": meta.get("total_preprocess_seconds"),
        "created_at": meta.get("created_at"),
        "document_quality_report": meta.get("document_quality_report"),
    }


def copy_simple_document(course_id: str, cached_course_id: str) -> bool:
    store = SimpleLocalVectorStore()
    copied = store.copy_document(cached_course_id, course_id)
    if copied <= 0:
        return False

    source_meta_path = _simple_meta_path(cached_course_id)
    target_meta_path = _simple_meta_path(course_id)
    meta: dict[str, Any] = {}
    if os.path.exists(source_meta_path):
        with open(source_meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    meta.update(
        {
            "course_id": course_id,
            "provider": "simple",
            "cached_from": cached_course_id,
            "num_chunks": copied,
            "persist_dir": SIMPLE_VECTOR_DIR,
        }
    )
    with open(target_meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    logger.info("[SimpleVector] Copied %d cached chunks from %s to %s", copied, cached_course_id, course_id)
    return True
