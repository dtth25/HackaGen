"""Chroma vector store provider for local RAG demos."""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.core.config import (
    BATCH_SIZE,
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    DOCUMENT_CHUNK_OVERLAP,
    DOCUMENT_CHUNK_SIZE,
    EMBEDDING_REQUESTS_PER_MINUTE,
    INDEX_DIR,
    get_embeddings,
    logger,
)
from backend.services.context_cleaner import classify_chunk
from backend.services.doc_processor import analyze_document_quality, get_text_from_any_file
from backend.vector_db.base import VectorSearchResult, VectorStoreInterface
from backend.vector_db.faiss_manager import _batch_embed_texts, _coerce_source_paths, _dedupe_splits


CHROMA_BATCH_SIZE = int(os.getenv("CHROMA_BATCH_SIZE", "500"))


def _chroma_meta_path(course_id: str) -> str:
    return os.path.join(INDEX_DIR, f"chroma_{course_id}.json")


def _clean_metadata(metadata: Mapping[str, Any] | None) -> dict[str, str | int | float | bool]:
    """Keep only Chroma-compatible primitive metadata values."""
    clean: dict[str, str | int | float | bool] = {}
    for key, value in dict(metadata or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            clean[str(key)] = value
        elif isinstance(value, int) and not isinstance(value, bool):
            clean[str(key)] = value
        elif isinstance(value, float):
            clean[str(key)] = float(value)
        elif isinstance(value, str):
            clean[str(key)] = value[:2000]
        else:
            clean[str(key)] = json.dumps(value, ensure_ascii=False)[:2000]
    return clean


def _source_chunk_id(metadata: Mapping[str, Any], fallback_index: int) -> str:
    raw = metadata.get("source_chunk_id") or metadata.get("chunk_id") or fallback_index
    return str(raw) if str(raw).startswith("chunk_") else f"chunk_{raw}"


#: chunk_type values that should never be used to generate content, only to
#: display/debug. Chunks indexed before this classification existed default to
#: "content", which is intentionally not in this set (backward compatible).
EXCLUDED_GENERATION_CHUNK_TYPES = ("toc", "noisy", "heading")


def _where_filter(
    document_id: str | None = None,
    user_id: str | None = None,
    extra_filters: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build a Chroma `where` clause. Chroma requires every dict (including nested
    ones passed via `$and`) to have exactly one key, so each field becomes its own
    single-key clause rather than one multi-key dict."""
    clauses: list[dict[str, Any]] = []
    if document_id:
        clauses.append({"document_id": document_id})
    if user_id:
        clauses.append({"user_id": user_id})
    for key, value in (extra_filters or {}).items():
        clauses.append({key: value})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


class ChromaVectorStore(VectorStoreInterface):
    """Persistent local Chroma collection for document chunks."""

    def __init__(
        self,
        persist_dir: str = CHROMA_PERSIST_DIR,
        collection_name: str = CHROMA_COLLECTION_NAME,
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        os.makedirs(self.persist_dir, exist_ok=True)

        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as exc:
            raise RuntimeError(
                "chromadb is not installed. Chroma is mandatory for the hackathon demo. "
                "Run `cd src/backend && uv sync --all-extras`, then start the backend from `src`."
            ) from exc

        logging.getLogger("chromadb.telemetry.product.posthog").disabled = True
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "[Chroma] Ready provider persist_dir=%s collection=%s",
            os.path.abspath(self.persist_dir),
            self.collection_name,
        )

    def health_check(self) -> dict[str, Any]:
        try:
            count = self.collection.count()
            return {
                "provider": "chroma",
                "ready": True,
                "persist_dir": self.persist_dir,
                "collection": self.collection_name,
                "chunk_count": count,
            }
        except Exception as exc:
            logger.exception("[Chroma] Health check failed: %s", exc)
            return {
                "provider": "chroma",
                "ready": False,
                "persist_dir": self.persist_dir,
                "collection": self.collection_name,
                "error": str(exc),
                "install_hint": (
                    "Chroma is mandatory for the hackathon demo. Run `cd src/backend && uv sync --all-extras` "
                    "and check that CHROMA_PERSIST_DIR is writable."
                ),
            }

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

        self.delete_document(document_id)
        inserted = 0
        created_at = time.time()

        for start in range(0, len(chunks), CHROMA_BATCH_SIZE):
            end = min(start + CHROMA_BATCH_SIZE, len(chunks))
            ids: list[str] = []
            docs: list[str] = []
            vectors: list[list[float]] = []
            batch_meta: list[dict[str, str | int | float | bool]] = []

            for offset, (chunk, vector, raw_meta) in enumerate(
                zip(chunks[start:end], embeddings[start:end], metadatas[start:end], strict=False),
                start=start,
            ):
                text = " ".join(str(chunk or "").split())
                if not text:
                    continue
                meta = _clean_metadata(raw_meta)
                meta["document_id"] = document_id
                meta.setdefault("chunk_id", offset)
                meta.setdefault("source_chunk_id", _source_chunk_id(meta, offset))
                meta.setdefault("chunk_type", "content")
                meta.setdefault("created_at", created_at)
                ids.append(f"{document_id}:{offset:06d}")
                docs.append(text)
                vectors.append([float(value) for value in vector])
                batch_meta.append(meta)

            if not ids:
                continue

            self.collection.add(
                ids=ids,
                documents=docs,
                embeddings=vectors,
                metadatas=batch_meta,
            )
            inserted += len(ids)
            logger.info(
                "[Chroma] Inserted chunks %d-%d for document_id=%s collection=%s",
                start + 1,
                end,
                document_id,
                self.collection_name,
            )

        logger.info("[Chroma] Stored %d chunks for document_id=%s", inserted, document_id)
        return inserted

    def _dedupe_and_diversify(
        self, items: list[VectorSearchResult], top_k: int, max_per_page: int = 2
    ) -> list[VectorSearchResult]:
        """Drop near-duplicate text and cap how many chunks come from the same page.

        Ranking order (distance ascending, already returned by Chroma) is preserved
        as the tie-breaker, so the closest matches still win within each page.
        """
        seen_signatures: set[str] = set()
        per_page_count: dict[Any, int] = {}
        selected: list[VectorSearchResult] = []
        overflow: list[VectorSearchResult] = []

        for item in items:
            signature = " ".join(item.text.lower().split())[:200]
            if signature and signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            page = item.metadata.get("page")
            if per_page_count.get(page, 0) < max_per_page:
                per_page_count[page] = per_page_count.get(page, 0) + 1
                selected.append(item)
            else:
                overflow.append(item)

            if len(selected) >= top_k:
                break

        if len(selected) < top_k:
            selected.extend(overflow[: top_k - len(selected)])

        return selected[:top_k]

    def similarity_search(
        self,
        query_embedding: Sequence[float],
        document_id: str | None = None,
        user_id: str | None = None,
        top_k: int = 8,
        filters: Mapping[str, Any] | None = None,
        exclude_noisy: bool = True,
    ) -> list[VectorSearchResult]:
        """Retrieve top_k chunks for a query embedding.

        By default excludes chunk_type in {toc, noisy} and use_for_generation=false
        so generation never has to see table-of-contents/junk chunks. Pass
        exclude_noisy=False for debug/review retrieval that wants everything.
        """
        if not document_id:
            raise ValueError("Chroma similarity_search requires document_id to avoid mixing documents.")

        extra_filters: dict[str, Any] = dict(filters or {})
        if exclude_noisy:
            extra_filters.setdefault("chunk_type", {"$nin": list(EXCLUDED_GENERATION_CHUNK_TYPES)})
            extra_filters.setdefault("use_for_generation", {"$ne": False})
        where = _where_filter(document_id=document_id, user_id=user_id, extra_filters=extra_filters)

        requested_k = max(1, int(top_k or 8))
        # Over-fetch when filtering so exclusion/dedupe/diversification still leave
        # enough usable chunks after trimming back down to requested_k.
        n_results = requested_k * 3 if exclude_noisy else requested_k
        query_kwargs: dict[str, Any] = {
            "query_embeddings": [[float(value) for value in query_embedding]],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_kwargs["where"] = where

        result = self.collection.query(**query_kwargs)
        documents = (result.get("documents") or [[]])[0] or []
        metadatas = (result.get("metadatas") or [[]])[0] or []
        distances = (result.get("distances") or [[]])[0] or []

        items: list[VectorSearchResult] = []
        for idx, text in enumerate(documents):
            metadata = dict(metadatas[idx] or {}) if idx < len(metadatas) else {}
            distance = float(distances[idx]) if idx < len(distances) and distances[idx] is not None else None
            raw_chunk_id = metadata.get("chunk_id")
            chunk_id = str(raw_chunk_id if raw_chunk_id is not None else idx)
            source_id = str(metadata.get("source_chunk_id") or _source_chunk_id(metadata, idx))
            score = 1.0 - distance if distance is not None else None
            items.append(
                VectorSearchResult(
                    chunk_id=chunk_id,
                    text=str(text or ""),
                    distance=distance,
                    score=score,
                    metadata=metadata,
                    source_chunk_id=source_id,
                )
            )

        if exclude_noisy and len(items) > requested_k:
            items = self._dedupe_and_diversify(items, requested_k)

        logger.info(
            "[Chroma] Retrieved %d chunks document_id=%s top_k=%d distances=%s",
            len(items),
            document_id or "*",
            n_results,
            [round(item.distance, 4) for item in items if item.distance is not None],
        )
        return items

    def get_document_chunks(self, document_id: str) -> list[VectorSearchResult]:
        result = self.collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"],
        )
        ids = result.get("ids") or []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        items: list[VectorSearchResult] = []
        for idx, text in enumerate(documents):
            metadata = dict(metadatas[idx] or {}) if idx < len(metadatas) else {}
            raw_chunk_id = metadata.get("chunk_id")
            if raw_chunk_id is None:
                raw_chunk_id = ids[idx] if idx < len(ids) else idx
            chunk_id = str(raw_chunk_id)
            source_id = str(metadata.get("source_chunk_id") or _source_chunk_id(metadata, idx))
            items.append(
                VectorSearchResult(
                    chunk_id=chunk_id,
                    text=str(text or ""),
                    metadata=metadata,
                    source_chunk_id=source_id,
                )
            )
        return items

    def delete_document(self, document_id: str) -> None:
        if not document_id:
            return
        try:
            if self.document_exists(document_id):
                self.collection.delete(where={"document_id": document_id})
                logger.info("[Chroma] Deleted chunks for document_id=%s", document_id)
        except Exception as exc:
            logger.warning("[Chroma] Could not delete document_id=%s: %s", document_id, exc)

    def document_exists(self, document_id: str) -> bool:
        if not document_id:
            return False
        result = self.collection.get(where={"document_id": document_id}, limit=1, include=["metadatas"])
        return bool(result.get("ids"))

    def count_chunks(self, document_id: str | None = None) -> int:
        if not document_id:
            return int(self.collection.count())
        result = self.collection.get(where={"document_id": document_id}, include=["metadatas"])
        return len(result.get("ids") or [])

    def copy_document(
        self, source_document_id: str, target_document_id: str, user_id: str | None = None
    ) -> int:
        """Copy stored chunks and embeddings between document IDs for file-hash cache hits.

        `user_id` overrides the copied metadata so a cache hit is tagged with the
        requesting user, not the original uploader's user_id.
        """
        result = self.collection.get(
            where={"document_id": source_document_id},
            include=["documents", "metadatas", "embeddings"],
        )
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        embeddings = result.get("embeddings")
        if not documents or embeddings is None:
            return 0

        copied_meta: list[dict[str, Any]] = []
        for idx, raw_meta in enumerate(metadatas):
            meta = dict(raw_meta or {})
            meta["document_id"] = target_document_id
            meta["cached_from"] = source_document_id
            meta["chunk_id"] = idx
            meta["source_chunk_id"] = _source_chunk_id(meta, idx)
            if user_id:
                meta["user_id"] = user_id
            else:
                meta.pop("user_id", None)
            copied_meta.append(meta)

        return self.add_chunks(target_document_id, documents, embeddings, copied_meta)

    def reset_collection(self) -> None:
        """Dev/debug only: drop and recreate the entire collection (all documents).

        Never call this from a normal user-facing flow (upload/generate/delete) —
        it destroys every course's vectors, not just one document's.
        """
        logger.warning(
            "[Chroma] RESET requested for collection '%s' — deleting all documents. Dev/debug only.",
            self.collection_name,
        )
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )


class ChromaCourseVectorStore:
    """LangChain-like adapter scoped to a single course/document."""

    def __init__(self, document_id: str, store: ChromaVectorStore | None = None):
        self.document_id = document_id
        self.store = store or ChromaVectorStore()
        self.embeddings = get_embeddings()

    def as_retriever(self, search_kwargs: Mapping[str, Any] | None = None):
        return _ChromaRetriever(self, dict(search_kwargs or {}))

    def get_document_chunks(self, document_id: str | None = None) -> list[VectorSearchResult]:
        """Delegate to the underlying Chroma store (used by the "Xem nguồn" grounding view)."""
        return self.store.get_document_chunks(document_id or self.document_id)


class _ChromaRetriever:
    """Small retriever shim compatible with ResourceGenerator usage."""

    def __init__(self, vectorstore: ChromaCourseVectorStore, search_kwargs: dict[str, Any]):
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


def create_or_load_chroma(
    course_id: str,
    source_paths: str | Sequence[str],
    on_progress: Callable[[int, int, str], None] | None = None,
    user_id: str | None = None,
) -> ChromaCourseVectorStore:
    """Create or load a Chroma-backed course vector store."""
    store = ChromaVectorStore()
    meta_path = _chroma_meta_path(course_id)
    if store.document_exists(course_id):
        logger.info("[Course %s] Found existing Chroma chunks, loading adapter...", course_id)
        if not os.path.exists(meta_path):
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "course_id": course_id,
                        "provider": "chroma",
                        "persist_dir": CHROMA_PERSIST_DIR,
                        "collection_name": CHROMA_COLLECTION_NAME,
                        "num_chunks": store.count_chunks(course_id),
                        "restored_from_chroma": True,
                        "created_at": time.time(),
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        return ChromaCourseVectorStore(course_id, store)

    paths = _coerce_source_paths(source_paths)
    if not paths:
        raise ValueError("No upload files were provided.")

    logger.info("[Course %s] Building new Chroma document from %s file(s)...", course_id, len(paths))
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
        # Most common cause: a scanned/image-only PDF on a machine without a working
        # OCR install. Fail with a friendly, actionable message instead of generating
        # anything from empty context (never hallucinate).
        raise ValueError(
            "Không trích xuất được văn bản từ tài liệu. File có thể là bản scan/ảnh — "
            "hệ thống cần OCR (Tesseract) để đọc loại file này. Hãy tải lên bản PDF có "
            "lớp văn bản, hoặc cài Tesseract OCR rồi thử lại."
        )

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
        if "page" not in doc.metadata:
            doc.metadata["page"] = idx // 5 + 1

        # Classify once at index time so retrieval can filter toc/noisy chunks via
        # Chroma metadata instead of re-classifying every chunk on every query.
        classification = classify_chunk(doc.page_content, chunk_id=f"chunk_{idx}", page=doc.metadata.get("page"))
        doc.metadata["chunk_type"] = classification["chunk_type"]
        doc.metadata["quality_score"] = classification["quality_score"]
        doc.metadata["use_for_generation"] = classification["use_for_generation"]
        if user_id:
            doc.metadata["user_id"] = user_id

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
        (
            "[Course %s] Embedding: %.2fs "
            "(requests=%d, api_batches=%d, cache_hits=%d, cache_misses=%d, retries=%d, throttle_sleep=%.2fs)"
        ),
        course_id,
        step_times["embedding"],
        embedding_stats.get("embedding_requests_sent", 0),
        embedding_stats.get("embedding_api_batches", 0),
        embedding_stats.get("embedding_cache_hits", 0),
        embedding_stats.get("embedding_cache_misses", 0),
        embedding_stats.get("embedding_retry_count", 0),
        embedding_stats.get("embedding_throttle_sleep_seconds", 0.0),
    )

    t_insert = time.perf_counter()
    if on_progress:
        on_progress(90, 100, "Dang luu chunks vao Chroma...")
    metadatas = [doc.metadata for doc in splits]
    inserted = store.add_chunks(course_id, texts, all_vectors, metadatas)
    step_times["chroma_insert"] = round(time.perf_counter() - t_insert, 2)
    step_times["vector_insert"] = step_times["chroma_insert"]
    total_time = round(time.perf_counter() - t_total, 2)

    os.makedirs(INDEX_DIR, exist_ok=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "course_id": course_id,
                "provider": "chroma",
                "persist_dir": CHROMA_PERSIST_DIR,
                "collection_name": CHROMA_COLLECTION_NAME,
                "user_id": user_id,
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
        (
            "[Course %s] Chroma document saved. Total: %.2fs "
            "(files=%d, size=%d bytes, pages=%d, chars=%d, chunks=%d, requests=%d, "
            "batches=%d, cache_hits=%d, retries=%d, extract=%.2fs, chunk=%.2fs, embed=%.2fs, insert=%.2fs)"
        ),
        course_id,
        total_time,
        len(paths),
        total_file_size_bytes,
        total_pages,
        total_extracted_chars,
        inserted,
        embedding_stats.get("embedding_requests_sent", len(texts)),
        embedding_stats.get("embedding_api_batches", (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE),
        embedding_stats.get("embedding_cache_hits", 0),
        embedding_stats.get("embedding_retry_count", 0),
        step_times.get("extract_text", 0),
        step_times.get("chunking", 0),
        step_times.get("embedding", 0),
        step_times.get("chroma_insert", 0),
    )
    return ChromaCourseVectorStore(course_id, store)


def load_existing_chroma(course_id: str) -> ChromaCourseVectorStore | None:
    """Load a Chroma document adapter if chunks exist."""
    try:
        store = ChromaVectorStore()
        if not store.document_exists(course_id):
            logger.warning("[Restore] Chroma document '%s' not found.", course_id)
            return None
        logger.info("[Restore] Loaded Chroma document '%s'.", course_id)
        return ChromaCourseVectorStore(course_id, store)
    except Exception as exc:
        logger.error("[Restore] Failed to load Chroma document '%s': %s", course_id, exc)
        return None


def list_chroma_courses() -> list[str]:
    """List course IDs with Chroma metadata."""
    courses: list[str] = []
    if not os.path.exists(INDEX_DIR):
        return courses
    for fname in os.listdir(INDEX_DIR):
        if fname.startswith("chroma_") and fname.endswith(".json"):
            courses.append(fname[len("chroma_") : -len(".json")])
    return sorted(courses)


def drop_chroma_index(course_id: str) -> None:
    """Delete a course from Chroma and remove its metadata file."""
    store = ChromaVectorStore()
    store.delete_document(course_id)
    meta_path = _chroma_meta_path(course_id)
    if os.path.exists(meta_path):
        os.remove(meta_path)


def get_chroma_index_stats(course_id: str) -> dict[str, Any]:
    """Return Chroma-backed preprocessing stats for one course."""
    meta_path = _chroma_meta_path(course_id)
    meta: dict[str, Any] = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    try:
        store = ChromaVectorStore()
        exists = store.document_exists(course_id)
        chunk_count = store.count_chunks(course_id) if exists else 0
    except Exception as exc:
        logger.warning("[Chroma] Stats check failed for '%s': %s", course_id, exc)
        exists = False
        chunk_count = 0

    return {
        "exists": exists,
        "provider": "chroma",
        "persist_dir": CHROMA_PERSIST_DIR,
        "collection_name": CHROMA_COLLECTION_NAME,
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


def copy_chroma_document(course_id: str, cached_course_id: str, user_id: str | None = None) -> bool:
    """Copy cached Chroma chunks to a new course ID."""
    store = ChromaVectorStore()
    copied = store.copy_document(cached_course_id, course_id, user_id=user_id)
    if copied <= 0:
        return False

    source_meta_path = _chroma_meta_path(cached_course_id)
    target_meta_path = _chroma_meta_path(course_id)
    meta: dict[str, Any] = {}
    if os.path.exists(source_meta_path):
        with open(source_meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    meta.update(
        {
            "course_id": course_id,
            "provider": "chroma",
            "cached_from": cached_course_id,
            "user_id": user_id,
            "num_chunks": copied,
            "persist_dir": CHROMA_PERSIST_DIR,
            "collection_name": CHROMA_COLLECTION_NAME,
        }
    )
    with open(target_meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    logger.info("[Chroma] Copied %d cached chunks from %s to %s", copied, cached_course_id, course_id)
    return True
