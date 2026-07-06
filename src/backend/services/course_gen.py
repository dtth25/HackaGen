"""Course lifecycle and vectorstore management for the four-output generator."""

import gc
import json
import os
import shutil
import threading
import time
from collections import OrderedDict
from typing import Any, Optional, Sequence
import hashlib

from backend.core.config import DEFAULT_MAX_CACHED_COURSES, generate_course_id, get_course_path, logger
from backend.vector_db.faiss_manager import (
    EmbeddingQuotaExceededError,
)
from backend.vector_db.manager import (
    copy_vector_index,
    create_or_load_vectorstore,
    drop_vector_index,
    get_index_stats,
    list_vector_courses,
    load_existing_vectorstore,
)

_HASH_LOCK = threading.Lock()
_IN_FLIGHT_HASHES: dict[str, str] = {}


def _compute_file_sha256(file_path: str) -> str:
    """Compute SHA256 hash of a file for cache deduplication."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _compute_combined_hash(file_paths: list[str]) -> str:
    """Compute a combined SHA256 hash for a set of files."""
    individual = sorted(_compute_file_sha256(p) for p in file_paths)
    return hashlib.sha256("|".join(individual).encode()).hexdigest()


def _load_hash_cache() -> dict:
    """Load the file hash cache from disk."""
    from backend.services.cache import get_cache_provider

    cache_data = get_cache_provider().get("document_hashes", {})
    return cache_data if isinstance(cache_data, dict) else {}


def _save_hash_cache(cache: dict) -> None:
    """Save the file hash cache to disk."""
    from backend.services.cache import get_cache_provider

    get_cache_provider().set("document_hashes", cache)


def _remove_hash_cache_refs(course_id: str) -> int:
    """Remove file-hash cache entries that point to a deleted document."""
    cache = _load_hash_cache()
    if not cache:
        return 0
    stale_hashes = [file_hash for file_hash, cached_id in cache.items() if cached_id == course_id]
    for file_hash in stale_hashes:
        cache.pop(file_hash, None)
    if stale_hashes:
        _save_hash_cache(cache)
    return len(stale_hashes)


def _update_meta(course_id: str, updates: dict) -> None:
    """Thread-safe update of course metadata JSON file."""
    meta_path = get_course_path(course_id)["meta"]
    try:
        with open(meta_path, "r+", encoding="utf-8") as f:
            meta = json.load(f)
            meta.update(updates)
            f.seek(0)
            json.dump(meta, f, ensure_ascii=False, indent=2)
            f.truncate()
    except Exception:
        pass


def _stage_from_progress(progress: int) -> str:
    """Map numeric preprocessing progress to a stable public stage."""
    if progress >= 100:
        return "completed"
    if progress >= 90:
        return "storing_vectors"
    if progress >= 35:
        return "embedding"
    if progress >= 30:
        return "chunking"
    return "extracting_text"


def _is_embedding_quota_error(exc: Exception) -> bool:
    """Detect Gemini embedding quota errors without leaking provider stack traces."""
    if isinstance(exc, EmbeddingQuotaExceededError):
        return True
    err_str = str(exc).lower()
    quota_markers = (
        "429",
        "resourceexhausted",
        "resource_exhausted",
        "quota exceeded",
        "embed_content_free_tier_requests",
        "embedcontentrequestsperminute",
    )
    return any(marker in err_str for marker in quota_markers)


def _public_processing_error(exc: Exception) -> tuple[str, str | None]:
    """Return a safe public error message and optional machine-readable code."""
    if _is_embedding_quota_error(exc):
        return (
            "Gemini embedding quota exceeded. Please wait and retry, use a smaller file, "
            "enable billing, or switch embedding provider.",
            "EMBEDDING_QUOTA_EXCEEDED",
        )
    return (str(exc), getattr(exc, "error_code", None))


def _safe_error_text(exc: Exception, limit: int = 1000) -> str:
    """Return compact developer details without stack traces or secrets."""
    raw = f"{type(exc).__name__}: {exc}"
    redacted = raw
    for marker in ("GOOGLE_API_KEY=", "GEMINI_API_KEY=", "OPENAI_API_KEY="):
        redacted = redacted.replace(marker, f"{marker}[redacted]")
    return redacted[:limit]


def _read_meta_stage(course_id: str) -> str:
    """Best-effort read of the latest public processing stage."""
    meta_path = get_course_path(course_id)["meta"]
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return str(meta.get("stage") or "")
    except Exception:
        return ""


def _structured_processing_error(course_id: str, exc: Exception) -> dict[str, Any]:
    """Classify preprocess failures into user-facing and developer-facing fields."""
    public_error, error_code = _public_processing_error(exc)
    err_text = str(exc)
    err_lower = err_text.lower()
    current_stage = _read_meta_stage(course_id)

    if _is_embedding_quota_error(exc):
        stage = "embedding_failed"
        user_message = (
            "Gemini API đã vượt giới hạn embedding tạm thời. Vui lòng chờ khoảng 1 phút rồi thử lại "
            "hoặc dùng file nhỏ hơn."
        )
        recommended_action = "wait_for_quota"
        can_retry = True
        status = "paused_due_to_quota"
        error_code = error_code or "EMBEDDING_QUOTA_EXCEEDED"
    elif "api key" in err_lower or "google_api_key" in err_lower or "gemini" in err_lower and "key" in err_lower:
        stage = "embedding_failed"
        user_message = "Thiếu hoặc sai Gemini API key nên hệ thống chưa tạo được embedding."
        recommended_action = "check_api_key"
        can_retry = True
        status = "failed"
        error_code = error_code or "EMBEDDING_API_KEY_MISSING"
    elif isinstance(exc, FileNotFoundError) or "file not found" in err_lower or "no such file" in err_lower:
        stage = "extraction_failed"
        user_message = "Không tìm thấy file đã upload. Vui lòng thử upload lại tài liệu."
        recommended_action = "retry"
        can_retry = False
        status = "failed"
        error_code = error_code or "UPLOAD_FILE_NOT_FOUND"
    elif "no upload files" in err_lower:
        stage = "extraction_failed"
        user_message = "Không tìm thấy file để phân tích. Vui lòng upload lại tài liệu."
        recommended_action = "retry"
        can_retry = False
        status = "failed"
        error_code = error_code or "UPLOAD_FILE_NOT_FOUND"
    elif "không trích xuất" in err_lower or "no readable text" in err_lower or "scan" in err_lower:
        stage = "extraction_failed"
        user_message = (
            "PDF này có vẻ là bản scan/ảnh hoặc không có lớp text đủ rõ. Vui lòng bật OCR "
            "hoặc tải bản PDF có text rõ hơn."
        )
        recommended_action = "upload_clearer_pdf"
        can_retry = True
        status = "failed"
        error_code = error_code or "PDF_TEXT_EXTRACTION_FAILED"
    elif "no usable text chunks" in err_lower or "usable text chunks" in err_lower:
        stage = "insufficient_context"
        user_message = (
            "Tài liệu có quá ít nội dung đọc được để tạo Study Pack đầy đủ. Hãy thử file rõ hơn "
            "hoặc tài liệu có nhiều text hơn."
        )
        recommended_action = "upload_clearer_pdf"
        can_retry = True
        status = "failed"
        error_code = error_code or "INSUFFICIENT_CONTEXT"
    elif "chroma" in err_lower or "vector" in err_lower or current_stage == "storing_vectors":
        stage = "vector_index_failed"
        user_message = "Không thể lưu vector vào Chroma. Vui lòng kiểm tra cấu hình Chroma hoặc khởi động lại backend."
        recommended_action = "check_chroma"
        can_retry = True
        status = "failed"
        error_code = error_code or "CHROMA_INDEX_FAILED"
    elif any(marker in err_lower for marker in (
        "getaddrinfo", "no such host", "wsa error", "errors resolving",
        "name or service not known", "address lookup failed",
        "network is unreachable", "connection refused", "connection reset",
    )):
        # DNS/network failure reaching Gemini — nothing wrong with the document
        # or the API key; the machine had no route to googleapis.com.
        stage = "embedding_failed"
        user_message = (
            "Không kết nối được tới máy chủ Gemini (lỗi mạng/DNS). "
            "Hãy kiểm tra Internet, VPN hoặc firewall của máy rồi bấm 'Thử phân tích lại'."
        )
        recommended_action = "check_network"
        can_retry = True
        status = "failed"
        error_code = error_code or "NETWORK_UNAVAILABLE"
    elif current_stage == "embedding":
        stage = "embedding_failed"
        user_message = "Không thể tạo embedding cho tài liệu. Vui lòng thử lại hoặc kiểm tra cấu hình Gemini."
        recommended_action = "retry"
        can_retry = True
        status = "failed"
        error_code = error_code or "EMBEDDING_FAILED"
    else:
        stage = "analysis_failed"
        user_message = "Không thể phân tích tài liệu này. Vui lòng thử lại hoặc dùng file PDF/DOCX/TXT rõ hơn."
        recommended_action = "retry"
        can_retry = True
        status = "failed"
        error_code = error_code or "DOCUMENT_ANALYSIS_FAILED"

    return {
        "status": status,
        "stage": stage,
        "user_message": user_message,
        "technical_error": _safe_error_text(exc),
        "can_retry": can_retry,
        "recommended_action": recommended_action,
        "error_code": error_code,
        "raw_error": public_error,
    }


def _is_limited_document_quality(report: dict[str, Any] | None) -> bool:
    """Return True when indexing succeeded but generation should be presented as limited."""
    if not isinstance(report, dict):
        return False
    readiness = str(report.get("generation_readiness") or "").lower()
    if readiness in {"limited", "summary_only", "insufficient", "needs_ocr"}:
        return True
    quality = report.get("quality_score")
    return isinstance(quality, (int, float)) and quality < 50


def _coerce_source_paths(source_paths: str | Sequence[str]) -> list[str]:
    """Normalize one or many upload paths."""
    if isinstance(source_paths, str):
        paths = [source_paths]
    else:
        paths = [str(path) for path in source_paths]
    return [path for path in paths if path]


class RAGChains:
    """Per-course container for the vectorstore used by Book, Slide, Quiz, and Vid."""

    def __init__(self, course_id: str, source_path: str | Sequence[str]):
        self.course_id = course_id
        self.source_paths = _coerce_source_paths(source_path)
        self.source_path = self.source_paths[0] if self.source_paths else ""
        self.vectorstore: Optional[Any] = None
        self.index_meta_path = get_course_path(course_id)["vector_meta"]

    def get_resource_generator(self):
        """Create a ResourceGenerator for this course."""
        from backend.services.resource_gen import ResourceGenerator

        return ResourceGenerator(self)

    def initialise_chains_only(self) -> "RAGChains":
        """Validate that the vectorstore is loaded."""
        if self.vectorstore is None:
            raise ValueError("vectorstore must be set before initialising a course.")
        return self

    def initialise(self) -> "RAGChains":
        """Create or load the course vectorstore."""
        self.vectorstore = create_or_load_vectorstore(self.course_id, self.source_paths or self.source_path)
        return self.initialise_chains_only()

    def _load_existing_vectorstore(self) -> Optional[Any]:
        """Load an existing vector store from disk."""
        return load_existing_vectorstore(self.course_id)


class CourseManager:
    """Multi-course manager with lazy loading and LRU eviction."""

    def __init__(self, max_cached: int = DEFAULT_MAX_CACHED_COURSES):
        self._courses: dict[str, RAGChains] = {}
        self._lock = threading.Lock()
        self._max_cached = max_cached
        self._all_course_ids: set[str] = set()
        self._lru: OrderedDict[str, None] = OrderedDict()
        self._scan_existing_courses()

    def _scan_existing_courses(self) -> None:
        """Register course IDs that already have vector metadata on disk."""
        try:
            found = 0
            for course_id in list_vector_courses():
                self._all_course_ids.add(course_id)
                found += 1

            if found:
                logger.info(
                    "[LazyLoad] Registered %s courses from vector DB metadata. Max cache: %s.",
                    found,
                    self._max_cached,
                )
        except Exception as exc:
            logger.warning("[LazyLoad] Could not scan vector DB metadata: %s", exc)

    def _evict_lru_course(self) -> None:
        """Evict the least recently used course from memory."""
        if not self._lru:
            return

        evict_id = next(iter(self._lru))
        del self._lru[evict_id]
        self._courses.pop(evict_id, None)
        logger.info("[LRU] Evicted course '%s' from cache.", evict_id)
        gc.collect()

    def _ensure_course_loaded(self, course_id: str) -> Optional[RAGChains]:
        """Lazy-load a course into memory if it is registered."""
        with self._lock:
            if course_id in self._courses:
                if course_id in self._lru:
                    self._lru.move_to_end(course_id, last=True)
                else:
                    self._lru[course_id] = None
                return self._courses[course_id]

            if course_id not in self._all_course_ids:
                return None

            source_paths: list[str] = []
            meta_path = get_course_path(course_id)["meta"]
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        raw_paths = meta.get("source_paths") or meta.get("source_path") or meta.get("pdf_path") or []
                        source_paths = _coerce_source_paths(raw_paths)
                except Exception:
                    source_paths = []

            while len(self._courses) >= self._max_cached:
                self._evict_lru_course()

            try:
                rag = RAGChains(course_id, source_paths)
                rag.vectorstore = rag._load_existing_vectorstore()
                if rag.vectorstore is None:
                    logger.warning("[LazyLoad] Course '%s' has no valid vector store.", course_id)
                    return None
                rag.initialise_chains_only()
                self._courses[course_id] = rag
                self._lru[course_id] = None
                return rag
            except Exception as exc:
                logger.error("[LazyLoad] Failed to load course '%s': %s", course_id, exc)
                return None

    def register_course_id(self, course_id: str, source_path: str | Sequence[str], user_id: Optional[str] = None) -> None:
        """Register a course before background document processing starts."""
        source_paths = _coerce_source_paths(source_path)
        self._all_course_ids.add(course_id)
        paths = get_course_path(course_id)
        with open(paths["meta"], "w", encoding="utf-8") as f:
            json.dump(
                {
                    "course_id": course_id,
                    "user_id": user_id,
                    "source_path": source_paths[0] if source_paths else "",
                    "source_paths": source_paths,
                    "pdf_path": source_paths[0] if source_paths else "",
                    "filenames": [os.path.basename(path) for path in source_paths],
                    "file_count": len(source_paths),
                    "status": "pending",
                    "stage": "uploading",
                    "created_at": time.time(),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        logger.info("[Register] Registered course '%s' (user_id=%s).", course_id, user_id)

    def _restore_from_cached_course(
        self,
        course_id: str,
        source_paths: list[str],
        cached_course_id: str,
        combined_hash: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """Copy existing vector data into a new course and load it into memory."""
        if not copy_vector_index(course_id, cached_course_id, user_id=user_id):
            return False

        logger.info(
            "[Cache HIT] course '%s' matches cached '%s' (hash=%s)",
            course_id,
            cached_course_id,
            combined_hash[:12],
        )
        _update_meta(
            course_id,
            {
                "status": "processing",
                "stage": "storing_vectors",
                "progress": 50,
                "progress_message": "Tìm thấy bản cache, đang sao chép chỉ mục...",
            },
        )

        rag = RAGChains(course_id, source_paths)
        rag.vectorstore = rag._load_existing_vectorstore()
        if rag.vectorstore is None:
            return False

        rag.initialise_chains_only()
        with self._lock:
            self._courses[course_id] = rag
            self._lru[course_id] = None
            self._all_course_ids.add(course_id)

        _update_meta(
            course_id,
            {
                "status": "ready",
                "stage": "completed",
                "ready_at": time.time(),
                "progress": 100,
                "progress_message": "Hoàn thành (từ cache)!",
                "cached_from": cached_course_id,
                "file_hash": combined_hash,
            },
        )
        logger.info("[Cache HIT] Course '%s' ready from cache.", course_id)
        return True

    def process_new_course(
        self, course_id: str, source_path: str | Sequence[str], user_id: Optional[str] = None
    ) -> None:
        """Parse, chunk, embed, and index a newly uploaded document.

        Includes SHA256 cache check, progress tracking, and per-step timing.
        """
        combined_hash: str | None = None
        owns_inflight_hash = False
        try:
            source_paths = _coerce_source_paths(source_path)

            _update_meta(course_id, {
                "status": "processing",
                "stage": "extracting_text",
                "processing_started_at": time.time(),
                "progress": 0,
                "progress_message": "Đang chuẩn bị...",
            })

            combined_hash = _compute_combined_hash(source_paths)
            cache = _load_hash_cache()
            cached_course_id = cache.get(combined_hash)

            if cached_course_id and cached_course_id != course_id:
                if self._restore_from_cached_course(course_id, source_paths, cached_course_id, combined_hash, user_id=user_id):
                    return

            duplicate_course_id: str | None = None
            with _HASH_LOCK:
                current_owner = _IN_FLIGHT_HASHES.get(combined_hash)
                if current_owner and current_owner != course_id:
                    duplicate_course_id = current_owner
                else:
                    _IN_FLIGHT_HASHES[combined_hash] = course_id
                    owns_inflight_hash = True

            if duplicate_course_id:
                logger.info(
                    "[Cache WAIT] course '%s' waits for in-flight course '%s' (hash=%s)",
                    course_id,
                    duplicate_course_id,
                    combined_hash[:12],
                )
                _update_meta(
                    course_id,
                    {
                        "status": "processing",
                        "stage": "extracting_text",
                        "progress": 5,
                        "progress_message": "File này đang được xử lý ở request khác, đang chờ cache...",
                        "waiting_for_course": duplicate_course_id,
                    },
                )
                wait_started = time.time()
                while time.time() - wait_started < 1800:
                    duplicate_meta_path = get_course_path(duplicate_course_id)["meta"]
                    duplicate_status = "processing"
                    if os.path.exists(duplicate_meta_path):
                        try:
                            with open(duplicate_meta_path, "r", encoding="utf-8") as f:
                                duplicate_status = json.load(f).get("status", "processing")
                        except Exception:
                            duplicate_status = "processing"

                    if duplicate_status == "ready" and self._restore_from_cached_course(
                        course_id,
                        source_paths,
                        duplicate_course_id,
                        combined_hash,
                        user_id=user_id,
                    ):
                        return
                    if duplicate_status in {"failed", "paused_due_to_quota"}:
                        logger.warning(
                            "[Cache WAIT] in-flight course '%s' ended as %s. Course '%s' will process from scratch.",
                            duplicate_course_id,
                            duplicate_status,
                            course_id,
                        )
                        break
                    time.sleep(1)

                with _HASH_LOCK:
                    if _IN_FLIGHT_HASHES.get(combined_hash) == duplicate_course_id:
                        _IN_FLIGHT_HASHES[combined_hash] = course_id
                        owns_inflight_hash = True

                cache = _load_hash_cache()
                cached_course_id = cache.get(combined_hash)
                if cached_course_id and cached_course_id != course_id:
                    if self._restore_from_cached_course(course_id, source_paths, cached_course_id, combined_hash, user_id=user_id):
                        return

            logger.info("[Cache MISS] Processing course '%s' from scratch.", course_id)
            _update_meta(course_id, {
                "stage": "extracting_text",
                "progress": 5,
                "progress_message": "Bắt đầu phân tích tài liệu...",
            })

            t_total = time.time()

            def _on_progress(current: int, total: int, message: str) -> None:
                progress = min(95, current)
                _update_meta(course_id, {
                    "stage": _stage_from_progress(progress),
                    "progress": progress,
                    "progress_message": message,
                })

            rag = RAGChains(course_id, source_paths)
            rag.vectorstore = create_or_load_vectorstore(
                course_id, source_paths, on_progress=_on_progress, user_id=user_id,
            )
            rag.initialise_chains_only()

            with self._lock:
                self._courses[course_id] = rag
                self._lru[course_id] = None
                self._all_course_ids.add(course_id)

            total_time = round(time.time() - t_total, 2)

            # Save hash to cache for future dedup
            cache[combined_hash] = course_id
            _save_hash_cache(cache)
            preprocess_profile = get_index_stats(course_id)
            doc_quality_report = preprocess_profile.get("document_quality_report")
            is_limited = _is_limited_document_quality(doc_quality_report)
            final_stage = "completed_limited" if is_limited else "completed"
            final_message = (
                "Đã đọc được một phần tài liệu. Một số học liệu sẽ dùng chế độ rút gọn/fallback."
                if is_limited
                else "Hoàn thành!"
            )

            _update_meta(course_id, {
                "status": "ready",
                "document_status": final_stage,
                "stage": final_stage,
                "ready_at": time.time(),
                "progress": 100,
                "progress_message": final_message,
                "file_hash": combined_hash,
                "total_processing_time": total_time,
                "preprocess_profile": preprocess_profile,
                "document_quality_report": doc_quality_report,
                "job_status": "completed",
            })
            logger.info(
                "[Background] Course '%s' processed in %.2fs (document_status=%s).",
                course_id,
                total_time,
                final_stage,
            )

        except Exception as exc:
            failure = _structured_processing_error(course_id, exc)
            logger.exception(
                "[Background] Failed processing '%s' stage=%s action=%s: %s",
                course_id,
                failure["stage"],
                failure["recommended_action"],
                exc,
            )
            try:
                _update_meta(course_id, {
                    "status": failure["status"],
                    "document_status": failure["status"],
                    "stage": failure["stage"],
                    "error": failure["user_message"],
                    "user_message": failure["user_message"],
                    "technical_error": failure["technical_error"],
                    "can_retry": failure["can_retry"],
                    "recommended_action": failure["recommended_action"],
                    "error_code": failure["error_code"],
                    "failure": failure,
                    "job_status": "failed",
                    "failed_at": time.time(),
                    "progress": -1,
                    "progress_message": failure["user_message"],
                })
            except Exception:
                pass
            raise
        finally:
            if combined_hash and owns_inflight_hash:
                with _HASH_LOCK:
                    if _IN_FLIGHT_HASHES.get(combined_hash) == course_id:
                        _IN_FLIGHT_HASHES.pop(combined_hash, None)

    def get_course_status(self, course_id: str) -> str:
        """Return course processing status."""
        if course_id in self._courses and self._courses[course_id].vectorstore is not None:
            return "ready"

        meta_path = get_course_path(course_id)["meta"]
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("status", "pending")
            except Exception:
                pass

        return "unknown"

    def reset_for_retry(self, course_id: str) -> None:
        """Forget in-memory vector adapters before retrying preprocessing."""
        with self._lock:
            self._courses.pop(course_id, None)
            self._lru.pop(course_id, None)
            self._all_course_ids.add(course_id)

    def create_course(self, source_path: str | Sequence[str]) -> str:
        """Synchronously create and index a course."""
        course_id = generate_course_id()
        source_paths = _coerce_source_paths(source_path)
        rag = RAGChains(course_id, source_paths).initialise()
        self._courses[course_id] = rag
        self._lru[course_id] = None
        self._all_course_ids.add(course_id)

        with open(get_course_path(course_id)["meta"], "w", encoding="utf-8") as f:
            json.dump(
                {
                    "course_id": course_id,
                    "source_path": source_paths[0] if source_paths else "",
                    "source_paths": source_paths,
                    "pdf_path": source_paths[0] if source_paths else "",
                    "filenames": [os.path.basename(path) for path in source_paths],
                    "file_count": len(source_paths),
                    "status": "ready",
                    "stage": "completed",
                    "created_at": time.time(),
                    "ready_at": time.time(),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        return course_id

    def get_course(self, course_id: str) -> Optional[RAGChains]:
        """Get a course, lazy-loading it from the configured vector DB if needed."""
        return self._ensure_course_loaded(course_id)

    def remove_course(self, course_id: str) -> None:
        """Remove a course from memory, generated files, and vector DB."""
        with self._lock:
            self._courses.pop(course_id, None)
            self._lru.pop(course_id, None)
            self._all_course_ids.discard(course_id)

        try:
            drop_vector_index(course_id)
        except Exception as exc:
            logger.warning("[Remove] Failed to drop vector DB data for '%s': %s", course_id, exc)

        try:
            removed_refs = _remove_hash_cache_refs(course_id)
            if removed_refs:
                logger.info("[Remove] Removed %d document hash cache refs for '%s'.", removed_refs, course_id)
        except Exception as exc:
            logger.warning("[Remove] Failed to clean cache refs for '%s': %s", course_id, exc)

        try:
            from backend.services.storage import get_file_storage

            get_file_storage().delete_document_files(course_id, get_course_path(course_id).values())
        except Exception as exc:
            logger.warning("[Remove] Storage provider failed for '%s': %s", course_id, exc)
            for path in get_course_path(course_id).values():
                if os.path.exists(path):
                    try:
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                        else:
                            os.remove(path)
                    except Exception as remove_exc:
                        logger.warning("[Remove] Failed to remove '%s': %s", path, remove_exc)

    def list_courses(self) -> list[str]:
        """List all registered course IDs."""
        return sorted(self._all_course_ids)

    def contains(self, course_id: str) -> bool:
        """Return whether a course ID is registered."""
        return course_id in self._all_course_ids
