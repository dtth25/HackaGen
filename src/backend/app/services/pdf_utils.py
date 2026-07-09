"""Shared PDF helpers: Vietnamese-capable font registration for ReportLab, plus
`prepare_pdf_text` — the single chokepoint that turns raw LLM prose into text safe to
hand to a ReportLab `Paragraph()` (Unicode-flattened, glyph-checked, XML-escaped)."""

import os
from typing import Optional, Tuple
from xml.sax.saxutils import escape as _xml_escape

from fontTools.ttLib import TTFont as _FontToolsTTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.services.text_format import clean_text

_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/arial.ttf", "Arial", "Arial-Bold"),
    ("C:/Windows/Fonts/tahoma.ttf", "Tahoma", "Tahoma-Bold"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVu", "DejaVu-Bold"),
]

_cache: Optional[Tuple[str, str]] = None
_registered_ttf_path: Optional[str] = None


def register_vietnamese_fonts() -> Tuple[str, str]:
    """Register the first available Vietnamese-capable TTF (Arial -> Tahoma -> DejaVu) with
    ReportLab and return (regular_font_name, bold_font_name). Falls back to Helvetica (which
    cannot render Vietnamese diacritics) if none of the candidates exist on the host."""
    global _cache, _registered_ttf_path
    if _cache is not None:
        return _cache

    font_name = "Helvetica"
    font_bold = "Helvetica-Bold"
    for ttf_path, name, bold_name in _FONT_CANDIDATES:
        if os.path.exists(ttf_path):
            try:
                pdfmetrics.registerFont(TTFont(name, ttf_path))
                font_name = name
                _registered_ttf_path = ttf_path
                bold_path = ttf_path.replace(".ttf", "bd.ttf") if "arial" in ttf_path else ttf_path
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                    font_bold = bold_name
                else:
                    font_bold = name
                break
            except Exception:
                continue

    _cache = (font_name, font_bold)
    return _cache


_cmap_cache: dict[str, set] = {}
# Conservative fallback allowlist used only when no TTF was registered (Helvetica has no
# usable cmap info readily available here) — plain ASCII plus the Vietnamese diacritic set.
_LATIN1_VN_FALLBACK = (
    "áàảãạăắằẳẵặâấầẩẫậđéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ"
    "ÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ"
)


def _cmap_for(ttf_path: str) -> set:
    if ttf_path not in _cmap_cache:
        try:
            font = _FontToolsTTFont(ttf_path, lazy=True)
            _cmap_cache[ttf_path] = set(font.getBestCmap().keys())
        except Exception:
            _cmap_cache[ttf_path] = set()
    return _cmap_cache[ttf_path]


def _filter_unsupported_glyphs(s: str) -> str:
    """Swap any character the registered PDF font can't render for '?' instead of letting
    ReportLab silently draw a .notdef tofu box. Must run after clean_text() — clean_text's
    own generated sub/superscript characters aren't guaranteed to be in Arial/Tahoma's cmap
    either, so this needs to check the final text, not just raw LLM-emitted symbols."""
    if not s:
        return s
    register_vietnamese_fonts()  # ensure _registered_ttf_path is populated
    if not _registered_ttf_path:
        return "".join(c if (ord(c) < 128 or c in _LATIN1_VN_FALLBACK or c.isspace()) else "?" for c in s)
    cmap = _cmap_for(_registered_ttf_path)
    if not cmap:
        return s
    return "".join(c if (ord(c) in cmap or c.isspace()) else "?" for c in s)


def _clean_and_filter(text: Optional[str]) -> str:
    cleaned = clean_text(text or "")
    return _filter_unsupported_glyphs(cleaned)


def prepare_pdf_text(text: Optional[str]) -> str:
    """LLM prose -> ReportLab-Paragraph-safe markup: strip LaTeX/Markdown to Unicode
    (clean_text), drop glyphs the registered font can't render, XML-escape, then convert
    newlines to <br/>. This is the one chokepoint for text destined for a static PDF/PPTX
    export — the live React UI renders raw Markdown/LaTeX directly via KaTeX instead."""
    return _xml_escape(_clean_and_filter(text)).replace("\n", "<br/>")


def prepare_pdf_plain_text(text: Optional[str]) -> str:
    """Same cleanup as `prepare_pdf_text` but WITHOUT XML-escaping — for text drawn directly
    via ReportLab canvas methods (e.g. `canvas.drawString`) rather than through a `Paragraph`,
    which don't parse markup and would render escaped entities like `&amp;` literally."""
    return _clean_and_filter(text)
