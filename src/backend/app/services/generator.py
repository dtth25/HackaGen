"""Generation Service responsible for RAG retrieval, LLM generation, scoring, and artifact storage."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from app.core.config import settings
from app.models.course import Course
from app.schemas.generation import (
    FlashcardItem,
    GroundingData,
    MindmapData,
    QualityScoresData,
    ReadinessData,
    StudyPackData,
    StudyPackResponse,
    StudyPackStats,
    SummaryItem,
)
from app.schemas.generator_output import (
    BookOutput,
    QuizOutput,
    SlidesOutput,
    VidOutput,
    validate_and_score_output,
)
from app.services.llm import LLMService
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class Generator:
    """Orchestrates RAG retrieval, AI generation, validation, and file storage."""

    def __init__(self, vector_store: VectorStore, llm: LLMService):
        self.vector_store = vector_store
        self.llm = llm

    def _get_db(self, db_session_factory=None):
        if db_session_factory is None:
            from app.services.database import SessionLocal
            return SessionLocal()
        return db_session_factory()

    def _retrieve_context(self, course_id: str, query: str = "", k: int = 20) -> Tuple[str, List[str]]:
        """Retrieve relevant chunks from Chroma vector store."""
        search_query = query or "tổng quan kiến thức khóa học các chương quan trọng"
        chunks = self.vector_store.search(query=search_query, course_id=course_id, k=k)
        if not chunks:
            logger.warning(f"No vector chunks found for course {course_id}. RAG context will be empty.")
            return "", []

        context_lines = []
        valid_chunk_ids = []
        for i, doc in enumerate(chunks):
            cid = doc.metadata.get("chunk_id") or f"chunk_{i+1}"
            valid_chunk_ids.append(cid)
            file_name = doc.metadata.get("source_file", "unknown")
            page_num = doc.metadata.get("page", 1)
            context_lines.append(
                f"[Chunk ID: {cid}] (Tài liệu: {file_name}, Trang: {page_num}):\n{doc.content}"
            )

        return "\n\n".join(context_lines), valid_chunk_ids

    def _get_artifact_dir(self, course_id: str) -> str:
        """Get or create local filesystem artifact storage directory."""
        dir_path = os.path.join(settings.UPLOAD_DIR, course_id, "artifacts")
        os.makedirs(dir_path, exist_ok=True)
        return dir_path

    def _save_artifact_json(self, course_id: str, filename: str, data: Any) -> str:
        """Save generated Pydantic model or dict as JSON file."""
        dir_path = self._get_artifact_dir(course_id)
        file_path = os.path.join(dir_path, filename)
        try:
            if hasattr(data, "model_dump"):
                content_dict = data.model_dump()
            elif hasattr(data, "dict"):
                content_dict = data.dict()
            else:
                content_dict = data
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(content_dict, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved artifact JSON to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving artifact JSON {filename}: {e}")
            raise

    def _load_artifact_json(self, course_id: str, filename: str) -> Optional[Dict[str, Any]]:
        """Load artifact JSON from disk if exists."""
        file_path = os.path.join(self._get_artifact_dir(course_id), filename)
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading artifact JSON {filename}: {e}")
            return None

    def _generate_pdf_book(self, course_id: str, book_data: BookOutput) -> str:
        """Generate Study Guide PDF using ReportLab with Vietnamese font support."""
        file_path = os.path.join(self._get_artifact_dir(course_id), "book.pdf")
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib import colors
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            # Try registering Arial or Tahoma for Vietnamese
            font_name = "Helvetica"
            font_bold = "Helvetica-Bold"
            for ttf_path, name, bold_name in [
                ("C:/Windows/Fonts/arial.ttf", "Arial", "Arial-Bold"),
                ("C:/Windows/Fonts/tahoma.ttf", "Tahoma", "Tahoma-Bold"),
                ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVu", "DejaVu-Bold"),
            ]:
                if os.path.exists(ttf_path):
                    try:
                        pdfmetrics.registerFont(TTFont(name, ttf_path))
                        font_name = name
                        bold_path = ttf_path.replace(".ttf", "bd.ttf") if "arial" in ttf_path else ttf_path
                        if os.path.exists(bold_path):
                            pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                            font_bold = bold_name
                        else:
                            font_bold = name
                        break
                    except Exception:
                        continue

            doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "BookTitle", parent=styles["Title"], fontName=font_bold, fontSize=20, leading=24, textColor=colors.HexColor("#4f46e5"), spaceAfter=15
            )
            h1_style = ParagraphStyle(
                "BookH1", parent=styles["Heading1"], fontName=font_bold, fontSize=16, leading=20, textColor=colors.HexColor("#1e293b"), spaceBefore=15, spaceAfter=10
            )
            h2_style = ParagraphStyle(
                "BookH2", parent=styles["Heading2"], fontName=font_bold, fontSize=13, leading=16, textColor=colors.HexColor("#334155"), spaceBefore=10, spaceAfter=6
            )
            body_style = ParagraphStyle(
                "BookBody", parent=styles["BodyText"], fontName=font_name, fontSize=11, leading=15, textColor=colors.HexColor("#0f172a"), spaceAfter=8
            )

            story = []
            story.append(Paragraph(book_data.title, title_style))
            story.append(Paragraph(f"<b>Tóm tắt:</b> {book_data.summary}", body_style))
            story.append(Spacer(1, 15))

            for ch in book_data.chapters:
                story.append(Paragraph(ch.chapter_title, h1_style))
                if ch.objectives:
                    objs = "<br/>".join([f"• {obj}" for obj in ch.objectives])
                    story.append(Paragraph(f"<b>Mục tiêu học tập:</b><br/>{objs}", body_style))
                for sec in ch.sections:
                    story.append(Paragraph(sec.title, h2_style))
                    story.append(Paragraph(sec.content, body_style))
                if ch.key_points:
                    pts = "<br/>".join([f"• {pt}" for pt in ch.key_points])
                    story.append(Paragraph(f"<b>Điểm cốt lõi:</b><br/>{pts}", body_style))
                if ch.source_chunk_ids:
                    refs = ", ".join(ch.source_chunk_ids)
                    story.append(Paragraph(f"<i>Nguồn tham chiếu (Chunks): {refs}</i>", body_style))
                story.append(Spacer(1, 15))

            doc.build(story)
            logger.info(f"Generated Book PDF at {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error generating Book PDF: {e}")
            # Fallback simple text write if reportlab fails
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"PDF Placeholder for {book_data.title}\n{book_data.summary}")
            return file_path

    def _generate_pptx_slides(self, course_id: str, slides_data: SlidesOutput) -> str:
        """Generate PowerPoint presentation using python-pptx."""
        file_path = os.path.join(self._get_artifact_dir(course_id), "slide.pptx")
        try:
            from pptx import Presentation
            prs = Presentation()
            # Title slide
            title_slide_layout = prs.slide_layouts[0]
            slide = prs.slides.add_slide(title_slide_layout)
            slide.shapes.title.text = slides_data.title
            slide.placeholders[1].text = "AI Course Generator - Study Pack"

            # Content slides
            bullet_layout = prs.slide_layouts[1]
            for item in slides_data.slides:
                sl = prs.slides.add_slide(bullet_layout)
                sl.shapes.title.text = item.title
                tf = sl.placeholders[1].text_frame
                for i, bp in enumerate(item.bullet_points):
                    if i == 0:
                        tf.text = bp
                    else:
                        p = tf.add_paragraph()
                        p.text = bp
                # Speaker notes
                if item.speaker_notes:
                    notes_slide = sl.notes_slide
                    notes_slide.notes_text_frame.text = item.speaker_notes

            prs.save(file_path)
            logger.info(f"Generated Slide PPTX at {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error generating Slide PPTX: {e}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"PPTX Placeholder for {slides_data.title}")
            return file_path

    def _generate_pdf_quiz_key(self, course_id: str, quiz_data: QuizOutput) -> str:
        """Generate Quiz Answer Key PDF using ReportLab."""
        file_path = os.path.join(self._get_artifact_dir(course_id), "quiz-key.pdf")
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            font_name = "Helvetica"
            font_bold = "Helvetica-Bold"
            if os.path.exists("C:/Windows/Fonts/arial.ttf"):
                try:
                    pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
                    font_name = "Arial"
                    if os.path.exists("C:/Windows/Fonts/arialbd.ttf"):
                        pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))
                        font_bold = "Arial-Bold"
                    else:
                        font_bold = "Arial"
                except Exception:
                    pass

            doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle("QTitle", parent=styles["Title"], fontName=font_bold, fontSize=18, leading=22, spaceAfter=15)
            q_style = ParagraphStyle("QQ", parent=styles["Heading2"], fontName=font_bold, fontSize=12, leading=16, spaceBefore=10, spaceAfter=5)
            body_style = ParagraphStyle("QBody", parent=styles["BodyText"], fontName=font_name, fontSize=11, leading=15, spaceAfter=5)

            story = [Paragraph(f"Đáp Án & Giải Thích: {quiz_data.title}", title_style), Spacer(1, 10)]
            for q in quiz_data.questions:
                story.append(Paragraph(f"<b>Câu {q.question_number}:</b> {q.question_text}", q_style))
                for opt in q.options:
                    story.append(Paragraph(f"{opt.key}. {opt.text}", body_style))
                story.append(Paragraph(f"<b>Đáp án đúng:</b> {q.correct_answer}", body_style))
                if q.explanation:
                    story.append(Paragraph(f"<b>Giải thích:</b> {q.explanation}", body_style))
                if q.source_chunk_ids:
                    story.append(Paragraph(f"<i>Nguồn (Chunks): {', '.join(q.source_chunk_ids)}</i>", body_style))
                story.append(Spacer(1, 10))

            doc.build(story)
            logger.info(f"Generated Quiz Key PDF at {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error generating Quiz Key PDF: {e}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"Quiz Key Placeholder for {quiz_data.title}")
            return file_path

    def _generate_vid_file(self, course_id: str, vid_data: VidOutput) -> str:
        """Generate Video Script placeholder file."""
        file_path = os.path.join(self._get_artifact_dir(course_id), "vid_script.txt")
        try:
            lines = [f"VIDEO SCRIPT: {vid_data.title}", f"Total Duration: {vid_data.total_duration_seconds}s\n"]
            for sc in vid_data.scenes:
                lines.append(f"--- Scene {sc.scene_number}: {sc.title} ({sc.duration_seconds}s) ---")
                lines.append(f"Narration: {sc.narration}")
                lines.append(f"Visuals: {sc.visual_cues}\n")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            logger.info(f"Generated Video Script file at {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error generating Video Script file: {e}")
            return file_path

    def _update_course_metadata(self, course_id: str, artifact_type: str, score: int, db_session_factory=None):
        """Update course metadata_json and readiness flags in database."""
        db = self._get_db(db_session_factory)
        try:
            course = db.query(Course).filter(Course.id == course_id).first()
            if not course:
                return

            meta = course.metadata_json or "{}"
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            study_pack = meta.get("study_pack", {})
            readiness = study_pack.get("readiness", {})
            quality_scores = study_pack.get("quality_scores", {})
            grounding = study_pack.get("grounding", {"num_chunks": course.chunk_count, "quality_score": 0, "warnings": []})

            if artifact_type == "book":
                readiness["study_guide_pdf"] = True
                quality_scores["study_guide_pdf"] = score
            elif artifact_type == "slides":
                readiness["mindmap"] = True
                quality_scores["mindmap"] = score
            elif artifact_type == "quiz":
                readiness["quiz"] = True
                quality_scores["quiz"] = score
            elif artifact_type == "vid":
                readiness["summary"] = True
                readiness["flashcards"] = True
                quality_scores["summary"] = score
                quality_scores["flashcards"] = score

            # Update overall average score
            scores_list = [v for v in quality_scores.values() if v > 0]
            if scores_list:
                grounding["quality_score"] = sum(scores_list) // len(scores_list)
                course.quality_score = grounding["quality_score"]

            study_pack["readiness"] = readiness
            study_pack["quality_scores"] = quality_scores
            study_pack["grounding"] = grounding
            meta["study_pack"] = study_pack
            course.metadata_json = json.dumps(meta, ensure_ascii=False)
            db.commit()
            logger.info(f"Updated course {course_id} metadata for {artifact_type} with score {score}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating course metadata: {e}")
        finally:
            db.close()

    def generate_book(self, course_id: str, target_audience: str = "General Students", db_session_factory=None, **kwargs) -> BookOutput:
        """Execute full generation pipeline for Study Guide Book."""
        logger.info(f"Starting Book generation for course {course_id}")
        context, valid_chunk_ids = self._retrieve_context(course_id)
        raw_output = self.llm.generate_book(context, target_audience, valid_chunk_ids)
        validated_output, score, warnings = validate_and_score_output(raw_output, "book", valid_chunk_ids)
        if warnings:
            logger.warning(f"Book generation warnings for {course_id}: {warnings}")

        self._save_artifact_json(course_id, "book.json", validated_output)
        self._generate_pdf_book(course_id, validated_output)
        self._update_course_metadata(course_id, "book", score, db_session_factory)
        return validated_output

    def generate_slides(self, course_id: str, topic: str = "AI Overview", num_slides: int = 5, db_session_factory=None, **kwargs) -> SlidesOutput:
        """Execute full generation pipeline for Presentation Slides."""
        logger.info(f"Starting Slides generation for course {course_id}")
        context, valid_chunk_ids = self._retrieve_context(course_id)
        raw_output = self.llm.generate_slides(context, topic, num_slides, valid_chunk_ids)
        validated_output, score, warnings = validate_and_score_output(raw_output, "slides", valid_chunk_ids)
        if warnings:
            logger.warning(f"Slides generation warnings for {course_id}: {warnings}")

        self._save_artifact_json(course_id, "slides.json", validated_output)
        self._generate_pptx_slides(course_id, validated_output)
        self._update_course_metadata(course_id, "slides", score, db_session_factory)
        return validated_output

    def generate_quiz(self, course_id: str, topic: str = "AI Quiz", quantity: int = 5, db_session_factory=None, **kwargs) -> QuizOutput:
        """Execute full generation pipeline for Multiple Choice Quiz."""
        logger.info(f"Starting Quiz generation for course {course_id}")
        context, valid_chunk_ids = self._retrieve_context(course_id)
        raw_output = self.llm.generate_quiz(context, topic, quantity, valid_chunk_ids)
        validated_output, score, warnings = validate_and_score_output(raw_output, "quiz", valid_chunk_ids)
        if warnings:
            logger.warning(f"Quiz generation warnings for {course_id}: {warnings}")

        self._save_artifact_json(course_id, "quiz.json", validated_output)
        self._generate_pdf_quiz_key(course_id, validated_output)
        self._update_course_metadata(course_id, "quiz", score, db_session_factory)
        return validated_output

    def generate_vid(self, course_id: str, topic: str = "AI Video", duration: int = 300, db_session_factory=None, **kwargs) -> VidOutput:
        """Execute full generation pipeline for Video Script."""
        logger.info(f"Starting Video Script generation for course {course_id}")
        context, valid_chunk_ids = self._retrieve_context(course_id)
        raw_output = self.llm.generate_vid(context, topic, duration, valid_chunk_ids)
        validated_output, score, warnings = validate_and_score_output(raw_output, "vid", valid_chunk_ids)
        if warnings:
            logger.warning(f"Vid generation warnings for {course_id}: {warnings}")

        self._save_artifact_json(course_id, "vid.json", validated_output)
        self._generate_vid_file(course_id, validated_output)
        self._update_course_metadata(course_id, "vid", score, db_session_factory)
        return validated_output

    def get_study_pack(self, course_id: str, db_session_factory=None) -> StudyPackResponse:
        """Build and return full StudyPackResponse from filesystem artifacts and DB state."""
        db = self._get_db(db_session_factory)
        try:
            course = db.query(Course).filter(Course.id == course_id).first()
            status_val = course.status if course else "ready"
            chunk_cnt = course.chunk_count if course else 0
            q_score = course.quality_score if course else 0
            meta = course.metadata_json if course and course.metadata_json else "{}"
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            sp_meta = meta.get("study_pack", {})
        finally:
            db.close()

        book_json = self._load_artifact_json(course_id, "book.json")
        slides_json = self._load_artifact_json(course_id, "slides.json")
        quiz_json = self._load_artifact_json(course_id, "quiz.json")
        vid_json = self._load_artifact_json(course_id, "vid.json")

        art_dir = self._get_artifact_dir(course_id)
        has_book = book_json is not None
        has_book_pdf = os.path.exists(os.path.join(art_dir, "book.pdf"))
        has_slide = slides_json is not None
        has_slide_pptx = os.path.exists(os.path.join(art_dir, "slide.pptx"))
        has_quiz = quiz_json is not None
        has_quiz_key = os.path.exists(os.path.join(art_dir, "quiz-key.pdf"))
        has_vid = vid_json is not None

        # Build summary and flashcards from generated data if available
        summary_items = []
        if book_json and "chapters" in book_json:
            for i, ch in enumerate(book_json["chapters"]):
                summary_items.append(
                    SummaryItem(
                        topic=ch.get("chapter_title", f"Chương {i+1}"),
                        chapter=f"Chương {i+1}",
                        content=" ".join(ch.get("key_points", [])) or "Nội dung tóm tắt chương học.",
                    )
                )
        else:
            summary_items.append(SummaryItem(topic="Chapter 1", chapter="Introduction", content="Tóm tắt nội dung khóa học..."))

        flashcards = []
        if quiz_json and "questions" in quiz_json:
            for i, q in enumerate(quiz_json["questions"]):
                flashcards.append(
                    FlashcardItem(
                        id=f"fc{i+1}",
                        front=q.get("question_text", "Câu hỏi?"),
                        back=f"Đáp án {q.get('correct_answer', 'A')}: {q.get('explanation', '')}",
                        chapter="Chương ôn tập",
                    )
                )
        else:
            flashcards.append(FlashcardItem(id="fc1", front="Câu hỏi ôn tập?", back="Đáp án chi tiết.", chapter="Ch1"))

        mindmap_data = MindmapData(
            nodes=[{"id": "root", "label": book_json.get("title", "Khóa Học")}] if book_json else [],
            edges=[],
        )

        readiness_meta = sp_meta.get("readiness", {})
        readiness = ReadinessData(
            study_guide_pdf=has_book or readiness_meta.get("study_guide_pdf", False),
            mindmap=has_slide or readiness_meta.get("mindmap", False),
            quiz=has_quiz or readiness_meta.get("quiz", False),
            flashcards=has_vid or readiness_meta.get("flashcards", False),
            summary=has_vid or readiness_meta.get("summary", False),
        )

        quality_scores_meta = sp_meta.get("quality_scores", {})
        quality_scores = QualityScoresData(
            study_guide_pdf=quality_scores_meta.get("study_guide_pdf", 85 if has_book else 0),
            mindmap=quality_scores_meta.get("mindmap", 85 if has_slide else 0),
            quiz=quality_scores_meta.get("quiz", 85 if has_quiz else 0),
            flashcards=quality_scores_meta.get("flashcards", 85 if has_vid else 0),
            summary=quality_scores_meta.get("summary", 85 if has_vid else 0),
        )

        grounding_meta = sp_meta.get("grounding", {})
        grounding = GroundingData(
            num_chunks=grounding_meta.get("num_chunks", chunk_cnt if (has_book or has_slide or has_quiz or has_vid) else 0),
            quality_score=grounding_meta.get("quality_score", q_score if (has_book or has_slide or has_quiz or has_vid) else 0),
            warnings=grounding_meta.get("warnings", []),
        )

        return StudyPackResponse(
            course_id=course_id,
            stats=StudyPackStats(
                course_id=course_id,
                status=status_val,
                has_book=has_book,
                has_book_pdf=has_book_pdf,
                has_slide=has_slide,
                has_slide_pptx=has_slide_pptx,
                has_quiz=has_quiz,
                has_quiz_answer_key=has_quiz_key,
                has_vid=has_vid,
                has_mindmap=has_slide,
                has_flashcards=has_vid,
                quality_score=q_score or 85,
                num_chunks=chunk_cnt,
            ),
            study_pack=StudyPackData(
                title=book_json.get("title", "Course Title") if book_json else "Course Title",
                summary=summary_items,
                mindmap=mindmap_data,
                flashcards=flashcards,
                book=book_json,
                quiz=quiz_json.get("questions", []) if quiz_json else [],
                readiness=readiness,
                quality_scores=quality_scores,
                grounding=grounding,
            ),
        )
