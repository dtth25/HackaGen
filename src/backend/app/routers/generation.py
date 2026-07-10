"""Generation Service router for HackaGen."""

import os
from typing import Any, Dict, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.course import Course
from app.models.user import User
from app.schemas.generation import (
    BookGenerateRequest,
    GenerateRequest,
    GenerateResponse,
    QuizGenerateRequest,
    SlideGenerateRequest,
    StudyPackResponse,
    VidGenerateRequest,
)
from app.services.generator import MAX_REGENERATIONS, Generator
from app.services.llm import LLMService
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/api/courses", tags=["generation"])
router_single = APIRouter(prefix="/api/course", tags=["generation"])
router_generate = APIRouter(prefix="/api", tags=["generation"])
router_docs = APIRouter(tags=["generation"])

_generator_instance = None


def get_generator() -> Generator:
    """Singleton helper to get Generator instance.

    Each of the 4 generation features (Book/Slide/Quiz/Vid) can be configured with its own
    Gemini API key (GEMINI_{BOOK,SLIDE,QUIZ,VID}_API_KEY), falling back to the shared
    GEMINI_API_KEY when a feature-specific key isn't set.
    """
    global _generator_instance
    if _generator_instance is None:
        vs = get_vector_store()
        llm = LLMService()
        # Only spin up a separate client for a feature that actually has its own key
        # configured — otherwise reuse the shared `llm` instance instead of creating
        # redundant genai.Client objects that all fall back to the same GEMINI_API_KEY.
        feature_keys = {
            "book": settings.GEMINI_BOOK_API_KEY,
            "slides": settings.GEMINI_SLIDE_API_KEY,
            "quiz": settings.GEMINI_QUIZ_API_KEY,
            "vid": settings.GEMINI_VID_API_KEY,
        }
        feature_llms = {
            feature: LLMService(api_key=key) if key else llm
            for feature, key in feature_keys.items()
        }
        _generator_instance = Generator(vs, llm, feature_llms)
    return _generator_instance


def get_valid_course(course_id: str, current_user: User, db: Session) -> Course:
    """Validate course existence and ownership."""
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.is_deleted == False)  # noqa: E712
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Khóa học không tồn tại."
        )

    if course.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Khóa học không tồn tại."
        )

    return course


def resolve_and_validate_course(
    req: Optional[GenerateRequest],
    query_course_id: Optional[str],
    current_user: User,
    db: Session,
) -> Course:
    """Resolve course_id from JSON body or query param and validate ownership."""
    cid = (req and req.course_id) or query_course_id
    if not cid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thiếu course_id trong yêu cầu.",
        )
    return get_valid_course(cid, current_user, db)


def check_regen_or_raise(generator: Generator, course_id: str, artifact: str) -> tuple[int, int]:
    """Enforce the regeneration cap (Generator.MAX_REGENERATIONS) before queueing a
    generate-* background task. The first generation of an artifact is always allowed and
    free; only re-triggers after it already reached "ready"/"error" count against the cap.
    Raises 429 once exhausted. Returns (regen_used, regen_max) for the response envelope."""
    allowed, used, max_allowed = generator.check_and_record_regen_attempt(course_id, artifact)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Đã đạt giới hạn {max_allowed} lần tạo lại cho mục này.",
        )
    return used, max_allowed


def regen_fields(generator: Generator, course_id: str, artifact: str) -> Dict[str, int]:
    """Regen usage fields for an artifact-status envelope, so the frontend knows how many
    regenerations remain without a separate study-pack round-trip."""
    used = generator.get_regen_usage(course_id).get(artifact, 0)
    return {"regen_used": used, "regen_max": MAX_REGENERATIONS}


# =====================================================================
# 1. Study Pack Endpoint
# =====================================================================


@router_single.get("/{course_id}/study-pack", response_model=StudyPackResponse)
@router.get("/{course_id}/study-pack", response_model=StudyPackResponse)
def get_study_pack(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Return actual study pack data for the specified course."""
    get_valid_course(course_id, current_user, db)
    generator = get_generator()
    return generator.get_study_pack(course_id)


# =====================================================================
# 2. Generate Endpoints (trigger background AI generation)
# =====================================================================


@router_generate.post("/generate-book", response_model=GenerateResponse)
def generate_book(
    background_tasks: BackgroundTasks,
    req: Optional[BookGenerateRequest] = None,
    course_id: Optional[str] = Query(None),
    user_prompt: Optional[str] = Query(None),
    detail_level: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Trigger background generation for Book artifact."""
    course = resolve_and_validate_course(req, course_id, current_user, db)
    prompt = (req and req.user_prompt) or user_prompt or ""
    detail = (req and req.detail_level) or detail_level or "Tiêu chuẩn"
    generator = get_generator()
    regen_used, regen_max = check_regen_or_raise(generator, course.id, "book")
    background_tasks.add_task(generator.generate_book, course.id, detail_level=detail, user_prompt=prompt)
    return GenerateResponse(course_id=course.id, regen_used=regen_used, regen_max=regen_max)


@router_generate.post("/generate-slide", response_model=GenerateResponse)
def generate_slide(
    background_tasks: BackgroundTasks,
    req: Optional[SlideGenerateRequest] = None,
    course_id: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    num_slides: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Trigger background generation for Slide artifact."""
    course = resolve_and_validate_course(req, course_id, current_user, db)
    t = (req and req.topic) or topic
    n = (req and req.num_slides) or num_slides or 15
    generator = get_generator()
    regen_used, regen_max = check_regen_or_raise(generator, course.id, "slides")
    background_tasks.add_task(generator.generate_slides, course.id, topic=t, num_slides=n)
    return GenerateResponse(course_id=course.id, regen_used=regen_used, regen_max=regen_max)


@router_generate.post("/generate-quiz", response_model=GenerateResponse)
def generate_quiz(
    background_tasks: BackgroundTasks,
    req: Optional[QuizGenerateRequest] = None,
    course_id: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    quantity: Optional[int] = Query(None),
    difficulty: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Trigger background generation for Quiz artifact."""
    course = resolve_and_validate_course(req, course_id, current_user, db)
    t = (req and req.topic) or topic
    q = (req and req.quantity) or quantity or 5
    d = (req and req.difficulty) or difficulty or "medium"
    generator = get_generator()
    regen_used, regen_max = check_regen_or_raise(generator, course.id, "quiz")
    background_tasks.add_task(generator.generate_quiz, course.id, topic=t, quantity=q, difficulty=d)
    return GenerateResponse(course_id=course.id, regen_used=regen_used, regen_max=regen_max)


@router_generate.post("/generate-vid", response_model=GenerateResponse)
def generate_vid(
    background_tasks: BackgroundTasks,
    req: Optional[VidGenerateRequest] = None,
    course_id: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    format: Optional[str] = Query(None),
    voice: Optional[str] = Query(None),
    user_prompt: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Trigger background generation for the narrated Video artifact."""
    course = resolve_and_validate_course(req, course_id, current_user, db)
    t = (req and req.topic) or topic
    fmt = (req and req.format) or format or "standard"
    v = (req and req.voice) or voice or "female"
    up = (req and req.user_prompt) or user_prompt or ""
    generator = get_generator()
    regen_used, regen_max = check_regen_or_raise(generator, course.id, "vid")
    background_tasks.add_task(generator.generate_vid, course.id, topic=t, fmt=fmt, voice=v, user_prompt=up)
    return GenerateResponse(course_id=course.id, estimated_time="3-5 minutes", regen_used=regen_used, regen_max=regen_max)


# =====================================================================
# 3. Artifact Retrieval Endpoints
# =====================================================================


@router_single.get("/{course_id}/book", response_model=Any)
@router.get("/{course_id}/book", response_model=Any)
def get_book(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve Book artifact status envelope: {status, error, progress, data}.

    status is one of "empty" | "processing" | "ready" | "error". `data` never leaks
    raw source_chunk_ids (grounding metadata), matching the no-raw-metadata invariant.
    """
    get_valid_course(course_id, current_user, db)
    generator = get_generator()
    data = generator._load_artifact_json(course_id, "book.json")
    info = generator.get_artifact_status(course_id, "book")
    status_val = info.get("status") or ("ready" if data else "empty")
    if status_val == "ready" and data is None:
        status_val = "empty"
    if data:
        for ch in data.get("chapters", []):
            ch.pop("source_chunk_ids", None)
    return {
        "status": status_val,
        "error": info.get("error"),
        "progress": info.get("progress"),
        "data": data,
        **regen_fields(generator, course_id, "book"),
    }


@router_single.get("/{course_id}/slide", response_model=Any)
@router.get("/{course_id}/slide", response_model=Any)
def get_slide(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve Slide artifact status envelope: {status, error, progress, data}.

    status is one of "empty" | "processing" | "ready" | "error". `data` never leaks
    raw source_chunk_ids (grounding metadata), matching the no-raw-metadata invariant.
    """
    get_valid_course(course_id, current_user, db)
    generator = get_generator()
    data = generator._load_artifact_json(course_id, "slides.json")
    info = generator.get_artifact_status(course_id, "slides")
    status_val = info.get("status") or ("ready" if data else "empty")
    if status_val == "ready" and data is None:
        status_val = "empty"
    if data:
        for sl in data.get("slides", []):
            sl.pop("source_chunk_ids", None)
    return {
        "status": status_val,
        "error": info.get("error"),
        "progress": info.get("progress"),
        "data": data,
        **regen_fields(generator, course_id, "slides"),
    }


@router_single.get("/{course_id}/quiz", response_model=Any)
@router.get("/{course_id}/quiz", response_model=Any)
def get_quiz(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve Quiz artifact status envelope: {status, error, progress, data}.

    status is one of "empty" | "processing" | "ready" | "error". `data` is the list of
    questions (or null) and never leaks raw source_chunk_ids (grounding metadata).
    """
    get_valid_course(course_id, current_user, db)
    generator = get_generator()
    raw = generator._load_artifact_json(course_id, "quiz.json")
    questions = raw.get("questions", []) if raw else None
    if questions:
        for q in questions:
            q.pop("source_chunk_ids", None)
    info = generator.get_artifact_status(course_id, "quiz")
    status_val = info.get("status") or ("ready" if questions else "empty")
    if status_val == "ready" and not questions:
        status_val = "empty"
    return {
        "status": status_val,
        "error": info.get("error"),
        "progress": info.get("progress"),
        "data": questions,
        **regen_fields(generator, course_id, "quiz"),
    }


@router_single.get("/{course_id}/vid", response_model=Any)
@router.get("/{course_id}/vid", response_model=Any)
def get_vid(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve Video artifact status envelope: {status, error, progress, data}.

    status is one of "empty" | "processing" | "ready" | "error". `data` never leaks
    raw source_chunk_ids (grounding metadata), matching the no-raw-metadata invariant.
    """
    get_valid_course(course_id, current_user, db)
    generator = get_generator()
    data = generator._load_artifact_json(course_id, "vid.json")
    info = generator.get_artifact_status(course_id, "vid")
    status_val = info.get("status") or ("ready" if data else "empty")
    if status_val == "ready" and data is None:
        status_val = "empty"
    if data:
        for sc in data.get("scenes", []):
            sc.pop("source_chunk_ids", None)
    return {
        "status": status_val,
        "error": info.get("error"),
        "progress": info.get("progress"),
        "data": data,
        **regen_fields(generator, course_id, "vid"),
    }


# =====================================================================
# 4. Download Endpoints (serve generated files or 404)
# =====================================================================


@router_single.get("/{course_id}/book.pdf")
@router.get("/{course_id}/book.pdf")
def download_book_pdf(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Download Book Study Guide PDF."""
    get_valid_course(course_id, current_user, db)
    file_path = os.path.join(settings.UPLOAD_DIR, course_id, "artifacts", "book.pdf")
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="application/pdf",
            filename=f"study_guide_{course_id}.pdf",
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Chưa có file PDF cho tài liệu này.",
    )


@router_single.get("/{course_id}/slide.pptx")
@router.get("/{course_id}/slide.pptx")
def download_slide_pptx(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Download Slide PPTX presentation."""
    get_valid_course(course_id, current_user, db)
    file_path = os.path.join(settings.UPLOAD_DIR, course_id, "artifacts", "slide.pptx")
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=f"slides_{course_id}.pptx",
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Chưa có file bài giảng PPTX cho tài liệu này.",
    )


@router_single.get("/{course_id}/slide.pdf")
@router.get("/{course_id}/slide.pdf")
def download_slide_pdf(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Download Slide presentation as a 16:9 PDF."""
    get_valid_course(course_id, current_user, db)
    file_path = os.path.join(settings.UPLOAD_DIR, course_id, "artifacts", "slide.pdf")
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="application/pdf",
            filename=f"slides_{course_id}.pdf",
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Chưa có file bài giảng PDF cho tài liệu này.",
    )


@router_single.get("/{course_id}/slide-images/{slide_num}")
@router.get("/{course_id}/slide-images/{slide_num}")
def get_slide_image(
    course_id: str,
    slide_num: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Get slide image by slide number."""
    get_valid_course(course_id, current_user, db)
    file_path = os.path.join(settings.UPLOAD_DIR, course_id, "artifacts", f"slide_{slide_num}.png")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/png")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Không tìm thấy ảnh slide tương ứng.",
    )


@router_single.get("/{course_id}/quiz-key.pdf")
@router.get("/{course_id}/quiz-key.pdf")
def download_quiz_key_pdf(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Download Quiz Answer Key PDF."""
    get_valid_course(course_id, current_user, db)
    file_path = os.path.join(settings.UPLOAD_DIR, course_id, "artifacts", "quiz-key.pdf")
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="application/pdf",
            filename=f"quiz_key_{course_id}.pdf",
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Chưa có file đáp án trắc nghiệm PDF cho tài liệu này.",
    )


@router_single.get("/{course_id}/vid.mp4")
@router.get("/{course_id}/vid.mp4")
def download_vid_mp4(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Download/stream the narrated Video MP4 (FileResponse supports Range for <video> seeking)."""
    get_valid_course(course_id, current_user, db)
    file_path = os.path.join(settings.UPLOAD_DIR, course_id, "artifacts", "vid.mp4")
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="video/mp4",
            filename=f"video_{course_id}.mp4",
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Chưa có file video cho tài liệu này.",
    )


@router_single.get("/{course_id}/vid/file")
@router.get("/{course_id}/vid/file")
def download_vid_transcript(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Download the Video narration transcript (.txt)."""
    get_valid_course(course_id, current_user, db)
    file_path = os.path.join(settings.UPLOAD_DIR, course_id, "artifacts", "transcript.txt")
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="text/plain",
            filename=f"transcript_{course_id}.txt",
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Chưa có bản lời thoại (transcript) cho video này.",
    )


@router_single.get("/{course_id}/vid.srt")
@router.get("/{course_id}/vid.srt")
def download_vid_srt(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Download the Video subtitle file (.srt)."""
    get_valid_course(course_id, current_user, db)
    file_path = os.path.join(settings.UPLOAD_DIR, course_id, "artifacts", "vid.srt")
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="application/x-subrip",
            filename=f"video_{course_id}.srt",
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Chưa có file phụ đề cho video này.",
    )


@router_docs.get("/documents/{document_id}/sources")
@router_docs.get("/api/documents/{document_id}/sources")
def get_sources(
    document_id: str,
    ids: Optional[str] = Query(None),
    developer: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Stable source-grounding endpoint for UI panels."""
    get_valid_course(document_id, current_user, db)
    vs = get_vector_store()
    stats = vs.get_course_stats(document_id)
    total_chunks = stats.get("chunk_count", 0)

    target_ids = [cid.strip() for cid in ids.split(",") if cid.strip()] if ids else None
    docs = vs.get_course_chunks(document_id, target_ids)

    sources = []
    for doc in docs:
        page_val = doc.metadata.get("page", 1)
        try:
            page_num = int(page_val)
        except (ValueError, TypeError):
            page_num = 1

        excerpt = doc.content
        if len(excerpt) > 300:
            excerpt = excerpt[:300] + "..."

        item = {
            "page": page_num,
            "excerpt": excerpt,
        }
        if developer and current_user.role == "admin":
            item["source_chunk_id"] = doc.metadata.get("chunk_id", "")
        sources.append(item)

    return {
        "document_id": document_id,
        "total_source_chunks": total_chunks,
        "matched_source_chunks": len(sources),
        "sources": sources,
    }




