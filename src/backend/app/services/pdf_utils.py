"""Shared PDF helpers: Vietnamese-capable font registration for ReportLab, plus
`prepare_pdf_text` — the single chokepoint that turns raw LLM prose into text safe to
hand to a ReportLab `Paragraph()` (Unicode-flattened, multi-script font fallback,
glyph-checked, XML-escaped)."""

import os
from typing import Dict, List, Optional, Tuple
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


# Per-script fallback fonts, tried in order for any glyph the main Vietnamese font (Arial/
# Tahoma) can't render — Arial/Tahoma cover Latin + Vietnamese diacritics but not Devanagari
# (Hindi/Urdu-in-Devanagari-transliteration) or CJK (Chinese) source documents. Each entry is
# (registered name, .ttc/.ttf path, subfontIndex for the regular-weight face in that
# collection). NOTE: Urdu written in Arabic script is NOT covered — Arabic requires contextual
# glyph shaping (initial/medial/final letterforms) that ReportLab's Paragraph engine doesn't
# perform, so Arabic-script text would still render as unconnected/incorrect glyph forms even
# with a suitable font registered. This is a known limitation, not a bug.
_FALLBACK_FONT_CANDIDATES: List[Tuple[str, str, int]] = [
    ("C:/Windows/Fonts/Nirmala.ttc", "NirmalaUI", 0),  # Devanagari + other Indic scripts
    ("C:/Windows/Fonts/msyh.ttc", "MicrosoftYaHei", 0),  # CJK (Chinese)
    # Installed by fonts-noto-cjk in the production Debian image. Keep the Windows
    # candidates above so local development continues to use the OS fonts unchanged.
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "NotoSansCJK", 0),
    # ReportLab cannot embed Noto's CFF outlines from its TTC, so use the TrueType
    # WenQuanYi face installed alongside Noto for actual ReportLab paragraph runs.
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "WenQuanYiZenHei", 0),
]

_fallback_font_names: Optional[List[str]] = None
_fallback_font_info: Dict[str, Tuple[str, int]] = {}


def _register_fallback_fonts() -> List[str]:
    """Lazily register the per-script fallback fonts that exist on this host. Returns the
    list of registered font names, in priority order, for use as inline <font name="..."> tags."""
    global _fallback_font_names
    if _fallback_font_names is not None:
        return _fallback_font_names

    names: List[str] = []
    for path, name, subfont_index in _FALLBACK_FONT_CANDIDATES:
        if not os.path.exists(path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(name, path, subfontIndex=subfont_index))
            names.append(name)
            _fallback_font_info[name] = (path, subfont_index)
        except Exception:
            continue

    _fallback_font_names = names
    return names


_cmap_cache: Dict[Tuple[str, int], set] = {}
# Conservative fallback allowlist used only when no TTF was registered (Helvetica has no
# usable cmap info readily available here) — plain ASCII plus the Vietnamese diacritic set.
_LATIN1_VN_FALLBACK = (
    "áàảãạăắằẳẵặâấầẩẫậđéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ"
    "ÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ"
)


def _cmap_for(ttf_path: str, subfont_index: int = 0) -> set:
    key = (ttf_path, subfont_index)
    if key not in _cmap_cache:
        try:
            font = _FontToolsTTFont(ttf_path, fontNumber=subfont_index, lazy=True)
            _cmap_cache[key] = set(font.getBestCmap().keys())
        except TypeError:
            # Plain .ttf (not a collection) — fontNumber isn't a valid kwarg for those.
            try:
                font = _FontToolsTTFont(ttf_path, lazy=True)
                _cmap_cache[key] = set(font.getBestCmap().keys())
            except Exception:
                _cmap_cache[key] = set()
        except Exception:
            _cmap_cache[key] = set()
    return _cmap_cache[key]


def _filter_unsupported_glyphs(s: str) -> str:
    """Swap any character the registered PDF font can't render for '?' instead of letting
    ReportLab silently draw a .notdef tofu box. Must run after clean_text() — clean_text's
    own generated sub/superscript characters aren't guaranteed to be in Arial/Tahoma's cmap
    either, so this needs to check the final text, not just raw LLM-emitted symbols. Single-
    font filter only (no script fallback) — used for canvas.drawString text, which can't mix
    fonts within one call the way a Paragraph's inline <font> markup can."""
    if not s:
        return s
    register_vietnamese_fonts()  # ensure _registered_ttf_path is populated
    if not _registered_ttf_path:
        return "".join(c if (ord(c) < 128 or c in _LATIN1_VN_FALLBACK or c.isspace()) else "?" for c in s)
    cmap = _cmap_for(_registered_ttf_path)
    if not cmap:
        return s
    return "".join(c if (ord(c) in cmap or c.isspace()) else "?" for c in s)


def _apply_script_fallback(s: str) -> str:
    """Segment text into runs by which registered font can render each character — the main
    Vietnamese-capable font first, then per-script fallbacks (Devanagari, CJK) in priority
    order — and wrap fallback-font runs in ReportLab's inline `<font name="...">` markup so
    those glyphs render instead of a run of '?'. A character none of the registered fonts
    cover still becomes '?' (e.g. Arabic-script Urdu — see _FALLBACK_FONT_CANDIDATES note).
    Each run is XML-escaped individually; safe because run boundaries never split an XML
    metacharacter (<, >, &) from its neighbors — those are always single-run ASCII."""
    if not s:
        return s
    register_vietnamese_fonts()
    fallback_names = _register_fallback_fonts()
    main_cmap = _cmap_for(_registered_ttf_path) if _registered_ttf_path else set()

    def _tag_for(c: str) -> Optional[str]:
        """None = draw in the main font (incl. '?' substitution below); otherwise a
        registered fallback font name to wrap this character's run in."""
        if c.isspace() or ord(c) < 128:
            return None
        if main_cmap:
            if ord(c) in main_cmap:
                return None
        elif c in _LATIN1_VN_FALLBACK:
            return None
        for name in fallback_names:
            path, subfont_index = _fallback_font_info[name]
            if ord(c) in _cmap_for(path, subfont_index):
                return name
        return "?"

    runs: List[Tuple[Optional[str], str]] = []
    for c in s:
        tag = _tag_for(c)
        char_out = "?" if tag == "?" else c
        run_key = None if tag == "?" else tag
        if runs and runs[-1][0] == run_key:
            runs[-1] = (run_key, runs[-1][1] + char_out)
        else:
            runs.append((run_key, char_out))

    parts = []
    for font_name, chunk in runs:
        escaped = _xml_escape(chunk)
        parts.append(f'<font name="{font_name}">{escaped}</font>' if font_name else escaped)
    return "".join(parts)


def _clean_and_filter(text: Optional[str]) -> str:
    cleaned = clean_text(text or "")
    return _filter_unsupported_glyphs(cleaned)


def prepare_pdf_text(text: Optional[str]) -> str:
    """LLM prose -> ReportLab-Paragraph-safe markup: strip LaTeX/Markdown to Unicode
    (clean_text), segment by script and apply per-script font fallback (Devanagari, CJK —
    see _apply_script_fallback), XML-escape, then convert newlines to <br/>. This is the one
    chokepoint for text destined for a static PDF/PPTX export — the live React UI renders raw
    Markdown/LaTeX directly via KaTeX instead."""
    cleaned = clean_text(text or "")
    marked = _apply_script_fallback(cleaned)
    return marked.replace("\n", "<br/>")


def prepare_pdf_plain_text(text: Optional[str]) -> str:
    """Same cleanup as `prepare_pdf_text` but WITHOUT XML-escaping or script-fallback markup —
    for text drawn directly via ReportLab canvas methods (e.g. `canvas.drawString`) rather
    than through a `Paragraph`, which don't parse markup (so no multi-font runs) and would
    render escaped entities like `&amp;` literally."""
    return _clean_and_filter(text)


def get_vietnamese_ttf_path() -> Optional[str]:
    """Return the filesystem path of the registered Vietnamese-capable TTF (if any) — the same
    font file register_vietnamese_fonts() wired into ReportLab. Lets other renderers (e.g.
    Pillow, which needs a raw font path rather than a registered ReportLab font name) draw the
    same glyph set instead of re-implementing the candidate search."""
    register_vietnamese_fonts()
    return _registered_ttf_path
