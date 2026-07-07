"""Generation Service router for AI Course Generator."""

import os
from typing import Any, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.course import Course
from app.models.user import User
from app.schemas.generation import (
    GenerateRequest,
    GenerateResponse,
    StudyPackResponse,
)
from app.services.generator import Generator
from app.services.llm import LLMService
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/api/courses", tags=["generation"])
router_single = APIRouter(prefix="/api/course", tags=["generation"])
router_generate = APIRouter(prefix="/api", tags=["generation"])

_generator_instance = None


def get_generator() -> Generator:
    """Singleton helper to get Generator instance."""
    global _generator_instance
    if _generator_instance is None:
        vs = get_vector_store()
        llm = LLMService()
        _generator_instance = Generator(vs, llm)
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
    req: Optional[GenerateRequest] = None,
    course_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Trigger background generation for Book artifact."""
    course = resolve_and_validate_course(req, course_id, current_user, db)
    generator = get_generator()
    background_tasks.add_task(generator.generate_book, course.id)
    return GenerateResponse(course_id=course.id)


@router_generate.post("/generate-slide", response_model=GenerateResponse)
def generate_slide(
    background_tasks: BackgroundTasks,
    req: Optional[GenerateRequest] = None,
    course_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Trigger background generation for Slide artifact."""
    course = resolve_and_validate_course(req, course_id, current_user, db)
    generator = get_generator()
    background_tasks.add_task(generator.generate_slides, course.id)
    return GenerateResponse(course_id=course.id)


@router_generate.post("/generate-quiz", response_model=GenerateResponse)
def generate_quiz(
    background_tasks: BackgroundTasks,
    req: Optional[GenerateRequest] = None,
    course_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Trigger background generation for Quiz artifact."""
    course = resolve_and_validate_course(req, course_id, current_user, db)
    generator = get_generator()
    background_tasks.add_task(generator.generate_quiz, course.id)
    return GenerateResponse(course_id=course.id)


@router_generate.post("/generate-vid", response_model=GenerateResponse)
def generate_vid(
    background_tasks: BackgroundTasks,
    req: Optional[GenerateRequest] = None,
    course_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Trigger background generation for Video artifact."""
    course = resolve_and_validate_course(req, course_id, current_user, db)
    generator = get_generator()
    background_tasks.add_task(generator.generate_vid, course.id)
    return GenerateResponse(course_id=course.id)


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
    """Retrieve Book artifact JSON (returns null if not generated yet)."""
    get_valid_course(course_id, current_user, db)
    generator = get_generator()
    return generator._load_artifact_json(course_id, "book.json")


@router_single.get("/{course_id}/slide", response_model=Any)
@router.get("/{course_id}/slide", response_model=Any)
def get_slide(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve Slide artifact JSON (returns null if not generated yet)."""
    get_valid_course(course_id, current_user, db)
    generator = get_generator()
    return generator._load_artifact_json(course_id, "slides.json")


@router_single.get("/{course_id}/quiz", response_model=Any)
@router.get("/{course_id}/quiz", response_model=Any)
def get_quiz(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve Quiz artifact JSON (returns empty list [] if not generated yet)."""
    get_valid_course(course_id, current_user, db)
    generator = get_generator()
    data = generator._load_artifact_json(course_id, "quiz.json")
    return data.get("questions", []) if data else []


@router_single.get("/{course_id}/vid", response_model=Any)
@router.get("/{course_id}/vid", response_model=Any)
def get_vid(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve Video artifact JSON (returns null if not generated yet)."""
    get_valid_course(course_id, current_user, db)
    generator = get_generator()
    return generator._load_artifact_json(course_id, "vid.json")


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


@router_single.get("/{course_id}/vid/file")
@router.get("/{course_id}/vid/file")
def download_vid_file(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Download Video Script file."""
    get_valid_course(course_id, current_user, db)
    file_path = os.path.join(settings.UPLOAD_DIR, course_id, "artifacts", "vid_script.txt")
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="text/plain",
            filename=f"vid_script_{course_id}.txt",
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Chưa có file video cho tài liệu này.",
    )
