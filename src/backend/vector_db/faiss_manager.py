"""
FAISS vector store manager.
Local, disk-based, no Docker required.

Optimized:
- Batch embedding with rate-limit retry.
- Single FAISS.from_embeddings() call instead of incremental add_documents.
- Progress callback support for frontend tracking.
- Per-step timing logs.
"""
import os
import json
import re
import time
import hashlib
import threading
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Sequence

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from backend.core.config import (
    get_embeddings,
    INDEX_DIR,
    BATCH_SIZE,
    DOCUMENT_CHUNK_OVERLAP,
    DOCUMENT_CHUNK_SIZE,
    EMBEDDING_CACHE_DIR,
    EMBEDDING_MAX_RETRIES,
    EMBEDDING_MODEL,
    EMBEDDING_REQUESTS_PER_MINUTE,
    RETRY_DELAY,
    MAX_RETRY_DELAY,
    logger,
)

from backend.services.doc_processor import analyze_document_quality, get_text_from_any_file
from backend.services.cache import get_cache_provider


EMBEDDING_QUOTA_MESSAGE = (
    "Gemini embedding quota exceeded. Please wait and retry, use a smaller file, "
    "enable billing, or switch embedding provider."
)


class EmbeddingQuotaExceededError(RuntimeError):
    """Raised when Gemini embedding quota remains exhausted after bounded retries."""

    error_code = "EMBEDDING_QUOTA_EXCEEDED"


class _EmbeddingRateLimiter:
    """Process-wide limiter for embedding text requests, not only HTTP batch calls."""

    def __init__(self, max_requests_per_minute: int, window_seconds: float = 60.0):
        self.max_requests = max(1, int(max_requests_per_minute))
        self.window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def wait_for(self, request_count: int) -> float:
        """Reserve request_count slots and return total sleep seconds."""
        request_count = max(1, min(int(request_count), self.max_requests))
        slept = 0.0

        while True:
            with self._lock:
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] >= self.window_seconds:
                    self._timestamps.popleft()

                if len(self._timestamps) + request_count <= self.max_requests:
                    self._timestamps.extend([now] * request_count)
                    return slept

                oldest = self._timestamps[0]
                wait_time = max(0.1, self.window_seconds - (now - oldest) + 0.05)

            time.sleep(wait_time)
            slept += wait_time


_EMBEDDING_RATE_LIMITER = _EmbeddingRateLimiter(EMBEDDING_REQUESTS_PER_MINUTE)


def _index_path(course_id: str) -> str:
    """Path to FAISS index folder for a course."""
    return os.path.join(INDEX_DIR, f"faiss_{course_id}")


def _drop_index(course_id: str):
    """Remove FAISS index for a course."""
    path = _index_path(course_id)
    if os.path.exists(path):
        import shutil
        shutil.rmtree(path)
        logger.info(f"[FAISS] Dropped index '{path}'")


def _coerce_source_paths(source_paths: str | Sequence[str]) -> list[str]:
    """Normalize one or many upload paths into a non-empty list."""
    if isinstance(source_paths, str):
        paths = [source_paths]
    else:
        paths = [str(path) for path in source_paths]
    return [path for path in paths if path]


def _dedupe_splits(splits: list[Document]) -> list[Document]:
    """Remove empty or obviously repeated chunks while preserving order."""
    deduped: list[Document] = []
    seen: set[str] = set()
    for doc in splits:
        compact = " ".join(str(doc.page_content or "").split())
        if len(compact) < 30:
            continue
        signature = hashlib.sha1(compact.lower().encode("utf-8", errors="ignore")).hexdigest()
        if signature in seen:
            continue
        seen.add(signature)
        doc.page_content = compact
        deduped.append(doc)
    return deduped


def _is_quota_error(exc: Exception) -> bool:
    """Return True for Gemini quota/rate-limit errors from different client layers."""
    err_str = str(exc).lower()
    quota_markers = (
        "429",
        "resourceexhausted",
        "resource_exhausted",
        "quota exceeded",
        "rate limit",
        "embed_content_free_tier_requests",
        "embedcontentrequestsperminute",
    )
    return any(marker in err_str for marker in quota_markers)


def _extract_retry_delay_seconds(exc: Exception) -> Optional[float]:
    """Extract retry_delay seconds from Gemini/gRPC error payloads when present."""
    for attr_name in ("retry_delay", "retry_delay_seconds"):
        retry_delay = getattr(exc, attr_name, None)
        if retry_delay is None:
            continue
        if isinstance(retry_delay, (int, float)):
            return float(retry_delay)
        seconds = getattr(retry_delay, "seconds", None)
        if seconds is not None:
            return float(seconds)

    err_str = str(exc)
    patterns = (
        r"retry_delay\s*\{\s*seconds:\s*(\d+(?:\.\d+)?)",
        r"retry[_\s-]?delay[\"']?\s*[:=]\s*[\"']?(\d+(?:\.\d+)?)s?",
        r"Please retry in\s+(\d+(?:\.\d+)?)s",
    )
    for pattern in patterns:
        match = re.search(pattern, err_str, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _embedding_cache_key(text: str) -> str:
    """Stable cache key for a normalized chunk body."""
    normalized = " ".join((text or "").split())
    return hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()


def _embedding_cache_path(cache_key: str) -> str:
    """Model-scoped embedding cache path."""
    model_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", EMBEDDING_MODEL).strip("_") or "embedding_model"
    return os.path.join(EMBEDDING_CACHE_DIR, model_key, cache_key[:2], f"{cache_key}.json")


def _load_cached_embedding(cache_key: str) -> Optional[list[float]]:
    """Load one cached embedding vector if it matches the active model."""
    try:
        vector = get_cache_provider().get_embedding(cache_key, EMBEDDING_MODEL)
        if vector:
            return vector
    except Exception as exc:
        logger.warning("[Embedding Cache] Cache provider read failed for %s: %s", cache_key, exc)

    path = _embedding_cache_path(cache_key)
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if payload.get("model") != EMBEDDING_MODEL:
            return None
        vector = payload.get("vector")
        if not isinstance(vector, list) or not vector:
            return None
        return [float(value) for value in vector]
    except Exception as exc:
        logger.warning("[Embedding Cache] Ignoring unreadable cache entry %s: %s", path, exc)
        return None


def _save_cached_embedding(cache_key: str, vector: list[float]) -> None:
    """Persist one chunk embedding for reuse across uploads."""
    try:
        get_cache_provider().set_embedding(cache_key, EMBEDDING_MODEL, vector)
        return
    except Exception as exc:
        logger.warning("[Embedding Cache] Cache provider write failed for %s: %s", cache_key, exc)

    path = _embedding_cache_path(cache_key)
    tmp_path = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "model": EMBEDDING_MODEL,
                    "hash": cache_key,
                    "dimension": len(vector),
                    "created_at": time.time(),
                    "vector": vector,
                },
                f,
            )
        os.replace(tmp_path, path)
    except Exception as exc:
        logger.warning("[Embedding Cache] Could not save cache entry %s: %s", path, exc)
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def _add_stat(stats: Optional[dict[str, Any]], key: str, value: int | float) -> None:
    if stats is not None:
        stats[key] = stats.get(key, 0) + value


def _batch_embed_texts_legacy(
    texts: list[str],
    embeddings_model,
    batch_size: int = 100,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> list[list[float]]:
    """Embed texts in batches with rate-limit retry.

    Returns a flat list of embedding vectors, one per input text.
    """
    all_vectors: list[list[float]] = []
    total = len(texts)

    for i in range(0, total, batch_size):
        batch = texts[i : i + batch_size]
        end_idx = min(i + batch_size, total)

        if on_progress:
            pct = int((i / total) * 100)
            on_progress(i, total, f"Đang tạo vector {i+1}-{end_idx}/{total} ({pct}%)")

        batch_t0 = time.perf_counter()
        logger.info(" -> Embedding batch %d-%d / %d", i + 1, end_idx, total)

        retries = 0
        while True:
            try:
                vectors = embeddings_model.embed_documents(batch)
                if len(vectors) != len(batch):
                    raise RuntimeError(
                        f"Embedding API returned {len(vectors)} vectors for {len(batch)} chunks."
                    )
                all_vectors.extend(vectors)
                logger.info(
                    " -> Embedding batch %d-%d / %d completed in %.2fs",
                    i + 1, end_idx, total, time.perf_counter() - batch_t0,
                )
                break
            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "ResourceExhausted" in err_str) and retries < EMBEDDING_MAX_RETRIES:
                    wait_time = min(MAX_RETRY_DELAY, max(2.0, RETRY_DELAY or 0.0) * (2 ** retries))
                    logger.warning(
                        " -> Rate limited on batch %d-%d. Waiting %ds (retry %d)...",
                        i + 1, end_idx, wait_time, retries + 1,
                    )
                    time.sleep(wait_time)
                    retries += 1
                else:
                    raise

        if end_idx < total and RETRY_DELAY > 0:
            time.sleep(RETRY_DELAY)

    if on_progress:
        on_progress(total, total, f"Hoàn thành tạo {total} vectors")

    return all_vectors


def _batch_embed_texts(
    texts: list[str],
    embeddings_model,
    batch_size: int = BATCH_SIZE,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    stats: Optional[dict[str, Any]] = None,
) -> list[list[float]]:
    """Embed texts in batches with cache, throttling, and bounded quota retry."""
    total = len(texts)
    if total == 0:
        return []

    all_vectors: list[Optional[list[float]]] = [None] * total
    misses_by_hash: dict[str, dict[str, Any]] = {}
    cache_hits = 0
    duplicate_hits = 0

    for index, text in enumerate(texts):
        cache_key = _embedding_cache_key(text)
        cached = _load_cached_embedding(cache_key)
        if cached is not None:
            all_vectors[index] = cached
            cache_hits += 1
            continue

        existing = misses_by_hash.get(cache_key)
        if existing:
            existing["indices"].append(index)
            duplicate_hits += 1
        else:
            misses_by_hash[cache_key] = {
                "hash": cache_key,
                "text": text,
                "indices": [index],
            }

    miss_entries = list(misses_by_hash.values())
    cache_misses = len(miss_entries)
    effective_batch_size = max(1, min(int(batch_size or 1), max(1, EMBEDDING_REQUESTS_PER_MINUTE)))

    if stats is not None:
        stats.update(
            {
                "embedding_total_chunks": total,
                "embedding_cache_hits": cache_hits,
                "embedding_cache_misses": cache_misses,
                "embedding_duplicate_hits": duplicate_hits,
                "embedding_requests_sent": cache_misses,
                "embedding_api_batches": 0,
                "embedding_retry_count": 0,
                "embedding_throttle_sleep_seconds": 0.0,
                "embedding_rate_limit_per_minute": EMBEDDING_REQUESTS_PER_MINUTE,
                "embedding_effective_batch_size": effective_batch_size,
            }
        )

    logger.info(
        (
            " -> Embedding plan: chunks=%d, cache_hits=%d, cache_misses=%d, "
            "duplicate_hits=%d, batch_size=%d, rpm_limit=%d"
        ),
        total,
        cache_hits,
        cache_misses,
        duplicate_hits,
        effective_batch_size,
        EMBEDDING_REQUESTS_PER_MINUTE,
    )

    if not miss_entries:
        if on_progress:
            on_progress(total, total, f"Reused {total} cached vectors")
        return [vector for vector in all_vectors if vector is not None]

    embedded_count = cache_hits
    for i in range(0, cache_misses, effective_batch_size):
        entries = miss_entries[i : i + effective_batch_size]
        batch = [str(entry["text"]) for entry in entries]
        end_idx = min(i + effective_batch_size, cache_misses)

        if on_progress:
            current = min(total, embedded_count)
            pct = int((current / total) * 100)
            on_progress(
                current,
                total,
                f"Embedding vectors {current + 1}-{min(total, current + len(batch))}/{total} ({pct}%)",
            )

        batch_t0 = time.perf_counter()
        logger.info(" -> Embedding batch %d-%d / %d uncached chunks", i + 1, end_idx, cache_misses)

        retries = 0
        while True:
            try:
                throttle_sleep = _EMBEDDING_RATE_LIMITER.wait_for(len(batch))
                if throttle_sleep > 0:
                    _add_stat(stats, "embedding_throttle_sleep_seconds", round(throttle_sleep, 2))
                    logger.info(
                        " -> Embedding throttle slept %.2fs before batch %d-%d / %d",
                        throttle_sleep,
                        i + 1,
                        end_idx,
                        cache_misses,
                    )
                vectors = embeddings_model.embed_documents(batch)
                if len(vectors) != len(batch):
                    raise RuntimeError(
                        f"Embedding API returned {len(vectors)} vectors for {len(batch)} chunks."
                    )
                _add_stat(stats, "embedding_api_batches", 1)
                for entry, vector in zip(entries, vectors):
                    vector_list = [float(value) for value in vector]
                    _save_cached_embedding(str(entry["hash"]), vector_list)
                    for output_index in entry["indices"]:
                        all_vectors[int(output_index)] = vector_list
                embedded_count += sum(len(entry["indices"]) for entry in entries)
                logger.info(
                    " -> Embedding batch %d-%d / %d completed in %.2fs",
                    i + 1,
                    end_idx,
                    cache_misses,
                    time.perf_counter() - batch_t0,
                )
                break
            except Exception as e:
                if _is_quota_error(e) and retries < EMBEDDING_MAX_RETRIES:
                    retry_delay = _extract_retry_delay_seconds(e)
                    exponential_delay = max(2.0, RETRY_DELAY or 0.0) * (2 ** retries)
                    wait_time = min(MAX_RETRY_DELAY, max(retry_delay or 0.0, exponential_delay))
                    _add_stat(stats, "embedding_retry_count", 1)
                    logger.warning(
                        " -> Gemini embedding quota hit on batch %d-%d. Waiting %.1fs (retry %d/%d)...",
                        i + 1,
                        end_idx,
                        wait_time,
                        retries + 1,
                        EMBEDDING_MAX_RETRIES,
                    )
                    time.sleep(wait_time)
                    retries += 1
                elif _is_quota_error(e):
                    logger.error(
                        " -> Gemini embedding quota exhausted after %d retries on batch %d-%d.",
                        EMBEDDING_MAX_RETRIES,
                        i + 1,
                        end_idx,
                    )
                    raise EmbeddingQuotaExceededError(EMBEDDING_QUOTA_MESSAGE) from e
                else:
                    raise

        if end_idx < cache_misses and RETRY_DELAY > 0:
            time.sleep(RETRY_DELAY)

    if on_progress:
        on_progress(total, total, f"Completed {total} vectors")

    missing_indices = [index for index, vector in enumerate(all_vectors) if vector is None]
    if missing_indices:
        raise RuntimeError(f"Embedding pipeline missed {len(missing_indices)} vectors.")

    return [vector for vector in all_vectors if vector is not None]


def create_or_load_faiss(
    course_id: str,
    source_paths: str | Sequence[str],
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> FAISS:
    """
    Create a new FAISS vector store from a document, or load an existing one.

    Args:
        course_id: Unique course identifier.
        source_paths: Path or paths to PDF/DOCX/TXT files.
        on_progress: Optional callback(current, total, message) for progress.

    Returns:
        FAISS vector store instance.
    """
    index_path = _index_path(course_id)

    # Load existing index if available
    if os.path.exists(index_path) and os.path.exists(os.path.join(index_path, "index.faiss")):
        logger.info(f"[Course {course_id}] Found existing FAISS index, loading...")
        return FAISS.load_local(
            index_path,
            get_embeddings(),
            allow_dangerous_deserialization=True,
        )

    paths = _coerce_source_paths(source_paths)
    if not paths:
        raise ValueError("No upload files were provided.")

    logger.info("[Course %s] Building new FAISS index from %s file(s)...", course_id, len(paths))
    step_times: dict[str, float] = {}
    t_total = time.perf_counter()

    # ── Step 1: Extract text from documents ─────────────────────────────────
    t_extract = time.perf_counter()
    if on_progress:
        on_progress(0, 100, "Đang trích xuất văn bản...")

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
                # Scale within 0-30% range for extraction
                file_pct = (doc_index / len(paths)) * 30
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

    # ── Step 2: Chunk documents ──────────────────────────────────────────────
    t_chunk = time.perf_counter()
    if on_progress:
        on_progress(30, 100, "Đang phân mảnh tài liệu...")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=DOCUMENT_CHUNK_SIZE,
        chunk_overlap=DOCUMENT_CHUNK_OVERLAP,
        separators=[
            "\n# ",
            "\n## ",
            "\n### ",
            "\nChương ",
            "\nBài ",
            "\n\n",
            "\n",
            ". ",
            " ",
            "",
        ],
    )
    raw_splits = text_splitter.split_documents(valid_docs)
    chunks_before_filter = len(raw_splits)
    splits = _dedupe_splits(raw_splits)
    num_chunks = len(splits)
    if num_chunks == 0:
        raise ValueError("File contains no usable text chunks after preprocessing.")
    logger.info(
        "[Course %s] Split into %d chunks before filtering, %d chunks after filtering.",
        course_id,
        chunks_before_filter,
        num_chunks,
    )
    logger.info(
        "[Course %s] Chunk config: chunk_size=%d, overlap=%d",
        course_id,
        DOCUMENT_CHUNK_SIZE,
        DOCUMENT_CHUNK_OVERLAP,
    )

    # Add internal source metadata for retrieval and debugging.
    for idx, doc in enumerate(splits):
        doc.metadata["chunk_id"] = idx
        doc.metadata["course_id"] = course_id
        doc.metadata.setdefault("source_file", os.path.basename(paths[0]))
        if "page" not in doc.metadata:
            doc.metadata["page"] = idx // 5 + 1  # Approximate page mapping

    step_times["chunking"] = round(time.perf_counter() - t_chunk, 2)
    logger.info("[Course %s] Chunking: %.2fs", course_id, step_times["chunking"])

    # ── Step 3: Batch embed all chunks ───────────────────────────────────────
    t_embed = time.perf_counter()
    if on_progress:
        on_progress(35, 100, "Đang tạo vector chỉ mục...")

    embeddings_model = get_embeddings()
    texts = [doc.page_content for doc in splits]
    embedding_stats: dict[str, Any] = {}

    def _embed_progress(current, total, message):
        if on_progress:
            # Scale within 35-90% range for embedding
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

    # ── Step 4: Build FAISS index in one shot ────────────────────────────────
    t_index = time.perf_counter()
    if on_progress:
        on_progress(90, 100, "Đang lưu chỉ mục FAISS...")

    text_embedding_pairs = list(zip(texts, all_vectors))
    metadatas = [doc.metadata for doc in splits]

    vectorstore = FAISS.from_embeddings(
        text_embeddings=text_embedding_pairs,
        embedding=embeddings_model,
        metadatas=metadatas,
    )

    # Persist to disk
    os.makedirs(index_path, exist_ok=True)
    vectorstore.save_local(index_path)

    step_times["faiss_index"] = round(time.perf_counter() - t_index, 2)
    step_times["vector_insert"] = step_times["faiss_index"]
    logger.info("[Course %s] FAISS indexing: %.2fs", course_id, step_times["faiss_index"])
    total_time = round(time.perf_counter() - t_total, 2)

    # Save metadata
    meta_path = os.path.join(INDEX_DIR, f"faiss_{course_id}.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "course_id": course_id,
            "index_path": index_path,
            "num_chunks": num_chunks,
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
        }, f, indent=2)

    if on_progress:
        on_progress(100, 100, "Hoàn thành!")

    logger.info(
        (
            "[Course %s] FAISS index saved to '%s'. Total: %.2fs "
            "(files=%d, size=%d bytes, pages=%d, chars=%d, chunks=%d, requests=%d, "
            "batches=%d, cache_hits=%d, retries=%d, extract=%.2fs, chunk=%.2fs, embed=%.2fs, index=%.2fs)"
        ),
        course_id, index_path, total_time,
        len(paths),
        total_file_size_bytes,
        total_pages,
        total_extracted_chars,
        num_chunks,
        embedding_stats.get("embedding_requests_sent", len(texts)),
        embedding_stats.get("embedding_api_batches", (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE),
        embedding_stats.get("embedding_cache_hits", 0),
        embedding_stats.get("embedding_retry_count", 0),
        step_times.get("extract_text", 0),
        step_times.get("chunking", 0),
        step_times.get("embedding", 0),
        step_times.get("faiss_index", 0),
    )
    return vectorstore


def load_existing_faiss(course_id: str) -> Optional[FAISS]:
    """Load existing FAISS index for a course if it exists."""
    index_path = _index_path(course_id)
    try:
        if not os.path.exists(os.path.join(index_path, "index.faiss")):
            logger.warning(f"[Restore] FAISS index for '{course_id}' not found.")
            return None
        vs = FAISS.load_local(
            index_path,
            get_embeddings(),
            allow_dangerous_deserialization=True,
        )
        logger.info(f"[Restore] Loaded FAISS index for '{course_id}'.")
        return vs
    except Exception as e:
        logger.error(f"[Restore] Failed to load FAISS index: {e}")
        return None


def list_faiss_courses() -> List[str]:
    """List all course IDs that have FAISS indices."""
    courses = []
    if not os.path.exists(INDEX_DIR):
        return courses
    for fname in os.listdir(INDEX_DIR):
        if fname.startswith("faiss_") and fname.endswith(".json"):
            course_id = fname[len("faiss_"):-len(".json")]
            courses.append(course_id)
    return sorted(courses)


def get_index_stats(course_id: str) -> Dict[str, Any]:
    """Get statistics about a FAISS index."""
    index_path = _index_path(course_id)
    meta_path = os.path.join(INDEX_DIR, f"faiss_{course_id}.json")
    if not os.path.exists(os.path.join(index_path, "index.faiss")):
        return {"exists": False}
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    return {
        "exists": True,
        "index_path": index_path,
        "num_chunks": meta.get("num_chunks"),
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
