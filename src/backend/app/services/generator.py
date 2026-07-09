"""Generation Service responsible for RAG retrieval, LLM generation, scoring, and artifact storage."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from app.core.config import settings
from app.models.course import Course
from app.schemas.generation import (
    GroundingData,
    QualityScoresData,
    ReadinessData,
    StudyPackData,
    StudyPackResponse,
    StudyPackStats,
)
from app.schemas.generator_output import (
    BookChapter,
    BookOutput,
    QuizOutput,
    SlidesOutput,
    VidOutput,
    validate_and_score_output,
)
from app.services.llm import LLMGenerationError, LLMService
from app.services.pdf_book import build_book_pdf
from app.services.text_format import clean_text
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


def _clean_slides_output(deck: SlidesOutput) -> SlidesOutput:
    """Normalize LLM-authored prose (strip LaTeX/Markdown) in-place across a slide deck.
    Slides are always rasterized to images for the reader (no live-text consumer), so this
    stays the only artifact type cleaned before persistence; Book/Quiz keep their raw
    LLM Markdown/LaTeX in storage and clean it only at PDF-build time (see pdf_utils.prepare_pdf_text)
    so the frontend's real Markdown+KaTeX renderer gets full fidelity."""
    deck.title = clean_text(deck.title)
    for sl in deck.slides:
        sl.title = clean_text(sl.title)
        sl.bullet_points = [clean_text(b) for b in sl.bullet_points]
    return deck


def _clean_vid_output(vid: VidOutput) -> VidOutput:
    """Normalize LLM-authored prose (strip LaTeX/Markdown) in-place across a video script.
    Frames are rasterized (like Slides), so this stays the only cleanup pass before render."""
    vid.title = clean_text(vid.title)
    for sc in vid.scenes:
        sc.title = clean_text(sc.title)
        sc.on_screen_text = clean_text(sc.on_screen_text or "")
        sc.narration = clean_text(sc.narration)
    return vid


class Generator:
    """Orchestrates RAG retrieval, AI generation, validation, and file storage."""

    def __init__(self, vector_store: VectorStore, llm: LLMService, feature_llms: Optional[Dict[str, LLMService]] = None):
        self.vector_store = vector_store
        self.llm = llm
        # Per-feature LLM instances (book/slides/quiz/vid), each optionally configured with
        # its own Gemini API key. Falls back to `self.llm` for any feature not provided.
        self.feature_llms = feature_llms or {}

    def _llm_for(self, feature: str) -> LLMService:
        return self.feature_llms.get(feature, self.llm)

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
        """Generate the Study Guide PDF (cover, preface, page-numbered TOC, chapters).

        Raises on failure — callers must treat that as a hard generation error, not write a
        placeholder file in its place.
        """
        file_path = os.path.join(self._get_artifact_dir(course_id), "book.pdf")
        build_book_pdf(file_path, book_data)
        return file_path

    def _generate_pdf_slides(self, course_id: str, slides_data: SlidesOutput) -> str:
        """Generate a 16:9 Widescreen PDF presentation using ReportLab."""
        file_path = os.path.join(self._get_artifact_dir(course_id), "slide.pdf")
        try:
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib import colors
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, PageBreak, Table, TableStyle
            from app.services.pdf_utils import prepare_pdf_text, register_vietnamese_fonts

            font_name, font_bold = register_vietnamese_fonts()

            # Widescreen 16:9 is 960 width by 540 height
            doc = SimpleDocTemplate(
                file_path,
                pagesize=(960, 540),
                leftMargin=50,
                rightMargin=50,
                topMargin=50,
                bottomMargin=50
            )

            styles = getSampleStyleSheet()

            # Styles for Slide contents
            slide_title_style = ParagraphStyle(
                "SlideTitle",
                parent=styles["Title"],
                fontName=font_bold,
                fontSize=28,
                leading=34,
                textColor=colors.HexColor("#06b6d4"), # Cyan-500
                alignment=0,
                spaceAfter=20
            )

            slide_body_style = ParagraphStyle(
                "SlideBody",
                parent=styles["BodyText"],
                fontName=font_name,
                fontSize=16,
                leading=22,
                textColor=colors.HexColor("#f8fafc"), # slate-50
                spaceAfter=12
            )

            slide_quote_style = ParagraphStyle(
                "SlideQuote",
                parent=styles["Normal"],
                fontName=font_name,
                fontSize=22,
                leading=30,
                textColor=colors.HexColor("#38bdf8"), # light-blue-400
                alignment=1,
                spaceAfter=20
            )

            story = []

            # Page Templates: background & footer drawing
            def draw_title_slide_bg(canvas, doc):
                canvas.saveState()
                canvas.setFillColor(colors.HexColor("#020617"))
                canvas.rect(0, 0, 960, 540, fill=True, stroke=False)
                
                canvas.setFillColor(colors.HexColor("#0f172a"))
                canvas.rect(0, 0, 960, 80, fill=True, stroke=False)
                
                canvas.setFillColor(colors.HexColor("#06b6d4"))
                canvas.rect(50, 150, 8, 260, fill=True, stroke=False)
                canvas.restoreState()

            def draw_content_slide_bg(canvas, doc):
                canvas.saveState()
                canvas.setFillColor(colors.HexColor("#0f172a"))
                canvas.rect(0, 0, 960, 540, fill=True, stroke=False)

                canvas.setFillColor(colors.HexColor("#1e293b"))
                canvas.rect(0, 480, 960, 60, fill=True, stroke=False)

                canvas.setStrokeColor(colors.HexColor("#06b6d4"))
                canvas.setLineWidth(2)
                canvas.line(0, 480, 960, 480)

                canvas.setFillColor(colors.HexColor("#64748b"))
                canvas.setFont(font_name, 10)
                canvas.drawRightString(910, 20, f"Slide {canvas._pageNumber}")
                canvas.restoreState()

            # Slide 1: Cover Page
            story.append(Spacer(1, 100))
            title_p = Paragraph(f"<font color='#06b6d4'>{prepare_pdf_text(slides_data.title)}</font>", ParagraphStyle("CoverTitle", parent=slide_title_style, fontSize=36, leading=44, leftIndent=30))
            story.append(title_p)
            story.append(PageBreak())

            # Slide content pages
            for idx, item in enumerate(slides_data.slides):
                story.append(Spacer(1, 10))
                story.append(Paragraph(prepare_pdf_text(item.title), slide_title_style))
                story.append(Spacer(1, 10))

                layout_type = getattr(item, "layout_type", "default") or "default"
                if layout_type == "two_column":
                    mid = (len(item.bullet_points) + 1) // 2
                    left_bps = [f"• {prepare_pdf_text(bp)}" for bp in item.bullet_points[:mid]]
                    right_bps = [f"• {prepare_pdf_text(bp)}" for bp in item.bullet_points[mid:]]

                    left_text = "<br/><br/>".join(left_bps)
                    right_text = "<br/><br/>".join(right_bps)

                    left_p = Paragraph(left_text, slide_body_style)
                    right_p = Paragraph(right_text, slide_body_style)

                    t = Table([[left_p, right_p]], colWidths=[420, 420])
                    t.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('LEFTPADDING', (0,0), (-1,-1), 0),
                        ('RIGHTPADDING', (0,0), (-1,-1), 10),
                    ]))
                    story.append(t)
                elif layout_type == "quote":
                    quote_text = "<br/><br/>".join(prepare_pdf_text(bp) for bp in item.bullet_points)
                    story.append(Spacer(1, 40))
                    story.append(Paragraph(f"<i>“{quote_text}”</i>", slide_quote_style))
                else:
                    bullets_html = []
                    for bp in item.bullet_points:
                        bullets_html.append(f"• {prepare_pdf_text(bp)}")
                    content_text = "<br/><br/>".join(bullets_html)
                    story.append(Paragraph(content_text, slide_body_style))

                if idx < len(slides_data.slides) - 1:
                    story.append(PageBreak())

            doc.build(
                story,
                onFirstPage=draw_title_slide_bg,
                onLaterPages=draw_content_slide_bg
            )
            logger.info(f"Generated 16:9 PDF Slides at {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error generating PDF slides: {e}", exc_info=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"PDF Slides Placeholder for {slides_data.title}")
            return file_path

    def _convert_pdf_to_images(self, pdf_path: str, course_id: str) -> list[str]:
        """Convert a PDF file into PNG slide images using PyMuPDF (fitz)."""
        import fitz
        artifact_dir = self._get_artifact_dir(course_id)
        image_paths = []
        try:
            doc = fitz.open(pdf_path)
            for i, page in enumerate(doc):
                pix = page.get_pixmap(dpi=150)
                img_name = f"slide_{i+1}.png"
                img_path = os.path.join(artifact_dir, img_name)
                pix.save(img_path)
                image_paths.append(img_path)
            logger.info(f"Converted {len(image_paths)} pages to PNG slide images for course {course_id}")
            return image_paths
        except Exception as e:
            logger.error(f"Failed to convert PDF to images: {e}", exc_info=True)
            return []

    def _generate_pptx_slides(self, course_id: str, slides_data: SlidesOutput) -> str:
        """Generate PowerPoint presentation by inserting ReportLab slide PNGs full screen."""
        file_path = os.path.join(self._get_artifact_dir(course_id), "slide.pptx")
        try:
            from pptx import Presentation
            from pptx.util import Inches

            pdf_path = self._generate_pdf_slides(course_id, slides_data)
            image_paths = self._convert_pdf_to_images(pdf_path, course_id)

            prs = Presentation()
            prs.slide_width = Inches(13.333)
            prs.slide_height = Inches(7.5)
            
            blank_layout = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[0]
            
            for img_path in image_paths:
                slide = prs.slides.add_slide(blank_layout)
                slide.shapes.add_picture(img_path, 0, 0, width=prs.slide_width, height=prs.slide_height)

            prs.save(file_path)
            logger.info(f"Generated Slide PPTX at {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error generating Slide PPTX: {e}", exc_info=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"PPTX Placeholder for {slides_data.title}")
            return file_path

    def _generate_pdf_quiz_key(self, course_id: str, quiz_data: QuizOutput) -> str:
        """Generate Quiz PDF in two sections: Student Quiz Sheet and Answer Key & Explanations."""
        file_path = os.path.join(self._get_artifact_dir(course_id), "quiz-key.pdf")
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib import colors
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, PageBreak
            from app.services.pdf_utils import prepare_pdf_text, register_vietnamese_fonts

            font_name, font_bold = register_vietnamese_fonts()

            doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle("QTitle", parent=styles["Title"], fontName=font_bold, fontSize=20, leading=24, textColor=colors.HexColor("#1e3a8a"), spaceAfter=15)
            part_style = ParagraphStyle("QPart", parent=styles["Heading1"], fontName=font_bold, fontSize=15, leading=18, textColor=colors.HexColor("#4f46e5"), spaceBefore=10, spaceAfter=15)
            q_style = ParagraphStyle("QQ", parent=styles["Heading2"], fontName=font_bold, fontSize=12, leading=16, textColor=colors.HexColor("#1e293b"), spaceBefore=10, spaceAfter=6)
            body_style = ParagraphStyle("QBody", parent=styles["BodyText"], fontName=font_name, fontSize=11, leading=15, textColor=colors.HexColor("#0f172a"), spaceAfter=5)

            story = [Paragraph(f"BỘ ĐỀ KIỂM TRA & ĐÁNH GIÁ: {prepare_pdf_text(quiz_data.title)}", title_style), Spacer(1, 10)]

            # --- Part 1: Student Quiz Sheet ---
            story.append(Paragraph("PHẦN 1: ĐỀ THI TRẮC NGHIỆM (STUDENT QUIZ SHEET)", part_style))
            for q in quiz_data.questions:
                story.append(Paragraph(f"<b>Câu {q.question_number}:</b> {prepare_pdf_text(q.question_text)}", q_style))
                for opt in q.options:
                    story.append(Paragraph(f"<b>{opt.key}.</b> {prepare_pdf_text(opt.text)}", body_style))
                story.append(Spacer(1, 10))
            story.append(PageBreak())

            # --- Part 2: Answer Key & Explanations ---
            story.append(Paragraph("PHẦN 2: ĐÁP ÁN & GIẢI THÍCH CHI TIẾT (ANSWER KEY & EXPLANATIONS)", part_style))
            for q in quiz_data.questions:
                diff_str = getattr(q, "difficulty", "Medium") or "Medium"
                story.append(Paragraph(f"<b>Câu {q.question_number} [Mức độ Bloom: {diff_str}]:</b> {prepare_pdf_text(q.question_text)}", q_style))
                story.append(Paragraph(f"<b>Đáp án đúng:</b> <font color='#16a34a'><b>{q.correct_answer}</b></font>", body_style))
                if q.explanation:
                    story.append(Paragraph(f"<b>Giải thích chi tiết:</b> {prepare_pdf_text(q.explanation)}", body_style))
                story.append(Spacer(1, 10))

            doc.build(story)
            logger.info(f"Generated Quiz Key PDF at {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error generating Quiz Key PDF: {e}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"Quiz Key Placeholder for {quiz_data.title}")
            return file_path

    def _generate_video_mp4(
        self, course_id: str, vid_data: VidOutput, fmt: str, voice: str, progress_cb=None
    ) -> str:
        """Render the narrated MP4 (TTS + still frames + ffmpeg concat) plus transcript.txt /
        vid.srt. Raises on failure — callers must treat that as a hard generation error, not
        write a placeholder file in its place (matches the strict invariant used by Book's PDF)."""
        from app.services.video_render import assemble_video

        artifact_dir = self._get_artifact_dir(course_id)
        return assemble_video(vid_data, fmt, voice, artifact_dir, progress_cb=progress_cb)

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
                readiness["slides"] = True
                quality_scores["slides"] = score
            elif artifact_type == "quiz":
                readiness["quiz"] = True
                quality_scores["quiz"] = score
            elif artifact_type == "vid":
                readiness["vid"] = True
                quality_scores["vid"] = score


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

    def _set_artifact_status(
        self,
        course_id: str,
        artifact: str,
        status: str,
        error: Optional[str] = None,
        progress: Optional[int] = None,
        db_session_factory=None,
    ):
        """Persist per-artifact generation status (processing/ready/error) into Course.metadata_json."""
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
            artifacts = study_pack.get("artifacts", {})
            entry = artifacts.get(artifact, {})

            now = datetime.utcnow().isoformat()
            entry["status"] = status
            entry["error"] = error
            if progress is not None:
                entry["progress"] = progress
            if status == "processing" and "started_at" not in entry:
                entry["started_at"] = now
            if status in ("ready", "error"):
                entry["finished_at"] = now
            entry["updated_at"] = now

            artifacts[artifact] = entry
            study_pack["artifacts"] = artifacts
            meta["study_pack"] = study_pack
            course.metadata_json = json.dumps(meta, ensure_ascii=False)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error setting artifact status for {artifact}: {e}")
        finally:
            db.close()

    def get_artifact_status(self, course_id: str, artifact: str, db_session_factory=None) -> Dict[str, Any]:
        """Read per-artifact generation status from Course.metadata_json."""
        db = self._get_db(db_session_factory)
        try:
            course = db.query(Course).filter(Course.id == course_id).first()
            if not course:
                return {}
            meta = course.metadata_json or "{}"
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            return meta.get("study_pack", {}).get("artifacts", {}).get(artifact, {})
        finally:
            db.close()

    def _resolve_topic(self, course_id: str, topic: Optional[str] = None, db_session_factory=None) -> str:
        """Resolve actual course/document topic if topic is missing or hardcoded generic AI string."""
        ignore_list = ["AI Quiz", "AI Overview", "AI Video", "AI Course", "General Students", ""]
        if topic and str(topic).strip() and str(topic).strip() not in ignore_list:
            return str(topic).strip()

        db = self._get_db(db_session_factory)
        try:
            course = db.query(Course).filter(Course.id == course_id).first()
            if course and course.name and course.name.strip():
                return course.name.strip()
            if course and course.filenames and len(course.filenames) > 0:
                fn = str(course.filenames[0])
                for ext in [".pdf", ".docx", ".txt", ".PPTX", ".PDF", ".DOCX", ".TXT"]:
                    if fn.lower().endswith(ext.lower()):
                        fn = fn[:-len(ext)]
                if fn.strip():
                    return fn.strip()
            if course and course.metadata_json:
                try:
                    meta = json.loads(course.metadata_json) if isinstance(course.metadata_json, str) else course.metadata_json
                    if isinstance(meta, dict) and meta.get("title"):
                        return str(meta["title"]).strip()
                except Exception:
                    pass
        finally:
            db.close()
        return "Nội dung tài liệu chính"

    def _get_doc_names(self, course_id: str, db_session_factory=None) -> str:
        """Fetch the course's source document filenames as a comma-separated string."""
        db = self._get_db(db_session_factory)
        try:
            course = db.query(Course).filter(Course.id == course_id).first()
            if course and course.filenames:
                return ", ".join(str(fn) for fn in course.filenames)
            return ""
        finally:
            db.close()

    def generate_book(
        self,
        course_id: str,
        detail_level: str = "Tiêu chuẩn",
        user_prompt: str = "",
        db_session_factory=None,
        **kwargs,
    ) -> Optional[BookOutput]:
        """Execute the multi-pass generation pipeline for the Study Guide Book:
        outline pass -> one LLM call per chapter (with per-chapter retrieval) -> assemble -> validate -> PDF.

        On any failure, records an "error" artifact status and returns None instead of writing a
        partial/placeholder artifact.
        """
        logger.info(f"Starting Book generation for course {course_id}")
        try:
            self._set_artifact_status(course_id, "book", "processing", progress=5, db_session_factory=db_session_factory)

            book_llm = self._llm_for("book")
            context, base_ids = self._retrieve_context(course_id, k=20)
            doc_names = self._get_doc_names(course_id, db_session_factory)
            outline = book_llm.generate_book_outline(context, detail_level, user_prompt, doc_names)
            plans = outline.chapters[:8]
            if len(plans) < 4:
                raise ValueError(f"Dàn ý chỉ có {len(plans)} chương, cần tối thiểu 4 chương.")

            self._set_artifact_status(course_id, "book", "processing", progress=15, db_session_factory=db_session_factory)

            all_ids = set(base_ids)
            chapters: List[BookChapter] = []
            total = len(plans)
            for i, plan in enumerate(plans):
                ch_context, ch_ids = self._retrieve_context(course_id, query=plan.retrieval_query, k=10)
                if not ch_context:
                    ch_context, ch_ids = context, base_ids
                all_ids.update(ch_ids)

                try:
                    content = book_llm.generate_book_chapter(
                        outline.title, plan, total, ch_context, detail_level, ch_ids
                    )
                except LLMGenerationError as e:
                    logger.warning(f"Chapter '{plan.chapter_title}' failed once, retrying: {e}")
                    content = book_llm.generate_book_chapter(
                        outline.title, plan, total, ch_context, detail_level, ch_ids
                    )

                chapters.append(
                    BookChapter(
                        chapter_title=content.chapter_title or plan.chapter_title,
                        introduction=content.introduction,
                        objectives=content.objectives,
                        sections=content.sections,
                        key_points=content.key_points,
                        review_questions=content.review_questions,
                        source_chunk_ids=content.source_chunk_ids,
                    )
                )
                progress = 15 + int(75 * (i + 1) / total)
                self._set_artifact_status(course_id, "book", "processing", progress=progress, db_session_factory=db_session_factory)

            book = BookOutput(title=outline.title, summary=outline.summary, preface=outline.preface, chapters=chapters)
            validated_output, score, warnings = validate_and_score_output(book, "book", list(all_ids))
            if warnings:
                logger.warning(f"Book generation warnings for {course_id}: {warnings}")

            self._save_artifact_json(course_id, "book.json", validated_output)
            self._generate_pdf_book(course_id, validated_output)
            self._update_course_metadata(course_id, "book", score, db_session_factory)
            self._set_artifact_status(course_id, "book", "ready", progress=100, db_session_factory=db_session_factory)
            return validated_output
        except Exception as e:
            logger.error(f"Book generation failed for course {course_id}: {e}", exc_info=True)
            self._set_artifact_status(
                course_id, "book", "error", error=str(e)[:500], db_session_factory=db_session_factory
            )
            return None

    def generate_slides(self, course_id: str, topic: str = "AI Overview", num_slides: int = 15, db_session_factory=None, **kwargs) -> Optional[SlidesOutput]:
        """Execute full generation pipeline for Presentation Slides.

        On any failure, records an "error" artifact status and returns None instead of
        letting a background-task exception vanish silently.
        """
        logger.info(f"Starting Slides generation for course {course_id}")
        try:
            self._set_artifact_status(course_id, "slides", "processing", progress=10, db_session_factory=db_session_factory)
            resolved_topic = self._resolve_topic(course_id, topic, db_session_factory=db_session_factory)
            context, valid_chunk_ids = self._retrieve_context(course_id, query=resolved_topic)
            raw_output = self._llm_for("slides").generate_slides(context, resolved_topic, num_slides, valid_chunk_ids)
            validated_output, score, warnings = validate_and_score_output(raw_output, "slides", valid_chunk_ids)
            if warnings:
                logger.warning(f"Slides generation warnings for {course_id}: {warnings}")
            validated_output = _clean_slides_output(validated_output)

            self._set_artifact_status(course_id, "slides", "processing", progress=70, db_session_factory=db_session_factory)
            self._save_artifact_json(course_id, "slides.json", validated_output)
            self._generate_pptx_slides(course_id, validated_output)
            self._update_course_metadata(course_id, "slides", score, db_session_factory)
            self._set_artifact_status(course_id, "slides", "ready", progress=100, db_session_factory=db_session_factory)
            return validated_output
        except Exception as e:
            logger.error(f"Slides generation failed for course {course_id}: {e}", exc_info=True)
            self._set_artifact_status(
                course_id, "slides", "error", error=str(e)[:500], db_session_factory=db_session_factory
            )
            return None

    def generate_quiz(self, course_id: str, topic: str = "AI Quiz", quantity: int = 5, difficulty: str = "mixed", db_session_factory=None, **kwargs) -> Optional[QuizOutput]:
        """Execute full generation pipeline for Multiple Choice Quiz.

        On any failure, records an "error" artifact status and returns None instead of
        letting a background-task exception vanish silently.
        """
        logger.info(f"Starting Quiz generation for course {course_id} (quantity={quantity}, difficulty={difficulty})")
        try:
            self._set_artifact_status(course_id, "quiz", "processing", progress=10, db_session_factory=db_session_factory)
            resolved_topic = self._resolve_topic(course_id, topic, db_session_factory=db_session_factory)
            context, valid_chunk_ids = self._retrieve_context(course_id, query=resolved_topic)
            raw_output = self._llm_for("quiz").generate_quiz(context, resolved_topic, quantity, valid_chunk_ids, difficulty=difficulty)
            validated_output, score, warnings = validate_and_score_output(raw_output, "quiz", valid_chunk_ids)
            if warnings:
                logger.warning(f"Quiz generation warnings for {course_id}: {warnings}")

            self._set_artifact_status(course_id, "quiz", "processing", progress=70, db_session_factory=db_session_factory)
            self._save_artifact_json(course_id, "quiz.json", validated_output)
            self._generate_pdf_quiz_key(course_id, validated_output)
            self._update_course_metadata(course_id, "quiz", score, db_session_factory)
            self._set_artifact_status(course_id, "quiz", "ready", progress=100, db_session_factory=db_session_factory)
            return validated_output
        except Exception as e:
            logger.error(f"Quiz generation failed for course {course_id}: {e}", exc_info=True)
            self._set_artifact_status(
                course_id, "quiz", "error", error=str(e)[:500], db_session_factory=db_session_factory
            )
            return None

    def generate_vid(
        self,
        course_id: str,
        topic: str = "AI Video",
        fmt: str = "standard",
        voice: str = "female",
        user_prompt: str = "",
        db_session_factory=None,
        **kwargs,
    ) -> Optional[VidOutput]:
        """Execute full generation pipeline for the narrated Video: LLM script (1 call) ->
        per-scene TTS narration + still frame -> ffmpeg mux/concat into vid.mp4.

        On any failure, records an "error" artifact status and returns None instead of
        letting a background-task exception vanish silently.
        """
        logger.info(f"Starting Video generation for course {course_id} (format={fmt}, voice={voice})")
        try:
            self._set_artifact_status(course_id, "vid", "processing", progress=10, db_session_factory=db_session_factory)
            resolved_topic = self._resolve_topic(course_id, topic, db_session_factory=db_session_factory)
            context, valid_chunk_ids = self._retrieve_context(course_id, query=resolved_topic)
            raw_output = self._llm_for("vid").generate_vid(
                context, resolved_topic, fmt, user_prompt, valid_chunk_ids
            )
            validated_output, score, warnings = validate_and_score_output(raw_output, "vid", valid_chunk_ids)
            if warnings:
                logger.warning(f"Vid generation warnings for {course_id}: {warnings}")
            validated_output = _clean_vid_output(validated_output)

            self._set_artifact_status(course_id, "vid", "processing", progress=25, db_session_factory=db_session_factory)

            def _progress_cb(fraction: float) -> None:
                self._set_artifact_status(
                    course_id, "vid", "processing", progress=25 + int(60 * fraction),
                    db_session_factory=db_session_factory,
                )

            self._generate_video_mp4(course_id, validated_output, fmt, voice, progress_cb=_progress_cb)

            self._set_artifact_status(course_id, "vid", "processing", progress=90, db_session_factory=db_session_factory)
            self._save_artifact_json(course_id, "vid.json", validated_output)
            self._update_course_metadata(course_id, "vid", score, db_session_factory)
            self._set_artifact_status(course_id, "vid", "ready", progress=100, db_session_factory=db_session_factory)
            return validated_output
        except Exception as e:
            logger.error(f"Vid generation failed for course {course_id}: {e}", exc_info=True)
            self._set_artifact_status(
                course_id, "vid", "error", error=str(e)[:500], db_session_factory=db_session_factory
            )
            return None

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

        readiness_meta = sp_meta.get("readiness", {})
        readiness = ReadinessData(
            study_guide_pdf=has_book or readiness_meta.get("study_guide_pdf", False),
            slides=has_slide or readiness_meta.get("slides", False),
            quiz=has_quiz or readiness_meta.get("quiz", False),
            vid=has_vid or readiness_meta.get("vid", False),
        )

        quality_scores_meta = sp_meta.get("quality_scores", {})
        quality_scores = QualityScoresData(
            study_guide_pdf=quality_scores_meta.get("study_guide_pdf", 85 if has_book else 0),
            slides=quality_scores_meta.get("slides", 85 if has_slide else 0),
            quiz=quality_scores_meta.get("quiz", 85 if has_quiz else 0),
            vid=quality_scores_meta.get("vid", 85 if has_vid else 0),
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
                quality_score=q_score or 85,
                num_chunks=chunk_cnt,
            ),
            study_pack=StudyPackData(
                title=book_json.get("title", "Course Title") if book_json else "Course Title",
                book=book_json,
                slides=slides_json,
                quiz=quiz_json.get("questions", []) if quiz_json else [],
                vid=vid_json,
                readiness=readiness,
                quality_scores=quality_scores,
                grounding=grounding,
            ),
        )
