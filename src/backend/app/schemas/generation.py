"""Pydantic schemas for Generation Service Skeleton."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Request payload for generating study artifacts."""

    course_id: Optional[str] = Field(
        None, description="ID of the course to generate artifacts for"
    )


class BookGenerateRequest(BaseModel):
    """Request payload for generating Book / Study Guide."""

    course_id: Optional[str] = None
    user_prompt: Optional[str] = ""
    detail_level: Optional[str] = "Tiêu chuẩn"


class SlideGenerateRequest(BaseModel):
    """Request payload for generating Presentation Slides."""

    course_id: Optional[str] = None
    topic: Optional[str] = "AI Overview"
    num_slides: Optional[int] = 15


class QuizGenerateRequest(BaseModel):
    """Request payload for generating Quiz."""

    course_id: Optional[str] = None
    topic: Optional[str] = "AI Quiz"
    quantity: Optional[int] = 5
    difficulty: Optional[str] = "medium"


class VidGenerateRequest(BaseModel):
    """Request payload for generating Video Script."""

    course_id: Optional[str] = None
    topic: Optional[str] = "AI Video"
    duration_minutes: Optional[int] = 5
    learning_mode: Optional[str] = "normal"
    video_renderer: Optional[str] = "simple_templates"
    allow_renderer_fallback: Optional[bool] = True


class GenerateResponse(BaseModel):
    """Response payload for generation request."""

    course_id: str
    status: str = "queued"
    message: str = "Generation started..."
    estimated_time: str = "2 minutes"


class ReadinessData(BaseModel):
    """Study pack artifact readiness flags."""

    study_guide_pdf: bool = False
    slides: bool = False
    quiz: bool = False
    vid: bool = False


class QualityScoresData(BaseModel):
    """Study pack artifact quality scores."""

    study_guide_pdf: int = 0
    slides: int = 0
    quiz: int = 0
    vid: int = 0


class GroundingData(BaseModel):
    """Grounding metrics and warnings."""

    num_chunks: int = 0
    quality_score: int = 0
    warnings: List[str] = []


class StudyPackData(BaseModel):
    """Core study pack content schema."""

    title: str
    book: Optional[Any] = None
    slides: Optional[Any] = None
    quiz: List[Any] = []
    vid: Optional[Any] = None
    readiness: ReadinessData
    quality_scores: QualityScoresData
    grounding: GroundingData


class StudyPackStats(BaseModel):
    """Study pack stats schema for frontend compatibility."""

    course_id: str
    status: str
    has_book: bool = False
    has_book_pdf: bool = False
    has_slide: bool = False
    has_slide_pptx: bool = False
    has_quiz: bool = False
    has_quiz_answer_key: bool = False
    has_vid: bool = False
    quality_score: int = 0
    num_chunks: int = 0


class StudyPackResponse(BaseModel):
    """Full study pack response schema."""

    course_id: str
    stats: Optional[StudyPackStats] = None
    study_pack: StudyPackData
