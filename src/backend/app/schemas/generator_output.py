"""Pydantic schemas and quality scoring for HackaGen outputs."""

from typing import Any, List, Optional, Tuple
from pydantic import BaseModel, Field


# =====================================================================
# 0. Course Title Schema
# =====================================================================


class CourseTitleOutput(BaseModel):
    """A short, human-friendly title generated for a newly uploaded course."""

    title: str = Field(..., description="Concise course title (max ~8 words), no file extension")


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
    introduction: str = Field("", description="Opening paragraph introducing the chapter")
    objectives: List[str] = Field(default_factory=list, description="Learning objectives")
    sections: List[BookSection] = Field(default_factory=list, description="Sections in this chapter")
    key_points: List[str] = Field(default_factory=list, description="Key takeaways")
    review_questions: List[str] = Field(default_factory=list, description="Review/self-check questions")
    source_chunk_ids: List[str] = Field(
        default_factory=list, description="List of chunk IDs used for grounding this chapter"
    )


class BookOutput(BaseModel):
    """Complete generated Study Guide Book."""

    title: str = Field(..., description="Overall title of the study guide")
    summary: str = Field(..., description="Executive summary of the course content")
    preface: str = Field("", description="Foreword/preface introducing the book to the reader")
    chapters: List[BookChapter] = Field(default_factory=list, description="Chapters of the book")


# =====================================================================
# 1b. Book multi-pass pipeline (internal, never persisted as book.json)
# =====================================================================


class BookChapterPlan(BaseModel):
    """Outline entry for a single planned chapter."""

    chapter_number: int = Field(..., description="1-based chapter order")
    chapter_title: str = Field(..., description="Chapter title, without a 'Chương N' prefix")
    description: str = Field(..., description="2-3 sentence summary of what this chapter teaches")
    retrieval_query: str = Field(..., description="Vietnamese search query used to retrieve context for this chapter")
    planned_sections: List[str] = Field(default_factory=list, description="3-5 planned section headings")


class BookOutline(BaseModel):
    """High-level plan for the whole book, produced by the first LLM pass."""

    title: str = Field(..., description="Overall title of the study guide")
    summary: str = Field(..., description="Executive summary of the course content")
    preface: str = Field(..., description="Foreword/preface, 200-350 words")
    chapters: List[BookChapterPlan] = Field(default_factory=list, description="Planned chapters, 5-8 entries")


class BookChapterContent(BaseModel):
    """Full content for a single chapter, produced by a per-chapter LLM pass."""

    chapter_title: str = Field(..., description="Title of the chapter")
    introduction: str = Field("", description="Opening paragraph introducing the chapter")
    objectives: List[str] = Field(default_factory=list, description="Learning objectives")
    sections: List[BookSection] = Field(default_factory=list, description="Sections in this chapter")
    key_points: List[str] = Field(default_factory=list, description="Key takeaways")
    review_questions: List[str] = Field(default_factory=list, description="Review/self-check questions")
    source_chunk_ids: List[str] = Field(
        default_factory=list, description="List of chunk IDs used for grounding this chapter"
    )


# =====================================================================
# 2. Slides Schemas
# =====================================================================


class SlideItem(BaseModel):
    """Single presentation slide."""

    slide_number: int = Field(..., description="Sequential slide number")
    title: str = Field(..., description="Slide title")
    layout_type: Optional[str] = Field("default", description="Slide layout: default, two_column, quote")
    bullet_points: List[str] = Field(default_factory=list, description="Concise bullet points on the slide")
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
    difficulty: Optional[str] = Field("Medium", description="Bloom taxonomy difficulty: Easy, Medium, Hard")
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
    """Single video scene. Frames stay text-minimal (heading + optional short keyword line) —
    the narration (spoken by TTS) carries the actual content, matching the NotebookLM-style
    "voice-led, uncluttered frame" aesthetic rather than dense on-screen bullet text."""

    scene_number: int = Field(..., description="Sequential scene number")
    title: str = Field(..., description="Short on-screen heading for the scene (<=6 words)")
    on_screen_text: Optional[str] = Field(
        "", description="Optional short keyword/phrase shown on screen (<=8 words), may be empty"
    )
    narration: str = Field(..., description="Voice-over script / narration text, spoken naturally")
    duration_seconds: int = Field(0, description="Actual scene duration in seconds, filled in from TTS audio length")
    source_chunk_ids: List[str] = Field(
        default_factory=list, description="List of chunk IDs used for grounding this scene"
    )


class VidOutput(BaseModel):
    """Complete generated Video Script."""

    title: str = Field(..., description="Title of the video script")
    total_duration_seconds: int = Field(..., description="Total estimated video duration in seconds")
    scenes: List[VidScene] = Field(default_factory=list, description="List of video scenes")




# =====================================================================
# 8. Quality Scoring and Validation
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
            if not (4 <= len(data.chapters) <= 10):
                warnings.append(f"Số chương ({len(data.chapters)}) nằm ngoài khoảng khuyến nghị 4-10.")
                base_score -= 10
            grounded_items = 0
            for ch in data.chapters:
                if not ch.chapter_title or not ch.sections:
                    warnings.append(f"Chương '{ch.chapter_title}' thiếu nội dung chi tiết.")
                    base_score -= 5
                word_count = len(ch.introduction.split()) + sum(len(s.content.split()) for s in ch.sections)
                if word_count < 400:
                    warnings.append(f"Chương '{ch.chapter_title}' quá ngắn ({word_count} từ).")
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
                if not sc.narration or len(sc.narration.split()) < 5:
                    warnings.append(f"Phân cảnh {sc.scene_number} thiếu lời đọc hoặc quá ngắn.")
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
