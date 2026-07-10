"""Book (Study Guide) PDF builder: cover, preface, TOC with real page numbers, chapters.

Uses ReportLab's multi-pass build (multiBuild) so the table of contents can carry accurate
page numbers, plus PDF sidebar bookmarks for chapters/sections. Raises on any failure — the
caller is responsible for recording an artifact error status instead of writing a placeholder.
"""

import hashlib
import logging
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
from reportlab.platypus.tableofcontents import TableOfContents

from app.schemas.generator_output import BookOutput
from app.services.pdf_utils import prepare_pdf_plain_text, prepare_pdf_text, register_vietnamese_fonts

logger = logging.getLogger(__name__)

# Local alias — pdf_book historically called this `_esc`; keep the name for a minimal diff
# below, but it now also flattens LaTeX/Markdown to Unicode and filters unsupported glyphs.
_esc = prepare_pdf_text


class _BookDocTemplate(SimpleDocTemplate):
    """SimpleDocTemplate that records TOC entries and PDF outline bookmarks for chapter/section headings."""

    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        style_name = getattr(flowable.style, "name", "")
        if style_name not in ("BookH1", "BookH2"):
            return
        level = 0 if style_name == "BookH1" else 1
        text = flowable.getPlainText()
        # Text-based (page-independent) key so bookmarks stay stable across multiBuild passes.
        key = f"bm-{level}-{hashlib.sha1(text.encode('utf-8')).hexdigest()[:10]}"
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text, key, level=level, closed=(level > 0))
        self.notify("TOCEntry", (level, text, self.page))


def build_book_pdf(file_path: str, book: BookOutput) -> None:
    """Render the Study Guide book to `file_path`. Raises on failure."""
    font_name, font_bold = register_vietnamese_fonts()
    styles = getSampleStyleSheet()

    cover_title_style = ParagraphStyle(
        "CoverTitle", parent=styles["Title"], fontName=font_bold, fontSize=26, leading=32,
        textColor=colors.HexColor("#1e3a8a"), alignment=1, spaceAfter=20,
    )
    cover_sub_style = ParagraphStyle(
        "CoverSub", parent=styles["Normal"], fontName=font_name, fontSize=14, leading=18,
        textColor=colors.HexColor("#475569"), alignment=1, spaceAfter=40,
    )
    cover_meta_style = ParagraphStyle(
        "CoverMeta", parent=styles["Normal"], fontName=font_name, fontSize=11, leading=15,
        textColor=colors.HexColor("#64748b"), alignment=1,
    )
    front_h_style = ParagraphStyle(
        "BookFrontH", parent=styles["Heading1"], fontName=font_bold, fontSize=18, leading=22,
        textColor=colors.HexColor("#1e3a8a"), spaceBefore=6, spaceAfter=14, keepWithNext=1,
    )
    toc_title_style = ParagraphStyle(
        "TocTitle", parent=styles["Heading1"], fontName=font_bold, fontSize=18, leading=22,
        textColor=colors.HexColor("#1e3a8a"), spaceAfter=15,
    )
    h1_style = ParagraphStyle(
        "BookH1", parent=styles["Heading1"], fontName=font_bold, fontSize=17, leading=21,
        textColor=colors.HexColor("#1e3a8a"), spaceBefore=6, spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "BookH2", parent=styles["Heading2"], fontName=font_bold, fontSize=13, leading=17,
        textColor=colors.HexColor("#334155"), spaceBefore=12, spaceAfter=6, keepWithNext=1,
    )
    body_style = ParagraphStyle(
        "BookBody", parent=styles["BodyText"], fontName=font_name, fontSize=11, leading=16.5,
        textColor=colors.HexColor("#0f172a"), spaceAfter=8, alignment=4,
    )
    box_label_style = ParagraphStyle(
        "BookBoxLabel", parent=styles["Normal"], fontName=font_bold, fontSize=11, leading=15,
        textColor=colors.HexColor("#0f172a"), spaceBefore=6, spaceAfter=4, keepWithNext=1,
    )
    obj_style = ParagraphStyle(
        "BookObj", parent=styles["Normal"], fontName=font_name, fontSize=10.5, leading=15,
        textColor=colors.HexColor("#0369a1"), spaceAfter=4, leftIndent=15,
    )
    key_style = ParagraphStyle(
        "BookKey", parent=styles["Normal"], fontName=font_name, fontSize=10.5, leading=15,
        textColor=colors.HexColor("#b45309"), spaceAfter=4, leftIndent=15,
    )
    question_style = ParagraphStyle(
        "BookQuestion", parent=styles["Normal"], fontName=font_name, fontSize=10.5, leading=15,
        textColor=colors.HexColor("#334155"), spaceAfter=4, leftIndent=15,
    )
    toc_style_l0 = ParagraphStyle(
        "TOCLevel0", parent=styles["Normal"], fontName=font_bold, fontSize=12, leading=18,
        textColor=colors.HexColor("#1e293b"), spaceAfter=6,
    )
    toc_style_l1 = ParagraphStyle(
        "TOCLevel1", parent=styles["Normal"], fontName=font_name, fontSize=10.5, leading=15,
        textColor=colors.HexColor("#475569"), leftIndent=14, spaceAfter=4,
    )

    doc = _BookDocTemplate(
        file_path, pagesize=A4, rightMargin=56, leftMargin=56, topMargin=60, bottomMargin=56, title=book.title,
    )

    toc = TableOfContents()
    toc.levelStyles = [toc_style_l0, toc_style_l1]

    story = []

    # --- Cover page ---
    story.append(Spacer(1, 110))
    story.append(Paragraph(_esc(book.title), cover_title_style))
    story.append(Paragraph("SÁCH ÔN TẬP — TÀI LIỆU HỌC TẬP RÚT GỌN", cover_sub_style))
    story.append(Spacer(1, 140))
    story.append(Paragraph("Biên soạn bởi HackaGen", cover_meta_style))
    story.append(Paragraph(f"Ngày xuất bản: {datetime.now().strftime('%d/%m/%Y')}", cover_meta_style))
    story.append(PageBreak())

    # --- Preface / summary ---
    story.append(Paragraph("LỜI NÓI ĐẦU", front_h_style))
    for para in (book.preface or "").split("\n\n"):
        if para.strip():
            story.append(Paragraph(_esc(para.strip()), body_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph("TÓM TẮT NỘI DUNG", front_h_style))
    story.append(Paragraph(_esc(book.summary), body_style))
    story.append(PageBreak())

    # --- Table of contents ---
    story.append(Paragraph("MỤC LỤC", toc_title_style))
    story.append(toc)
    story.append(PageBreak())

    # --- Chapters ---
    for i, ch in enumerate(book.chapters, 1):
        story.append(Paragraph(f"Chương {i}: {_esc(ch.chapter_title)}", h1_style))
        if ch.introduction:
            story.append(Paragraph(_esc(ch.introduction), body_style))
        if ch.objectives:
            story.append(Spacer(1, 4))
            story.append(Paragraph("Mục tiêu học tập", box_label_style))
            for obj in ch.objectives:
                story.append(Paragraph(f"• {_esc(obj)}", obj_style))
        for sec in ch.sections:
            story.append(Paragraph(_esc(sec.title), h2_style))
            for para in (sec.content or "").split("\n\n"):
                if para.strip():
                    story.append(Paragraph(_esc(para.strip()), body_style))
        if ch.key_points:
            story.append(Spacer(1, 6))
            story.append(Paragraph("Điểm cốt lõi", box_label_style))
            for pt in ch.key_points:
                story.append(Paragraph(f"› {_esc(pt)}", key_style))
        if ch.review_questions:
            story.append(Spacer(1, 6))
            story.append(Paragraph("Câu hỏi ôn tập", box_label_style))
            for j, q in enumerate(ch.review_questions, 1):
                story.append(Paragraph(f"{j}. {_esc(q)}", question_style))
        if i < len(book.chapters):
            story.append(PageBreak())

    def _on_cover(canvas, _doc):
        pass

    def _on_page(canvas, _doc):
        canvas.saveState()
        clean_title = prepare_pdf_plain_text(book.title)
        title_short = clean_title if len(clean_title) <= 60 else clean_title[:57] + "..."
        canvas.setFont(font_name, 9)
        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.drawString(56, A4[1] - 40, title_short)
        canvas.drawRightString(A4[0] - 56, 30, f"Trang {canvas.getPageNumber()}")
        canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
        canvas.setLineWidth(0.5)
        canvas.line(56, A4[1] - 46, A4[0] - 56, A4[1] - 46)
        canvas.restoreState()

    doc.multiBuild(story, onFirstPage=_on_cover, onLaterPages=_on_page)
    logger.info(f"Generated Book PDF at {file_path}")
