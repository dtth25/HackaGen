"""FastAPI server for the AI Course Generator Study Pack API."""

# ruff: noqa: E402

import json
import os
import re
import sys

_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

import time
import uuid
from collections import OrderedDict
from contextlib import asynccontextmanager
from functools import partial
from typing import Any, Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

from backend.core.config import (
    BOOKS_DIR,
    CACHE_DIR,
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    CACHE_PROVIDER,
    DATA_DIR,
    INDEX_DIR,
    JOB_QUEUE_PROVIDER,
    LOCAL_OUTPUT_DIR,
    QUESTIONS_DIR,
    SLIDES_DIR,
    STORAGE_PROVIDER,
    UPLOAD_DIR,
    VECTOR_DB_PROVIDER,
    VIDEOS_DIR,
    _timestamp,
    get_course_path,
    logger,
    sanitize_input,
)
from backend.services.course_gen import CourseManager
from backend.services.cache import get_cache_provider
from backend.services.jobs import JobQueue, get_job_queue
from backend.services.storage import get_file_storage
from backend.vector_db.manager import (
    drop_vector_index,
    get_index_stats,
    health_check as vector_db_health_check,
    list_all_vector_courses,
)
from fastapi import Depends
from backend.core.db import init_db
from backend.core.security import get_current_user
from backend.models.user import UserInDB
from backend.api.auth import router as auth_router
from backend.api.admin import router as admin_router


ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
ALLOW_ALL_ORIGINS = os.getenv("ALLOW_ALL_ORIGINS", "true").lower() in {"1", "true", "yes"}

MAX_UPLOAD_SIZE = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "300"))
PUBLIC_DEMO_COURSE_IDS = {"43826a7bcf62", "9e2144776930", "80040c13b2af"}

course_manager: Optional[CourseManager] = None
job_queue: Optional[JobQueue] = None
rate_limit_store: OrderedDict[str, list[float]] = OrderedDict()
STARTUP_DIRS = {
    "upload_dir": UPLOAD_DIR,
    "data_dir": DATA_DIR,
    "index_dir": INDEX_DIR,
    "chroma_dir": CHROMA_PERSIST_DIR,
    "questions_dir": QUESTIONS_DIR,
    "cache_dir": CACHE_DIR,
    "books_dir": BOOKS_DIR,
    "slides_dir": SLIDES_DIR,
    "videos_dir": VIDEOS_DIR,
}
if LOCAL_OUTPUT_DIR:
    STARTUP_DIRS["local_output_dir"] = LOCAL_OUTPUT_DIR
startup_state: dict = {
    "status": "starting",
    "ready": False,
    "vector_db_provider": VECTOR_DB_PROVIDER,
    "vector_db_health": None,
    "storage_provider": STORAGE_PROVIDER,
    "storage_health": None,
    "job_queue_provider": JOB_QUEUE_PROVIDER,
    "job_queue_health": None,
    "cache_provider": CACHE_PROVIDER,
    "cache_health": None,
    "details": {
        "upload_dir": False,
        "output_dir": False,
        "vector_db": False,
        "config_loaded": False,
    },
    "startup_duration_seconds": None,
    "error": None,
}


def _startup_health_payload() -> dict:
    """Return a stable readiness payload for frontend proxy checks."""
    details = dict(startup_state.get("details", {}))
    vector_db_health = startup_state.get("vector_db_health") or {}
    vector_db_ready = bool(details.get("vector_db", False))
    return {
        "status": startup_state.get("status", "starting"),
        "ready": bool(startup_state.get("ready")),
        "details": details,
        # Nested vector_db status block for frontend/user-friendly warnings.
        "vector_db": {
            "provider": startup_state.get("vector_db_provider", VECTOR_DB_PROVIDER),
            "ready": vector_db_ready,
            "collection": CHROMA_COLLECTION_NAME,
            "persist_dir": CHROMA_PERSIST_DIR,
            "error": vector_db_health.get("error") if not vector_db_ready else None,
        },
        # Flat fields kept for backward compatibility with existing frontend proxy checks.
        "vector_db_provider": startup_state.get("vector_db_provider", VECTOR_DB_PROVIDER),
        "storage_provider": startup_state.get("storage_provider", STORAGE_PROVIDER),
        "job_queue_provider": startup_state.get("job_queue_provider", JOB_QUEUE_PROVIDER),
        "cache_provider": startup_state.get("cache_provider", CACHE_PROVIDER),
        "vector_db_ready": vector_db_ready,
        "storage_ready": bool((startup_state.get("storage_health") or {}).get("ready")),
        "job_queue_ready": bool((startup_state.get("job_queue_health") or {}).get("ready")),
        "cache_ready": bool((startup_state.get("cache_health") or {}).get("ready")),
        "chroma_persist_dir": CHROMA_PERSIST_DIR,
        "chroma_collection_name": CHROMA_COLLECTION_NAME,
        "startup_duration_seconds": startup_state.get("startup_duration_seconds"),
        "error": startup_state.get("error"),
    }


def _initialise_backend_runtime() -> None:
    """Prepare folders and the local vector DB registry without calling Gemini."""
    global course_manager, job_queue
    startup_started = time.perf_counter()
    startup_state.update(
        {
            "status": "starting",
            "ready": False,
            "vector_db_provider": VECTOR_DB_PROVIDER,
            "vector_db_health": None,
            "storage_provider": STORAGE_PROVIDER,
            "storage_health": None,
            "job_queue_provider": JOB_QUEUE_PROVIDER,
            "job_queue_health": None,
            "cache_provider": CACHE_PROVIDER,
            "cache_health": None,
            "startup_duration_seconds": None,
            "error": None,
            "details": {
                "upload_dir": False,
                "output_dir": False,
                "vector_db": False,
                "config_loaded": False,
            },
        }
    )

    try:
        logger.info("[Startup] Loading config and creating runtime directories...")
        for dir_name, dir_path in STARTUP_DIRS.items():
            os.makedirs(dir_path, exist_ok=True)
            logger.info("[Startup] Directory ready: %s=%s", dir_name, os.path.abspath(dir_path))

        init_db()
        logger.info("[Startup] SQLite user database initialized.")

        storage_state = get_file_storage().health_check()
        cache_state = get_cache_provider().health_check()
        job_queue = get_job_queue()
        queue_state = job_queue.health_check()
        vector_state = vector_db_health_check()
        details = {
            "upload_dir": os.path.isdir(UPLOAD_DIR),
            "output_dir": all(
                os.path.isdir(path)
                for path in [QUESTIONS_DIR, CACHE_DIR, BOOKS_DIR, SLIDES_DIR, VIDEOS_DIR]
            ),
            "vector_db": bool(vector_state.get("ready")),
            "config_loaded": True,
        }
        startup_state["details"] = details
        startup_state["vector_db_provider"] = vector_state.get("provider", VECTOR_DB_PROVIDER)
        startup_state["vector_db_health"] = vector_state
        startup_state["storage_provider"] = storage_state.get("provider", STORAGE_PROVIDER)
        startup_state["storage_health"] = storage_state
        startup_state["job_queue_provider"] = queue_state.get("provider", JOB_QUEUE_PROVIDER)
        startup_state["job_queue_health"] = queue_state
        startup_state["cache_provider"] = cache_state.get("provider", CACHE_PROVIDER)
        startup_state["cache_health"] = cache_state

        from backend.core.config import get_model_name, EMBEDDING_MODEL
        default_m = get_model_name("default")
        book_m = get_model_name("book")
        slide_m = get_model_name("slide")
        video_m = get_model_name("video")
        quality_m = get_model_name("quality")
        course_m = get_model_name("course")
        mindmap_m = get_model_name("mindmap")
        quiz_m = get_model_name("quiz")
        flashcard_m = get_model_name("flashcard")
        summary_m = get_model_name("summary")
        fast_m = get_model_name("fast")
        mode = "Pro Mode" if "pro" in default_m.lower() or "pro" in book_m.lower() else "Flash Mode"
        logger.info(
            "[Startup Config] Active Mode: %s | Default: %s | Fast: %s | Book: %s | Slide: %s | "
            "Video: %s | Course: %s | Mindmap: %s | Quiz: %s | Flashcard: %s | Summary: %s | "
            "Quality: %s | Embedding: %s | Vector DB: %s",
            mode,
            default_m,
            fast_m,
            book_m,
            slide_m,
            video_m,
            course_m,
            mindmap_m,
            quiz_m,
            flashcard_m,
            summary_m,
            quality_m,
            EMBEDDING_MODEL,
            startup_state["vector_db_provider"],
        )
        logger.info(
            "[Startup Providers] storage=%s queue=%s cache=%s",
            startup_state["storage_provider"],
            startup_state["job_queue_provider"],
            startup_state["cache_provider"],
        )

        logger.info(
            "[Startup] Initializing CourseManager (scan vector DB metadata, provider=%s)...",
            startup_state["vector_db_provider"],
        )
        course_manager = CourseManager()
        courses = course_manager.list_courses()

        runtime_ready = all(details.values())
        startup_state.update(
            {
                "status": "ok" if runtime_ready else "error",
                "ready": runtime_ready,
                "startup_duration_seconds": round(time.perf_counter() - startup_started, 3),
                "error": None if runtime_ready else vector_state.get("error") or vector_state.get("install_hint"),
            }
        )
        logger.info(
            "[Startup] Ready=%s in %.3fs. Restored %d course(s): %s",
            startup_state["ready"],
            startup_state["startup_duration_seconds"],
            len(courses),
            courses,
        )
    except Exception as exc:
        course_manager = None
        job_queue = None
        startup_state.update(
            {
                "status": "error",
                "ready": False,
                "startup_duration_seconds": round(time.perf_counter() - startup_started, 3),
                "error": str(exc),
            }
        )
        logger.exception("[Startup] Failed to initialize backend: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create the course manager on startup."""
    _initialise_backend_runtime()
    yield
    logger.info("[Shutdown] Cleaning up backend resources...")


app = FastAPI(
    title="AI Course Generator API",
    version="4.0.0",
    description="Generate a grounded Document-to-Study-Pack experience centered on a structured Sách PDF.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ALLOW_ALL_ORIGINS else ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth")
app.include_router(auth_router, prefix="/auth")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(admin_router, prefix="/admin")


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log each endpoint and duration for backend troubleshooting."""
    request_started = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        logger.exception("[Request] %s %s failed: %s", request.method, request.url.path, exc)
        raise
    finally:
        status_code = getattr(response, "status_code", "error")
        logger.info(
            "[Request] %s %s -> %s in %.3fs",
            request.method,
            request.url.path,
            status_code,
            time.perf_counter() - request_started,
        )


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply a simple in-memory rate limit."""
    if request.method == "OPTIONS" or request.url.path.endswith("/status"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    rate_limit_store.setdefault(client_ip, [])
    rate_limit_store[client_ip] = [t for t in rate_limit_store[client_ip] if now - t < RATE_LIMIT_WINDOW]

    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        response = JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Vui lòng thử lại sau."},
        )
        origin = request.headers.get("origin")
        if ALLOW_ALL_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = "*"
        elif origin in ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

    rate_limit_store[client_ip].append(now)

    if len(rate_limit_store) > 1000:
        old_clients = [
            ip for ip, times in rate_limit_store.items() if times and now - max(times) > RATE_LIMIT_WINDOW * 2
        ]
        for ip in old_clients:
            del rate_limit_store[ip]

    return await call_next(request)


class UploadResponse(BaseModel):
    course_id: str
    document_id: str
    filename: str
    filenames: list[str] = Field(default_factory=list)
    file_count: int = 1
    status: str
    message: str


class StatusResponse(BaseModel):
    status: str
    course_id: Optional[str] = None
    courses: Optional[list[str]] = None


class GenerateBookRequest(BaseModel):
    course_id: str
    user_prompt: str = ""
    target_audience: str = "sinh viên"
    learning_mode: str = "normal"
    # Optional per-request Learning Profile override; falls back to the user's saved
    # profile (see models/learning_profile.py) when omitted.
    profile: Optional[dict[str, Any]] = None

    @field_validator("user_prompt")
    @classmethod
    def validate_user_prompt(cls, value: str) -> str:
        value = sanitize_input(value or "")
        if len(value) > 2000:
            raise ValueError("Yêu cầu quá dài (tối đa 2000 ký tự).")
        return value

    @field_validator("target_audience")
    @classmethod
    def validate_target_audience(cls, value: str) -> str:
        value = sanitize_input(value or "sinh viên")
        if len(value) > 120:
            raise ValueError("Đối tượng học quá dài (tối đa 120 ký tự).")
        return value or "sinh viên"

    @field_validator("learning_mode")
    @classmethod
    def validate_learning_mode(cls, value: str) -> str:
        value = sanitize_input(value or "normal").lower()
        return value if value in {"normal", "high_yield"} else "normal"


class GenerateQuizRequest(BaseModel):
    course_id: str
    topic: str = "tổng quan"
    quantity: int = Field(default=10, ge=1, le=30)
    difficulty: str = "medium"
    learning_mode: str = "normal"
    profile: Optional[dict[str, Any]] = None

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        value = sanitize_input(value or "tổng quan")
        if len(value) > 200:
            raise ValueError("Chủ đề quá dài (tối đa 200 ký tự).")
        return value or "tổng quan"

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, value: str) -> str:
        value = sanitize_input(value or "medium").lower()
        return value if value in {"easy", "medium", "hard"} else "medium"

    @field_validator("learning_mode")
    @classmethod
    def validate_learning_mode(cls, value: str) -> str:
        value = sanitize_input(value or "normal").lower()
        return value if value in {"normal", "high_yield"} else "normal"


class GenerateSlideRequest(BaseModel):
    course_id: str
    topic: str = "tổng quan"
    num_slides: int = Field(default=8, ge=1, le=30)
    learning_mode: str = "normal"
    profile: Optional[dict[str, Any]] = None

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        value = sanitize_input(value or "tổng quan")
        if len(value) > 200:
            raise ValueError("Chủ đề quá dài (tối đa 200 ký tự).")
        return value or "tổng quan"

    @field_validator("learning_mode")
    @classmethod
    def validate_learning_mode(cls, value: str) -> str:
        value = sanitize_input(value or "normal").lower()
        return value if value in {"normal", "high_yield"} else "normal"


class GenerateVidRequest(BaseModel):
    course_id: Optional[str] = None
    document_id: Optional[str] = None
    video_mode: str = "three_minute"
    topic_id: Optional[str] = None
    chapter_id: Optional[str] = None
    user_mode: str = "student"
    render_mp4: bool = True
    # Bypass the "large document -> use a playlist" recommendation when the user
    # explicitly chooses to render a single compressed video anyway.
    force: bool = False
    topic: str = "tổng quan"
    duration_minutes: int = Field(default=3, ge=1, le=15)
    learning_mode: str = "normal"
    video_renderer: str = "simple_templates"
    allow_renderer_fallback: bool = True
    profile: Optional[dict[str, Any]] = None

    def get_document_id(self) -> str:
        return self.document_id or self.course_id or ""

    @field_validator("video_mode")
    @classmethod
    def validate_video_mode(cls, value: str) -> str:
        value = (value or "three_minute").strip().lower()
        valid_modes = {"sixty_second", "three_minute", "ten_minute", "playlist_by_chapter"}
        return value if value in valid_modes else "three_minute"

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        value = sanitize_input(value or "tổng quan")
        if len(value) > 200:
            raise ValueError("Chủ đề quá dài (tối đa 200 ký tự).")
        return value or "tổng quan"

    @field_validator("learning_mode")
    @classmethod
    def validate_learning_mode(cls, value: str) -> str:
        value = sanitize_input(value or "normal").lower()
        return value if value in {"normal", "high_yield"} else "normal"

    @field_validator("video_renderer")
    @classmethod
    def validate_video_renderer(cls, value: str) -> str:
        value = sanitize_input(value or "simple_templates").lower()
        aliases = {"simple_slides": "simple_templates", "simple": "simple_templates"}
        value = aliases.get(value, value)
        return value if value in {"simple_templates", "manim"} else "simple_templates"


def _get_course_manager() -> CourseManager:
    """Return the course manager or fail if startup has not completed."""
    if not course_manager:
        raise HTTPException(503, "Backend đang khởi động, vui lòng chờ vài giây.")
    return course_manager


def _get_ready_course(course_id: str):
    """Return a ready course or raise a public API error."""
    mgr = _get_course_manager()
    status = mgr.get_course_status(course_id)
    if status != "ready":
        raise HTTPException(400, f"Tài liệu '{course_id}' chưa sẵn sàng (trạng thái: {status}).")

    rag = mgr.get_course(course_id)
    if not rag:
        raise HTTPException(404, f"Không tìm thấy tài liệu '{course_id}'.")
    return rag


def _read_json(path: str, missing_message: str):
    """Read a JSON artifact from disk."""
    if not os.path.exists(path):
        raise HTTPException(404, missing_message)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _clean_source_excerpt(value: str, limit: int = 420) -> str:
    """Return a short public-safe source excerpt without internal debug markers.

    Returns "" for chunks that are table-of-contents noise — those are not useful
    grounding evidence and would leak "Contents"/index lines into the UI.
    """
    cleaned = re.sub(r"===\s*BẮT ĐẦU.*?===", " ", str(value or ""), flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"===\s*KẾT THÚC.*?===", " ", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"\[MÃ ĐỊNH DANH TRANG:\s*\d+\]", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bNỘI DUNG:\s*", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bpage\s*:\s*\d+\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bchunk_id\s*:\s*[\w.-]+\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bsource\s*:\s*[\w./\\:-]+\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?:\.\s*){3,}", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if re.match(r"^(contents|table of contents|mục lục|muc luc)\b", cleaned, flags=re.IGNORECASE):
        return ""
    # Index-style content: mostly short "1. Title 7"-like entries with little prose.
    digit_ratio = sum(ch.isdigit() for ch in cleaned) / len(cleaned) if cleaned else 0
    if digit_ratio > 0.2 and len(cleaned) < 600:
        return ""

    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rsplit(" ", 1)[0].strip().rstrip(".") + "…"


def _coerce_source_page(value) -> int | None:
    """Coerce an optional source page value for display."""
    if value in (None, "", 0):
        return None
    try:
        page = int(value)
        return page if page > 0 else None
    except (TypeError, ValueError):
        return None


def _display_source_filename(path) -> str | None:
    """Best-effort human-readable filename for a stored source path (strips the internal timestamp/index prefix)."""
    if not path:
        return None
    name = os.path.basename(str(path))
    name = re.sub(r"^(?:\d{2}_)?\d{9,}_", "", name)
    return name or None


def _source_id_aliases(item) -> set[str]:
    """Return internal aliases that may be used by generated outputs."""
    metadata = getattr(item, "metadata", {}) or {}
    aliases = {
        str(getattr(item, "chunk_id", "") or ""),
        str(getattr(item, "source_chunk_id", "") or ""),
        str(metadata.get("chunk_id") or ""),
        str(metadata.get("source_chunk_id") or ""),
    }
    return {alias for alias in aliases if alias}


def _document_source_payload(document_id: str, ids: str = "", developer: bool = False) -> dict:
    """Build clean source excerpts for UI grounding without leaking debug metadata by default."""
    mgr = _get_course_manager()
    if not mgr.contains(document_id):
        raise HTTPException(404, f"Không tìm thấy tài liệu '{document_id}'.")

    rag = _get_ready_course(document_id)
    if not getattr(rag, "vectorstore", None):
        raise HTTPException(409, "Vector DB chưa sẵn sàng cho tài liệu này.")

    requested_ids = {item.strip() for item in str(ids or "").split(",") if item.strip()}
    try:
        chunks = rag.vectorstore.get_document_chunks(document_id)
    except Exception as exc:
        logger.warning("[Sources] Could not load source chunks document_id=%s: %s", document_id, exc)
        raise HTTPException(500, "Không thể tải nguồn được dùng cho tài liệu này.") from exc

    sources = []
    for item in chunks:
        aliases = _source_id_aliases(item)
        if requested_ids and aliases.isdisjoint(requested_ids):
            continue

        excerpt = _clean_source_excerpt(getattr(item, "text", ""))
        if not excerpt:
            continue

        metadata = getattr(item, "metadata", {}) or {}
        source = {
            "page": _coerce_source_page(metadata.get("page")),
            "excerpt": excerpt,
            "filename": _display_source_filename(metadata.get("source")),
        }
        if developer:
            source["source_chunk_id"] = (
                str(getattr(item, "source_chunk_id", "") or metadata.get("source_chunk_id") or metadata.get("chunk_id") or "")
                or None
            )
        sources.append(source)
        if len(sources) >= 24:
            break

    return {
        "document_id": document_id,
        "total_source_chunks": len(chunks),
        "matched_source_chunks": len(sources),
        "sources": sources,
    }


def _update_course_meta(course_id: str, updates: dict) -> None:
    """Best-effort update for local course metadata."""
    meta_path = get_course_path(course_id)["meta"]
    try:
        meta = {}
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        meta.update(updates)
        os.makedirs(os.path.dirname(meta_path), exist_ok=True)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning("[Meta] Could not update course metadata course_id=%s: %s", course_id, exc)


def _build_course_info(course_id: str) -> dict:
    """Build course metadata for list endpoints."""
    info = {"course_id": course_id, "status": "unknown"}
    if course_manager:
        info["status"] = course_manager.get_course_status(course_id)

    meta_path = get_course_path(course_id)["meta"]
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            info["created_at"] = meta.get("created_at")
            info["filenames"] = meta.get("filenames") or []
            info["file_count"] = meta.get("file_count") or len(info["filenames"])
            if "error" in meta:
                info["error"] = meta["error"]
            if "error_code" in meta:
                info["error_code"] = meta["error_code"]
        except Exception:
            pass
    return info


@app.get("/health")
async def readiness_health():
    """Return startup readiness without touching Gemini quota."""
    return _startup_health_payload()


@app.get("/api/health", response_model=StatusResponse)
async def health():
    """Return backend health and registered course IDs."""
    mgr = _get_course_manager()
    return StatusResponse(status="ok", course_id=None, courses=sorted(mgr.list_courses()))


@app.get("/api/courses", response_model=StatusResponse)
async def list_courses(current_user: UserInDB = Depends(get_current_user)):
    """Return registered course IDs."""
    mgr = _get_course_manager()
    courses = [course_id for course_id in sorted(mgr.list_courses()) if _course_is_visible(course_id, current_user)]
    return StatusResponse(status="ok", courses=courses)


@app.get("/api/courses/all")
async def list_all_courses_with_meta(current_user: UserInDB = Depends(get_current_user)):
    """Return the current user's own courses with local metadata (admins see all)."""
    mgr = _get_course_manager()
    courses = []
    seen_ids = set()

    def _visible(course_id: str) -> bool:
        if current_user.role == "admin" or course_id.startswith("demo"):
            return True
        return _course_owner_id(course_id) == current_user.id

    for course_id in list_all_vector_courses():
        if course_id and course_id not in seen_ids and _visible(course_id):
            seen_ids.add(course_id)
            courses.append(_build_course_info(course_id))

    for course_id in mgr.list_courses():
        if course_id not in seen_ids and _visible(course_id):
            courses.append(_build_course_info(course_id))

    return {"courses": courses, "total": len(courses)}


@app.get("/api/demo-course")
async def get_demo_course():
    """Return safe demo course ID and metadata without calling Gemini quota."""
    demo_id = "43826a7bcf62"
    paths = get_course_path(demo_id)
    import shutil
    if not os.path.exists(paths["questions"]):
        alt_q = os.path.join(QUESTIONS_DIR, "course_9e2144776930_questions.json")
        if os.path.exists(alt_q):
            shutil.copy2(alt_q, paths["questions"])
    if not os.path.exists(paths["questions_key_pdf"]):
        alt_key = os.path.join(QUESTIONS_DIR, "course_80040c13b2af_answer_key.pdf")
        if os.path.exists(alt_key):
            shutil.copy2(alt_key, paths["questions_key_pdf"])
    return {
        "course_id": demo_id,
        "document_id": demo_id,
        "filename": "AI_for_A0_Demo.pdf",
        "filenames": ["AI_for_A0_Demo.pdf"],
        "status": "ready",
        "stage": "completed",
        "message": "Đã nạp tài liệu demo thành công. Không tiêu tốn quota Gemini.",
    }


@app.delete("/api/courses/{course_id}", response_model=StatusResponse)
@app.delete("/api/documents/{course_id}", response_model=StatusResponse)
@app.delete("/documents/{course_id}", response_model=StatusResponse)
async def delete_course(course_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Delete a course/document and generated public artifacts."""
    _verify_course_access(course_id, current_user)
    mgr = _get_course_manager()
    if not mgr.contains(course_id):
        raise HTTPException(404, f"Không tìm thấy tài liệu '{course_id}'.")
    mgr.remove_course(course_id)
    return StatusResponse(status="deleted", course_id=course_id)



def _validate_upload_metadata(upload_file: UploadFile) -> None:
    """Validate upload metadata before reading file bytes."""
    if not upload_file.filename:
        raise HTTPException(400, "Tên file không được để trống.")

    file_ext = os.path.splitext(upload_file.filename.lower())[1]
    if file_ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            400,
            f"Định dạng file '{file_ext}' không hợp lệ. Hệ thống chỉ hỗ trợ: {allowed}",
        )


async def _save_upload_files(course_id: str, upload_files: list[UploadFile]) -> tuple[list[str], list[str]]:
    """Save one or many upload files under the same course workspace."""
    storage = get_file_storage(upload_dir=UPLOAD_DIR, output_dir=LOCAL_OUTPUT_DIR)
    saved_paths: list[str] = []
    filenames: list[str] = []

    for index, upload_file in enumerate(upload_files, 1):
        _validate_upload_metadata(upload_file)
        content = await upload_file.read()
        if len(content) == 0:
            raise HTTPException(400, f"File '{upload_file.filename}' là file rỗng. Vui lòng kiểm tra lại.")
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                400,
                f"File '{upload_file.filename}' quá lớn. Tối đa {MAX_UPLOAD_SIZE // (1024 * 1024)}MB.",
            )

        try:
            file_path = storage.save_upload(course_id, upload_file.filename, content, index=index)
        except Exception as exc:
            raise HTTPException(500, f"Lỗi trong quá trình lưu file: {exc}") from exc

        saved_paths.append(file_path)
        filenames.append(upload_file.filename)
        logger.info(
            "[Upload] Saved file course=%s filename=%s size_bytes=%d path=%s",
            course_id,
            upload_file.filename,
            len(content),
            os.path.abspath(file_path),
        )

    return saved_paths, filenames


@app.post("/api/upload", response_model=UploadResponse)
async def upload(
    file: UploadFile | None = File(None),
    files: list[UploadFile] | None = File(None),
    current_user: UserInDB = Depends(get_current_user),
):
    """Upload one or many PDF, DOCX, or TXT documents as one course corpus."""
    mgr = _get_course_manager()

    upload_files = list(files or [])
    if file is not None:
        upload_files.insert(0, file)
    upload_files = [item for item in upload_files if item and item.filename]
    if not upload_files:
        raise HTTPException(400, "Vui lòng chọn ít nhất một file PDF, DOCX hoặc TXT.")

    course_id = uuid.uuid4().hex[:12]
    saved_paths, filenames = await _save_upload_files(course_id, upload_files)
    mgr.register_course_id(course_id, saved_paths, user_id=current_user.id)

    queue = job_queue or get_job_queue()
    # `user_id=` on enqueue_preprocess is consumed by the queue itself (job-record
    # tracking only) and is never forwarded to the handler — bind it via partial so
    # process_new_course actually receives it and can tag Chroma chunk metadata.
    process_handler = partial(mgr.process_new_course, user_id=current_user.id)
    preprocess_job = queue.enqueue_preprocess(course_id, process_handler, course_id, saved_paths, user_id=current_user.id)
    _update_course_meta(
        course_id,
        {
            "preprocess_job_id": preprocess_job.id,
            "job_type": preprocess_job.job_type,
            "job_status": preprocess_job.status,
        },
    )

    file_label = filenames[0] if len(filenames) == 1 else f"{len(filenames)} files"
    return UploadResponse(
        course_id=course_id,
        document_id=course_id,
        filename=file_label,
        filenames=filenames,
        file_count=len(filenames),
        status="processing",
        message=f"Đã nhận {len(filenames)} file và đang phân tích tài liệu. ID tài liệu: {course_id}",
    )


def _course_owner_id(course_id: str) -> str | None:
    """Return the owning user_id recorded in a course's metadata, if any."""
    meta_path = get_course_path(course_id)["meta"]
    if not os.path.exists(meta_path):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return meta.get("user_id")
    except Exception as exc:
        logger.debug("[Auth] Failed to read owner for course %s: %s", course_id, exc)
        return None


def _is_public_demo_course(course_id: str) -> bool:
    return course_id.startswith("demo") or course_id in PUBLIC_DEMO_COURSE_IDS


def _course_is_visible(course_id: str, user: UserInDB) -> bool:
    if user.role == "admin" or _is_public_demo_course(course_id):
        return True
    return _course_owner_id(course_id) == user.id


def _verify_course_access(course_id: str, user: UserInDB) -> None:
    if user.role == "admin" or _is_public_demo_course(course_id):
        return
    owner_id = _course_owner_id(course_id)
    if not owner_id:
        raise HTTPException(status_code=403, detail="Tai lieu nay chua gan voi tai khoan cua ban.")
    if owner_id != user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập tài liệu này.")


@app.get("/api/course/{course_id}/status")
async def get_course_status(course_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Return document processing status with progress tracking."""
    _verify_course_access(course_id, current_user)
    mgr = _get_course_manager()
    status = mgr.get_course_status(course_id)

    info = {"course_id": course_id, "status": status}

    meta_path = get_course_path(course_id)["meta"]
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if meta.get("error"):
                info["error"] = meta["error"]
            if meta.get("error_code"):
                info["error_code"] = meta["error_code"]
            info["filenames"] = meta.get("filenames") or []
            info["file_count"] = meta.get("file_count") or len(info["filenames"])
            if "stage" in meta:
                info["stage"] = meta["stage"]
            # Progress tracking fields
            if "progress" in meta:
                info["progress"] = meta["progress"]
            if "progress_message" in meta:
                info["progress_message"] = meta["progress_message"]
            if "total_processing_time" in meta:
                info["total_processing_time"] = meta["total_processing_time"]
            if "cached_from" in meta:
                info["cached_from"] = meta["cached_from"]
            if "preprocess_profile" in meta:
                info["preprocess_profile"] = meta["preprocess_profile"]
            if "preprocess_job_id" in meta:
                info["job_id"] = meta["preprocess_job_id"]
            doc_quality = meta.get("document_quality_report") or (meta.get("preprocess_profile") or {}).get("document_quality_report")
            if not doc_quality:
                idx_stats = get_index_stats(course_id)
                doc_quality = idx_stats.get("document_quality_report")
            if doc_quality:
                info["document_quality_report"] = doc_quality
                info["quality_score"] = doc_quality.get("quality_score")
                info["pdf_type"] = doc_quality.get("pdf_type")
                info["warnings"] = doc_quality.get("warnings")
                info["recommended_action"] = doc_quality.get("recommended_action")
        except Exception:
            pass

    return info


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Return local job metadata for polling/admin views."""
    queue = job_queue or get_job_queue()

    job = queue.get_job_status(job_id)
    if not job:
        raise HTTPException(404, f"Không tìm thấy job '{job_id}'.")
    if current_user.role != "admin":
        job_user_id = job.get("user_id")
        if not job_user_id or job_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Ban khong co quyen truy cap job nay.")
    return job


DOCUMENT_PUBLIC_STATUSES = {
    "extracting_text",
    "cleaning_text",
    "chunking",
    "embedding",
    "storing_vectors",
    "completed",
    "completed_limited",
    "failed",
    "paused_due_to_quota",
    "analysis_failed",
    "extraction_failed",
    "embedding_failed",
    "vector_index_failed",
    "insufficient_context",
}


def _document_status_payload(document_id: str) -> dict:
    """Return a stable document preprocessing status payload for frontend polling."""
    mgr = _get_course_manager()
    course_status = mgr.get_course_status(document_id)
    if course_status == "unknown":
        raise HTTPException(404, f"Không tìm thấy tài liệu '{document_id}'.")

    meta: dict = {}
    meta_path = get_course_path(document_id)["meta"]
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as exc:
            logger.warning("[Status] Could not read metadata for '%s': %s", document_id, exc)

    stage = str(meta.get("stage") or "").strip()
    document_status = str(meta.get("document_status") or meta.get("status") or "").strip()
    error_code = meta.get("error_code")
    failure = meta.get("failure") if isinstance(meta.get("failure"), dict) else {}
    failure_stage = str(failure.get("stage") or "").strip() or (
        stage
        if stage in {"analysis_failed", "extraction_failed", "embedding_failed", "vector_index_failed", "insufficient_context"}
        else ""
    )

    if (
        stage == "paused_due_to_quota"
        or document_status == "paused_due_to_quota"
        or course_status == "paused_due_to_quota"
        or error_code == "EMBEDDING_QUOTA_EXCEEDED"
    ):
        public_status = "paused_due_to_quota"
    elif stage == "completed_limited" or document_status == "completed_limited":
        public_status = "completed_limited"
    elif course_status == "ready" or stage == "completed":
        public_status = "completed"
    elif course_status == "failed":
        public_status = "failed"
    elif stage in DOCUMENT_PUBLIC_STATUSES:
        public_status = stage
    elif course_status in {"pending", "processing"}:
        public_status = "extracting_text"
    else:
        public_status = "failed"

    raw_progress = meta.get("progress")
    if isinstance(raw_progress, (int, float)):
        progress = int(max(0, min(100, raw_progress)))
    elif public_status in {"completed", "completed_limited"}:
        progress = 100
    else:
        progress = 0

    default_messages = {
        "extracting_text": "Đang đọc nội dung tài liệu...",
        "cleaning_text": "Đang làm sạch nội dung tài liệu...",
        "chunking": "Đang chia nhỏ kiến thức...",
        "embedding": "Đang tạo embedding và kiểm soát quota...",
        "storing_vectors": "Đang lưu dữ liệu vào Vector DB...",
        "completed": "Tài liệu đã sẵn sàng.",
        "completed_limited": "Đã đọc được một phần tài liệu. Một số học liệu sẽ dùng chế độ rút gọn/fallback.",
        "failed": "Không phân tích được tài liệu.",
        "paused_due_to_quota": "Đã vượt giới hạn Gemini embedding, vui lòng chờ rồi thử lại hoặc dùng file nhỏ hơn.",
    }
    user_message = (
        failure.get("user_message")
        or meta.get("user_message")
        or (meta.get("error") if public_status in {"failed", "paused_due_to_quota"} else None)
    )
    message = (
        user_message
        or meta.get("progress_message")
        or default_messages.get(public_status, "Đang xử lý tài liệu...")
    )
    error = user_message if public_status in {"failed", "paused_due_to_quota"} else None

    payload = {
        "document_id": document_id,
        "status": public_status,
        "stage": failure_stage or stage or public_status,
        "failure_stage": failure_stage or None,
        "progress": progress,
        "message": message,
        "error": error,
        "user_message": user_message,
        "technical_error": failure.get("technical_error") or meta.get("technical_error"),
        "can_retry": bool(failure.get("can_retry", meta.get("can_retry", public_status in {"failed", "paused_due_to_quota"}))),
        "recommended_action": failure.get("recommended_action") or meta.get("recommended_action"),
        "error_code": failure.get("error_code") or error_code,
    }
    if meta.get("preprocess_job_id"):
        payload["job_id"] = meta["preprocess_job_id"]
        queue = job_queue or get_job_queue()
        job = queue.get_job_status(meta["preprocess_job_id"])
        if job:
            payload["job"] = job
    return payload


def _resolve_retry_source_paths(document_id: str, meta: dict) -> list[str]:
    """Resolve saved upload paths across common Windows/local working directories."""
    raw_paths = meta.get("source_paths") or meta.get("source_path") or meta.get("pdf_path") or []
    if isinstance(raw_paths, str):
        raw_paths = [raw_paths]
    paths: list[str] = []
    for raw in raw_paths:
        if not raw:
            continue
        raw_path = str(raw)
        candidates = [
            raw_path,
            os.path.abspath(raw_path),
            os.path.join(_current_dir, raw_path),
            os.path.join(_parent_dir, raw_path),
            os.path.join(UPLOAD_DIR, document_id, os.path.basename(raw_path)),
        ]
        found = next((candidate for candidate in candidates if os.path.exists(candidate)), None)
        if found:
            paths.append(os.path.abspath(found))
    return paths


def _retry_document_preprocess(document_id: str, current_user: UserInDB) -> dict:
    """Retry preprocessing from already-saved uploads without requiring re-upload."""
    _verify_course_access(document_id, current_user)
    meta_path = get_course_path(document_id)["meta"]
    if not os.path.exists(meta_path):
        raise HTTPException(404, f"Không tìm thấy metadata của tài liệu '{document_id}'.")
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception as exc:
        raise HTTPException(500, f"Không đọc được metadata của tài liệu '{document_id}'.") from exc

    source_paths = _resolve_retry_source_paths(document_id, meta)
    if not source_paths:
        raise HTTPException(
            404,
            "Không tìm thấy file đã upload để retry. Vui lòng upload lại tài liệu.",
        )

    try:
        drop_vector_index(document_id)
    except Exception as exc:
        logger.warning("[Retry] Could not clear previous vector index document_id=%s: %s", document_id, exc)

    mgr = _get_course_manager()
    mgr.reset_for_retry(document_id)
    queue = job_queue or get_job_queue()
    process_handler = partial(mgr.process_new_course, user_id=current_user.id)
    preprocess_job = queue.enqueue_preprocess(document_id, process_handler, document_id, source_paths, user_id=current_user.id)

    _update_course_meta(
        document_id,
        {
            "status": "processing",
            "document_status": "extracting_text",
            "stage": "extracting_text",
            "progress": 0,
            "progress_message": "Đang chạy lại phân tích tài liệu...",
            "error": None,
            "error_code": None,
            "user_message": None,
            "technical_error": None,
            "failure": None,
            "can_retry": False,
            "recommended_action": None,
            "source_paths": source_paths,
            "source_path": source_paths[0],
            "pdf_path": source_paths[0],
            "preprocess_job_id": preprocess_job.id,
            "job_type": preprocess_job.job_type,
            "job_status": preprocess_job.status,
            "retried_at": time.time(),
        },
    )
    logger.info("[Retry] Requeued preprocess document_id=%s job_id=%s files=%d", document_id, preprocess_job.id, len(source_paths))
    return {
        "document_id": document_id,
        "status": "processing",
        "stage": "extracting_text",
        "progress": 0,
        "message": "Đang chạy lại phân tích tài liệu...",
        "job_id": preprocess_job.id,
    }


@app.get("/documents/{document_id}/status")
async def get_document_status(document_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Return stable document preprocessing status."""
    _verify_course_access(document_id, current_user)
    return _document_status_payload(document_id)


@app.get("/api/documents/{document_id}/status")
async def get_api_document_status(document_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Return stable document preprocessing status under the API prefix."""
    _verify_course_access(document_id, current_user)
    return _document_status_payload(document_id)


@app.post("/documents/{document_id}/retry")
async def retry_document_status(document_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Retry document preprocessing from the saved upload files."""
    return _retry_document_preprocess(document_id, current_user)


@app.post("/api/documents/{document_id}/retry")
async def retry_api_document_status(document_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Retry document preprocessing from the saved upload files under the API prefix."""
    return _retry_document_preprocess(document_id, current_user)



@app.get("/documents/{document_id}/sources")
async def get_document_sources(
    document_id: str,
    ids: str = "",
    developer: bool = False,
    current_user: UserInDB = Depends(get_current_user),
):
    """Return clean source excerpts used for public grounding displays."""
    _verify_course_access(document_id, current_user)
    return _document_source_payload(document_id, ids=ids, developer=developer and current_user.role == "admin")


@app.get("/api/documents/{document_id}/sources")
async def get_api_document_sources(
    document_id: str,
    ids: str = "",
    developer: bool = False,
    current_user: UserInDB = Depends(get_current_user),
):
    """Return clean source excerpts under the API prefix."""
    _verify_course_access(document_id, current_user)
    return _document_source_payload(document_id, ids=ids, developer=developer and current_user.role == "admin")


@app.post("/api/generate-book")
async def generate_book(req: GenerateBookRequest, current_user: UserInDB = Depends(get_current_user)):
    """Generate the Book output and its downloadable PDF."""
    _verify_course_access(req.course_id, current_user)
    rag = _get_ready_course(req.course_id)
    profile = _resolve_profile(current_user, req.profile)
    result = rag.get_resource_generator().generate_book(req.user_prompt, req.target_audience, req.learning_mode, profile=profile)
    return {
        "course_id": req.course_id,
        "book": result.get("book", {}),
        "pdf_url": result.get("pdf_url", f"/api/course/{req.course_id}/book.pdf"),
    }


@app.post("/api/generate-slide")
async def generate_slide(req: GenerateSlideRequest, current_user: UserInDB = Depends(get_current_user)):
    """Generate the Slide output."""
    _verify_course_access(req.course_id, current_user)
    rag = _get_ready_course(req.course_id)
    profile = _resolve_profile(current_user, req.profile)
    result = rag.get_resource_generator().generate_slides_v2(req.topic, req.num_slides, req.learning_mode, profile=profile)
    slides = result.get("slides", [])
    return {
        "course_id": req.course_id,
        "topic": req.topic,
        "deck_title": result.get("deck_title"),
        "total_slides": len(slides),
        "slides": slides,
        "quality_report": result.get("quality_report"),
        "generation_status": result.get("generation_status"),
        "pptx_url": result.get("pptx_url", f"/api/course/{req.course_id}/slide.pptx"),
    }


@app.post("/api/generate-quiz")
async def generate_quiz(req: GenerateQuizRequest, current_user: UserInDB = Depends(get_current_user)):
    """Generate the Quiz output."""
    _verify_course_access(req.course_id, current_user)
    rag = _get_ready_course(req.course_id)
    profile = _resolve_profile(current_user, req.profile)
    result = rag.get_resource_generator().generate_quiz_v2(req.topic, req.quantity, req.difficulty, req.learning_mode, profile=profile)
    questions = result.get("questions", [])
    return {
        "course_id": req.course_id,
        "topic": req.topic,
        "difficulty": req.difficulty,
        "quiz_title": result.get("quiz_title"),
        "total_questions": len(questions),
        "questions": questions,
        "difficulty_mix": result.get("difficulty_mix"),
        "exam_pack": result.get("exam_pack"),
        "quality_report": result.get("quality_report"),
        "generation_status": result.get("generation_status"),
        "answer_key_url": result.get("answer_key_url", f"/api/course/{req.course_id}/quiz-key.pdf"),
    }


class RegenerateSceneRequest(BaseModel):
    scene_index: int
    video_index: Optional[int] = 1
    instruction: Optional[str] = None


class RenderPlaylistVideoRequest(BaseModel):
    video_index: int


@app.post("/api/generate-vid")
async def generate_vid(req: GenerateVidRequest, current_user: UserInDB = Depends(get_current_user)):
    """Generate the Vid output."""
    doc_id = req.get_document_id()
    if not doc_id:
        raise HTTPException(status_code=400, detail="Thiếu document_id hoặc course_id.")
    _verify_course_access(doc_id, current_user)
    rag = _get_ready_course(doc_id)
    profile = _resolve_profile(current_user, req.profile)
    result = rag.get_resource_generator().generate_vid(
        topic=req.topic or req.topic_id or "tổng quan",
        duration_minutes=req.duration_minutes,
        learning_mode=req.learning_mode,
        video_renderer=req.video_renderer,
        allow_renderer_fallback=req.allow_renderer_fallback,
        video_mode=req.video_mode,
        topic_id=req.topic_id,
        chapter_id=req.chapter_id,
        user_mode=req.user_mode,
        render_mp4=req.render_mp4,
        force=req.force,
        profile=profile,
    )
    return {"course_id": doc_id, "document_id": doc_id, "vid": result.get("vid", {})}


@app.post("/api/course/{course_id}/vid/scene/regenerate")
async def regenerate_vid_scene(course_id: str, req: RegenerateSceneRequest, current_user: UserInDB = Depends(get_current_user)):
    _verify_course_access(course_id, current_user)
    rag = _get_ready_course(course_id)
    result = rag.get_resource_generator().regenerate_video_scene(req.scene_index, req.video_index, req.instruction)
    return {"course_id": course_id, "vid": result.get("vid", {})}


@app.post("/api/course/{course_id}/vid/render")
async def render_playlist_vid(course_id: str, req: RenderPlaylistVideoRequest, current_user: UserInDB = Depends(get_current_user)):
    _verify_course_access(course_id, current_user)
    rag = _get_ready_course(course_id)
    result = rag.get_resource_generator().render_playlist_video(req.video_index)
    return {"course_id": course_id, "vid": result.get("vid", {})}


@app.get("/api/course/{course_id}/book")
async def get_saved_book(course_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Return the generated Book JSON."""
    _verify_course_access(course_id, current_user)
    paths = get_course_path(course_id)
    book = _read_json(paths["book"], "Chưa có Book cho tài liệu này.")
    return {
        "course_id": course_id,
        "book": book,
        "pdf_url": f"/api/course/{course_id}/book.pdf" if os.path.exists(paths["book_pdf"]) else None,
    }


@app.get("/api/course/{course_id}/book.pdf")
async def get_saved_book_pdf(course_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Return the generated Book PDF."""
    _verify_course_access(course_id, current_user)
    paths = get_course_path(course_id)
    if not os.path.exists(paths["book_pdf"]):
        if not os.path.exists(paths["book"]):
            raise HTTPException(404, "Sách PDF chưa được tạo. Vui lòng tạo sách trước.")
        rag = _get_ready_course(course_id)
        rag.get_resource_generator().export_book_pdf()

    return FileResponse(
        paths["book_pdf"],
        media_type="application/pdf",
        filename=f"study-guide-{course_id}.pdf",
    )


@app.get("/api/course/{course_id}/slide")
async def get_saved_slide(course_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Return the generated Slide JSON."""
    _verify_course_access(course_id, current_user)
    paths = get_course_path(course_id)
    payload = _read_json(paths["slides"], "Chưa có Slide cho tài liệu này.")
    slides = payload.get("slides", []) if isinstance(payload, dict) else payload
    return {
        "course_id": course_id,
        "slides": slides,
        "total_slides": len(slides),
        "quality_report": payload.get("quality_report") if isinstance(payload, dict) else None,
        "pptx_url": f"/api/course/{course_id}/slide.pptx" if os.path.exists(paths["slides_pptx"]) else None,
    }


@app.get("/api/course/{course_id}/slide.pptx")
async def download_saved_slide_pptx(course_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Download the generated Slide PPTX."""
    _verify_course_access(course_id, current_user)
    paths = get_course_path(course_id)
    if not os.path.exists(paths["slides_pptx"]):
        if not os.path.exists(paths["slides"]):
            raise HTTPException(404, "Chưa có Slide PPTX cho tài liệu này.")
        rag = _get_ready_course(course_id)
        rag.get_resource_generator().export_slides_pptx()
    return FileResponse(
        paths["slides_pptx"],
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"slide_{course_id}.pptx",
    )


@app.get("/api/course/{course_id}/slide.json")
async def download_saved_slide_json(course_id: str):
    """Deprecated: Slide JSON is an internal renderer artifact."""
    raise HTTPException(404, "Slide JSON không còn là public output.")


@app.get("/api/course/{course_id}/slide.pdf")
async def download_saved_slide_pdf(course_id: str):
    """Deprecated: Slide download is PPTX-only."""
    raise HTTPException(404, "Slide PDF đã được thay bằng PPTX.")


@app.get("/api/course/{course_id}/quiz")
async def get_saved_quiz(course_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Return the generated Quiz JSON."""
    _verify_course_access(course_id, current_user)
    paths = get_course_path(course_id)
    raw = _read_json(paths["questions"], None)
    if isinstance(raw, dict):
        questions = raw.get("questions") or []
        quiz_title = raw.get("quiz_title")
        difficulty_mix = raw.get("difficulty_mix")
        quality_report = raw.get("quality_report")
    else:
        # Legacy on-disk shape: a bare question list saved before the quiz schema upgrade.
        questions = raw if isinstance(raw, list) else []
        quiz_title = None
        difficulty_mix = None
        quality_report = None
    return {
        "course_id": course_id,
        "quiz_title": quiz_title,
        "questions": questions,
        "total_questions": len(questions),
        "difficulty_mix": difficulty_mix,
        "quality_report": quality_report,
        "answer_key_url": f"/api/course/{course_id}/quiz-key.pdf" if os.path.exists(paths["questions_key_pdf"]) else None,
    }


@app.get("/api/course/{course_id}/quiz-key.pdf")
async def download_saved_quiz_answer_key(course_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Download the generated Quiz answer key PDF."""
    _verify_course_access(course_id, current_user)
    paths = get_course_path(course_id)
    if not os.path.exists(paths["questions_key_pdf"]):
        if not os.path.exists(paths["questions"]):
            raise HTTPException(404, "Chưa có key đáp án Quiz cho tài liệu này.")
        rag = _get_ready_course(course_id)
        rag.get_resource_generator().export_quiz_answer_key_pdf()
    return FileResponse(paths["questions_key_pdf"], media_type="application/pdf", filename=f"quiz_key_{course_id}.pdf")


@app.get("/api/course/{course_id}/quiz.json")
async def download_saved_quiz_json(course_id: str):
    """Deprecated: Quiz JSON is an internal renderer artifact."""
    raise HTTPException(404, "Quiz JSON không còn là public output.")


@app.get("/api/course/{course_id}/quiz.pdf")
async def download_saved_quiz_pdf(course_id: str):
    """Deprecated: Quiz PDF was replaced by the answer key PDF."""
    raise HTTPException(404, "Quiz PDF đã được thay bằng file key đáp án.")


@app.get("/api/course/{course_id}/vid")
async def get_saved_vid(course_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Return the generated Vid metadata."""
    _verify_course_access(course_id, current_user)
    vid_path = os.path.join(get_course_path(course_id)["videos"], "vid.json")
    return {"course_id": course_id, "vid": _read_json(vid_path, "Chưa có Vid cho tài liệu này.")}


@app.get("/api/course/{course_id}/vid/file")
async def get_saved_vid_file(course_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Return the generated Vid MP4 file."""
    _verify_course_access(course_id, current_user)
    video_path = os.path.join(get_course_path(course_id)["videos"], "vid.mp4")
    if not os.path.exists(video_path):
        raise HTTPException(404, "Chưa có file Vid cho tài liệu này.")
    return FileResponse(video_path, media_type="video/mp4", filename=f"vid_{course_id}.mp4")


@app.get("/api/course/{course_id}/files")
async def get_course_files(course_id: str, current_user: UserInDB = Depends(get_current_user)):
    """List generated public artifacts for a course."""
    _verify_course_access(course_id, current_user)
    paths = get_course_path(course_id)
    files = {}

    for key in ["book", "book_pdf", "questions", "questions_key_pdf", "slides", "slides_pptx"]:
        if os.path.exists(paths[key]):
            files[key] = paths[key]

    video_dir = paths["videos"]
    if os.path.exists(video_dir):
        files["vid"] = sorted(os.listdir(video_dir))

    return {"course_id": course_id, "files": files}


def _compute_course_stats(course_id: str) -> dict:
    """Build artifact availability stats. Internal helper shared by the /stats route
    and get_study_pack — callers are responsible for their own auth/ownership checks."""
    mgr = _get_course_manager()
    if not mgr.contains(course_id):
        raise HTTPException(404, f"Không tìm thấy tài liệu '{course_id}'.")

    paths = get_course_path(course_id)
    idx_stats = get_index_stats(course_id)
    doc_quality = idx_stats.get("document_quality_report")
    if not doc_quality:
        meta_path = paths["meta"]
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                doc_quality = meta.get("document_quality_report") or (meta.get("preprocess_profile") or {}).get("document_quality_report")
            except Exception:
                pass

    num_chunks = idx_stats.get("num_chunks") or 0
    num_chunks_before = idx_stats.get("num_chunks_before_filter") or num_chunks
    noisy_chunks_removed = max(0, num_chunks_before - num_chunks)
    num_chars = idx_stats.get("num_extracted_chars") or 0
    quality_score = doc_quality["quality_score"] if doc_quality and "quality_score" in doc_quality else (85 if (num_chars > 1000 or num_chunks >= 5) else (70 if num_chunks > 0 else 50))

    stats = {
        "course_id": course_id,
        "status": mgr.get_course_status(course_id),
        "generated_at": _timestamp(),
        "has_book": os.path.exists(paths["book"]),
        "has_book_pdf": os.path.exists(paths["book_pdf"]),
        "has_slide": os.path.exists(paths["slides"]),
        "has_slide_pptx": os.path.exists(paths["slides_pptx"]),
        "has_quiz": os.path.exists(paths["questions"]),
        "has_quiz_answer_key": os.path.exists(paths["questions_key_pdf"]),
        "has_vid": os.path.exists(os.path.join(paths["videos"], "vid.json")),
        "has_mindmap": os.path.exists(paths["mindmap"]),
        "has_flashcards": os.path.exists(paths["flashcards"]),
        "num_chunks": num_chunks,
        "noisy_chunks_removed": noisy_chunks_removed,
        "quality_score": quality_score,
        "is_university_ready": quality_score >= 80,
        "document_quality_report": doc_quality,
        "pdf_type": doc_quality.get("pdf_type") if doc_quality else None,
        "warnings": doc_quality.get("warnings", []) if doc_quality else [],
        "recommended_action": doc_quality.get("recommended_action") if doc_quality else "generate",
    }

    if stats["has_quiz"]:
        try:
            with open(paths["questions"], "r", encoding="utf-8") as f:
                quiz_raw_stats = json.load(f)
            questions_stats = (
                quiz_raw_stats.get("questions", [])
                if isinstance(quiz_raw_stats, dict)
                else (quiz_raw_stats if isinstance(quiz_raw_stats, list) else [])
            )
            stats["total_questions"] = len(questions_stats)
        except Exception:
            stats["total_questions"] = 0

    if stats["has_slide"]:
        try:
            with open(paths["slides"], "r", encoding="utf-8") as f:
                stats["total_slides"] = len(json.load(f))
        except Exception:
            stats["total_slides"] = 0

    return stats


@app.get("/api/course/{course_id}/stats")
async def get_course_stats(course_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Return basic artifact availability stats."""
    _verify_course_access(course_id, current_user)
    return _compute_course_stats(course_id)




def _get_generator_for_readiness(course_id: str):
    """Resolve a resource generator for readiness/fallback checks.

    Tolerant of courses that are still processing or evicted from the in-memory
    cache: readiness should be checkable on whatever vector data already exists
    on disk, not only on fully "ready" courses.
    """
    mgr = _get_course_manager()
    rag = mgr.get_course(course_id)
    if not rag:
        raise HTTPException(404, f"Không tìm thấy tài liệu '{course_id}' hoặc dữ liệu vector chưa sẵn sàng.")
    return rag.get_resource_generator()


def _resolve_profile(current_user: UserInDB, explicit: Optional[dict] = None) -> Optional[dict]:
    """Resolve which Learning Profile a generation call should use: an explicit
    per-request override takes priority, otherwise fall back to the user's saved
    profile (set via onboarding/settings). None if the user has never set one."""
    return explicit or current_user.learning_profile

class FallbackGenerateRequest(BaseModel):
    fallback_type: str
    title: Optional[str] = "Bản học dự phòng"


class ProfileOverrideRequest(BaseModel):
    """Optional body for endpoints (mindmap/flashcards regenerate) that otherwise take
    no request body — lets a caller override the user's saved Learning Profile for
    just this one regeneration."""

    profile: Optional[dict[str, Any]] = None


@app.get("/api/course/{course_id}/readiness")
async def get_course_readiness(course_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Evaluate context quality and return per-output readiness report."""
    _verify_course_access(course_id, current_user)
    try:
        generator = _get_generator_for_readiness(course_id)
        report = generator.evaluate_readiness()
        return report
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to evaluate generation readiness", "detail": str(e)}
        )


@app.post("/api/course/{course_id}/generate-fallback")
async def generate_fallback_output(course_id: str, payload: FallbackGenerateRequest, current_user: UserInDB = Depends(get_current_user)):
    """Generate grounded safe fallback content when full generation is blocked."""
    _verify_course_access(course_id, current_user)
    try:
        generator = _get_generator_for_readiness(course_id)
        docs = []
        if hasattr(generator, "vectorstore") and generator.vectorstore:
            try:
                retriever = generator.vectorstore.as_retriever(search_kwargs={"k": 32})
                docs = retriever.invoke("tổng quan")
            except Exception:
                docs = []
                
        profile = current_user.learning_profile
        ftype = payload.fallback_type.lower()
        if ftype in ("summary", "short_summary"):
            data = generator.generate_fallback_summary(payload.title or "Tóm tắt tài liệu", docs, profile=profile)
        elif ftype in ("high_yield", "high_yield_notes"):
            data = generator.generate_fallback_high_yield(payload.title or "Bản học trọng tâm", docs, profile=profile)
        elif ftype in ("outline", "document_outline"):
            data = generator.generate_fallback_outline(payload.title or "Dàn ý tài liệu", docs)
        elif ftype in ("key_terms", "flashcards"):
            data = generator.generate_fallback_key_terms(payload.title or "Thuật ngữ chính", docs)
        elif ftype in ("shallow_mindmap", "mindmap", "shallow_concept_map"):
            data = generator.generate_fallback_shallow_mindmap(payload.title or "Sơ đồ khái niệm", docs)
        elif ftype in ("short_video_script", "video_script", "short_60_second_script"):
            data = generator.generate_fallback_short_video_script(payload.title or "Kịch bản video ngắn", docs)
        elif ftype in ("storyboard_only", "storyboard"):
            data = generator.generate_fallback_storyboard_only(payload.title or "Storyboard video", docs)
        else:
            return JSONResponse(
                status_code=400,
                content={"error": f"Unsupported fallback type: {payload.fallback_type}"}
            )
            
        return {
            "status": "success",
            "course_id": course_id,
            "fallback_type": ftype,
            "result": data,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to generate fallback output", "detail": str(e)}
        )


@app.get("/api/course/{course_id}/study-pack")
async def get_study_pack(course_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Return the complete grounded Study Pack derived from the structured book/notes."""
    _verify_course_access(course_id, current_user)
    stats = _compute_course_stats(course_id)
    paths = get_course_path(course_id)

    book = _read_json(paths["book"], "Chưa có Sách cho tài liệu này.") if os.path.exists(paths["book"]) else None
    quiz_raw = _read_json(paths["questions"], None) if os.path.exists(paths["questions"]) else None
    # paths["questions"] holds an object ({quiz_title, questions, ...}) since the quiz schema
    # upgrade; coerce back to the flat question list this endpoint has always exposed.
    quiz_data = quiz_raw.get("questions", []) if isinstance(quiz_raw, dict) else (quiz_raw if isinstance(quiz_raw, list) else [])

    summary_items = []
    flashcards_list = []

    if isinstance(book, dict):
        chapters = book.get("chapters", [])
        for c_idx, chapter in enumerate(chapters):
            c_title = chapter.get("title", f"Chương {c_idx+1}")
            sections = chapter.get("lessons") or chapter.get("sections") or []
            for s_idx, sec in enumerate(sections):
                s_title = sec.get("title") or sec.get("short_name") or f"Phần {s_idx+1}"
                qc = sec.get("quick_check", [])
                core_ans = qc[0].get("answer") if qc and isinstance(qc, list) and len(qc) > 0 else ""
                if core_ans:
                    summary_items.append({"topic": s_title, "chapter": c_title, "content": core_ans})
                elif sec.get("content"):
                    summary_items.append({"topic": s_title, "chapter": c_title, "content": sec.get("content")[:200].rstrip(". ") + "…"})

                fcs = sec.get("flashcards", [])
                if isinstance(fcs, list):
                    for fc in fcs:
                        if isinstance(fc, dict) and fc.get("front") and fc.get("back"):
                            flashcards_list.append({
                                "front": fc["front"],
                                "back": fc["back"],
                                "chapter": c_title
                            })

    mindmap_data = None
    if os.path.exists(paths.get("mindmap", "")):
        mindmap_data = _read_json(paths["mindmap"], None)
    
    if not mindmap_data and isinstance(book, dict):
        try:
            mindmap_data = _get_generator_for_readiness(course_id).build_mindmap_from_book(book)
        except Exception as e:
            logger.warning(f"[StudyPack] Failed to build mindmap from book: {e}")

    if not mindmap_data:
        mindmap_data = {"title": course_id, "root": {"id": "root", "title": course_id, "children": []}, "nodes": [], "edges": []}

    # Prefer the dedicated flashcard deck (real card_type/difficulty/concept_tags) over the
    # book-lesson lookup above (which is effectively always empty) or the quiz-derived guess below.
    if os.path.exists(paths.get("flashcards", "")):
        flashcards_deck = _read_json(paths["flashcards"], None)
        deck_cards = flashcards_deck.get("cards") if isinstance(flashcards_deck, dict) else None
        if isinstance(deck_cards, list) and deck_cards:
            flashcards_list = [
                {
                    "id": c.get("id"),
                    "front": c.get("front", ""),
                    "back": c.get("back", ""),
                    "chapter": (c.get("concept_tags") or ["Flashcards"])[0],
                    "card_type": c.get("card_type"),
                    "difficulty": c.get("difficulty"),
                    "source_chunk_ids": c.get("source_chunk_ids", []),
                }
                for c in deck_cards
                if isinstance(c, dict) and c.get("front") and c.get("back")
            ]

    # If no flashcards in book sections, derive from quiz if available
    if not flashcards_list and isinstance(quiz_data, list):
        for q in quiz_data[:15]:
            if isinstance(q, dict) and q.get("question") and q.get("explanation"):
                flashcards_list.append({
                    "front": q["question"],
                    "back": q["explanation"],
                    "chapter": "Quiz Review"
                })

    readiness = {
        "study_guide_pdf": stats.get("has_book_pdf", False) or stats.get("has_book", False),
        "mindmap": isinstance(mindmap_data, dict) and (len(mindmap_data.get("nodes", [])) > 0 or len(mindmap_data.get("root", {}).get("children", [])) > 0),
        "quiz": stats.get("has_quiz", False),
        "flashcards": len(flashcards_list) > 0,
        "summary": len(summary_items) > 0,
    }

    base_score = stats.get("quality_score", 85)
    quality_scores = {
        "study_guide_pdf": book.get("quality_report", {}).get("score", base_score) if isinstance(book, dict) else base_score,
        "mindmap": mindmap_data.get("quality_report", {}).get("score", min(100, base_score + 2)) if isinstance(mindmap_data, dict) else min(100, base_score + 2),
        "quiz": 92 if stats.get("has_quiz") else base_score,
        "flashcards": min(100, base_score + 4),
        "summary": min(100, base_score + 3),
    }

    return {
        "course_id": course_id,
        "stats": stats,
        "study_pack": {
            "title": book.get("title", course_id) if isinstance(book, dict) else course_id,
            "summary": summary_items,
            "mindmap": mindmap_data,
            "flashcards": flashcards_list,
            "book": book if isinstance(book, dict) else None,
            "quiz": quiz_data,
            "readiness": readiness,
            "quality_scores": quality_scores,
            "grounding": {
                "num_chunks": stats.get("num_chunks", 0),
                "quality_score": base_score,
                "warnings": stats.get("warnings", []),
            },
        },
    }


@app.get("/api/course/{course_id}/mindmap")
async def get_course_mindmap(course_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Return the 3-level interactive mindmap for a course."""
    _verify_course_access(course_id, current_user)
    paths = get_course_path(course_id)
    if os.path.exists(paths.get("mindmap", "")):
        mindmap = _read_json(paths["mindmap"], None)
        if mindmap and isinstance(mindmap, dict):
            return mindmap

    gen = _get_generator_for_readiness(course_id)
    mindmap = gen.regenerate_mindmap(force_llm=False, profile=current_user.learning_profile)
    return mindmap


@app.post("/api/course/{course_id}/mindmap/regenerate")
async def regenerate_course_mindmap(
    course_id: str, req: Optional[ProfileOverrideRequest] = None, current_user: UserInDB = Depends(get_current_user)
):
    """Regenerate the 3-level interactive mindmap using clean chunks or book plan."""
    _verify_course_access(course_id, current_user)
    gen = _get_generator_for_readiness(course_id)
    profile = _resolve_profile(current_user, (req.profile if req else None))
    mindmap = gen.regenerate_mindmap(force_llm=True, profile=profile)
    return mindmap


@app.get("/api/course/{course_id}/flashcards")
async def get_course_flashcards(course_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Return the saved flashcard deck for a course, generating it on first request."""
    _verify_course_access(course_id, current_user)
    paths = get_course_path(course_id)
    if os.path.exists(paths.get("flashcards", "")):
        deck = _read_json(paths["flashcards"], None)
        if deck and isinstance(deck, dict):
            return deck

    gen = _get_generator_for_readiness(course_id)
    return gen.generate_flashcards_v2(profile=current_user.learning_profile)


@app.post("/api/course/{course_id}/flashcards/regenerate")
async def regenerate_course_flashcards(
    course_id: str, req: Optional[ProfileOverrideRequest] = None, current_user: UserInDB = Depends(get_current_user)
):
    """Regenerate the flashcard deck from clean chunks."""
    _verify_course_access(course_id, current_user)
    gen = _get_generator_for_readiness(course_id)
    profile = _resolve_profile(current_user, (req.profile if req else None))
    return gen.generate_flashcards_v2(profile=profile)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
