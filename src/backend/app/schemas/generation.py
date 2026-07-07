"""Pydantic schemas for Generation Service Skeleton."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Request payload for generating study artifacts."""

    course_id: Optional[str] = Field(
        None, description="ID of the course to generate artifacts for"
    )


class GenerateResponse(BaseModel):
    """Response payload for generation request."""

    course_id: str
    status: str = "queued"
    message: str = "Generation started..."
    estimated_time: str = "2 minutes"


class SummaryItem(BaseModel):
    """Summary item schema."""

    topic: str
    chapter: str
    content: str


class MindmapData(BaseModel):
    """Mindmap structure schema."""

    nodes: List[Any] = []
    edges: List[Any] = []


class FlashcardItem(BaseModel):
    """Flashcard item schema."""

    id: str
    front: str
    back: str
    chapter: str


class ReadinessData(BaseModel):
    """Study pack artifact readiness flags."""

    study_guide_pdf: bool = False
    mindmap: bool = False
    quiz: bool = False
    flashcards: bool = False
    summary: bool = False


class QualityScoresData(BaseModel):
    """Study pack artifact quality scores."""

    study_guide_pdf: int = 0
    mindmap: int = 0
    quiz: int = 0
    flashcards: int = 0
    summary: int = 0


class GroundingData(BaseModel):
    """Grounding metrics and warnings."""

    num_chunks: int = 0
    quality_score: int = 0
    warnings: List[str] = []


class StudyPackData(BaseModel):
    """Core study pack content schema."""

    title: str
    summary: List[SummaryItem]
    mindmap: MindmapData
    flashcards: List[FlashcardItem]
    book: Optional[Any] = None
    quiz: List[Any] = []
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
    has_mindmap: bool = False
    has_flashcards: bool = False
    quality_score: int = 0
    num_chunks: int = 0


class StudyPackResponse(BaseModel):
    """Full study pack response schema."""

    course_id: str
    stats: Optional[StudyPackStats] = None
    study_pack: StudyPackData
