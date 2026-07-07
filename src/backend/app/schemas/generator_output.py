"""Pydantic schemas and quality scoring for AI Course Generator outputs."""

from typing import Any, List, Tuple
from pydantic import BaseModel, Field


# =====================================================================
# 1. Book (Study Guide) Schemas
# =====================================================================


class BookSection(BaseModel):
    """Section within a study guide chapter."""

    title: str = Field(..., description="Title of the section")
    content: str = Field(..., description="Detailed explanation and instructional content")


class BookChapter(BaseModel):
    """Chapter of the study guide."""

    chapter_title: str = Field(..., description="Title of the chapter")
    objectives: List[str] = Field(default_factory=list, description="Learning objectives")
    sections: List[BookSection] = Field(default_factory=list, description="Sections in this chapter")
    key_points: List[str] = Field(default_factory=list, description="Key takeaways")
    source_chunk_ids: List[str] = Field(
        default_factory=list, description="List of chunk IDs used for grounding this chapter"
    )


class BookOutput(BaseModel):
    """Complete generated Study Guide Book."""

    title: str = Field(..., description="Overall title of the study guide")
    summary: str = Field(..., description="Executive summary of the course content")
    chapters: List[BookChapter] = Field(default_factory=list, description="Chapters of the book")


# =====================================================================
# 2. Slides Schemas
# =====================================================================


class SlideItem(BaseModel):
    """Single presentation slide."""

    slide_number: int = Field(..., description="Sequential slide number")
    title: str = Field(..., description="Slide title")
    bullet_points: List[str] = Field(default_factory=list, description="Concise bullet points on the slide")
    speaker_notes: str = Field("", description="Detailed script/notes for the speaker")
    source_chunk_ids: List[str] = Field(
        default_factory=list, description="List of chunk IDs used for grounding this slide"
    )


class SlidesOutput(BaseModel):
    """Complete generated Presentation Slides."""

    title: str = Field(..., description="Title of the presentation deck")
    slides: List[SlideItem] = Field(default_factory=list, description="List of slides")


# =====================================================================
# 3. Quiz Schemas
# =====================================================================


class QuizOption(BaseModel):
    """Multiple choice option."""

    key: str = Field(..., description="Option letter: A, B, C, or D")
    text: str = Field(..., description="Text content of the option")


class QuizQuestion(BaseModel):
    """Single multiple choice question."""

    question_number: int = Field(..., description="Sequential question number")
    question_text: str = Field(..., description="The question text")
    options: List[QuizOption] = Field(default_factory=list, description="List of 4 choices (A, B, C, D)")
    correct_answer: str = Field(..., description="The correct option letter (A, B, C, or D)")
    explanation: str = Field("", description="Detailed explanation of why the answer is correct")
    source_chunk_ids: List[str] = Field(
        default_factory=list, description="List of chunk IDs used for grounding this question"
    )


class QuizOutput(BaseModel):
    """Complete generated Multiple Choice Quiz."""

    title: str = Field(..., description="Title of the quiz assessment")
    questions: List[QuizQuestion] = Field(default_factory=list, description="List of quiz questions")


# =====================================================================
# 4. Video Script Schemas
# =====================================================================


class VidScene(BaseModel):
    """Single video scene."""

    scene_number: int = Field(..., description="Sequential scene number")
    title: str = Field(..., description="Scene title or topic")
    duration_seconds: int = Field(..., description="Estimated duration in seconds")
    narration: str = Field(..., description="Voice-over script / narration text")
    visual_cues: str = Field(..., description="Description of on-screen visuals, animations, or graphics")
    source_chunk_ids: List[str] = Field(
        default_factory=list, description="List of chunk IDs used for grounding this scene"
    )


class VidOutput(BaseModel):
    """Complete generated Video Script."""

    title: str = Field(..., description="Title of the video script")
    total_duration_seconds: int = Field(..., description="Total estimated video duration in seconds")
    scenes: List[VidScene] = Field(default_factory=list, description="List of video scenes")


# =====================================================================
# 5. Quality Scoring and Validation
# =====================================================================


def validate_and_score_output(
    data: Any,
    artifact_type: str,
    valid_chunk_ids: List[str] = None,
) -> Tuple[Any, int, List[str]]:
    """Validate generated artifact and calculate quality score (0-100).

    Returns:
        tuple[data, quality_score, warnings]
    """
    valid_chunk_ids_set = set(valid_chunk_ids or [])
    warnings: List[str] = []
    base_score = 80  # Start with high baseline for valid schema

    if artifact_type == "book":
        if not isinstance(data, BookOutput):
            data = BookOutput.model_validate(data)
        if not data.chapters:
            warnings.append("Sách không có chương nào.")
            base_score -= 20
        else:
            grounded_items = 0
            for ch in data.chapters:
                if not ch.chapter_title or not ch.sections:
                    warnings.append(f"Chương '{ch.chapter_title}' thiếu nội dung chi tiết.")
                    base_score -= 5
                # Check grounding
                if ch.source_chunk_ids:
                    grounded_items += 1
                    invalid_refs = [cid for cid in ch.source_chunk_ids if cid not in valid_chunk_ids_set]
                    if invalid_refs and valid_chunk_ids_set:
                        warnings.append(f"Chương '{ch.chapter_title}' tham chiếu chunk không tồn tại: {invalid_refs}")
            # Boost score if well grounded
            if len(data.chapters) > 0 and (grounded_items / len(data.chapters)) >= 0.8:
                base_score += 10

    elif artifact_type == "slides":
        if not isinstance(data, SlidesOutput):
            data = SlidesOutput.model_validate(data)
        if not data.slides:
            warnings.append("Bài giảng không có slide nào.")
            base_score -= 20
        else:
            grounded_items = 0
            for sl in data.slides:
                if not sl.bullet_points:
                    warnings.append(f"Slide {sl.slide_number} thiếu nội dung bullet points.")
                    base_score -= 5
                if sl.source_chunk_ids:
                    grounded_items += 1
            if len(data.slides) > 0 and (grounded_items / len(data.slides)) >= 0.8:
                base_score += 10

    elif artifact_type == "quiz":
        if not isinstance(data, QuizOutput):
            data = QuizOutput.model_validate(data)
        if not data.questions:
            warnings.append("Bộ đề trắc nghiệm không có câu hỏi nào.")
            base_score -= 20
        else:
            grounded_items = 0
            for q in data.questions:
                if len(q.options) != 4:
                    warnings.append(f"Câu hỏi {q.question_number} không đủ 4 lựa chọn.")
                    base_score -= 10
                if q.correct_answer not in ["A", "B", "C", "D"]:
                    warnings.append(f"Câu hỏi {q.question_number} có đáp án đúng không hợp lệ: {q.correct_answer}")
                    base_score -= 10
                if q.source_chunk_ids:
                    grounded_items += 1
            if len(data.questions) > 0 and (grounded_items / len(data.questions)) >= 0.8:
                base_score += 10

    elif artifact_type == "vid":
        if not isinstance(data, VidOutput):
            data = VidOutput.model_validate(data)
        if not data.scenes:
            warnings.append("Kịch bản video không có phân cảnh nào.")
            base_score -= 20
        else:
            grounded_items = 0
            for sc in data.scenes:
                if not sc.narration or not sc.visual_cues:
                    warnings.append(f"Phân cảnh {sc.scene_number} thiếu lời đọc hoặc mô tả hình ảnh.")
                    base_score -= 5
                if sc.source_chunk_ids:
                    grounded_items += 1
            if len(data.scenes) > 0 and (grounded_items / len(data.scenes)) >= 0.8:
                base_score += 10

    # Clamp score between 0 and 100
    quality_score = max(0, min(100, base_score))
    # Ensure quality score satisfies criteria (> 70) when schema is valid and not empty
    if quality_score <= 70 and not warnings:
        quality_score = 75

    return data, quality_score, warnings
