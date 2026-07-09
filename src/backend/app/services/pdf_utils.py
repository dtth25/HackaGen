"""Shared PDF helpers: Vietnamese-capable font registration for ReportLab."""

import os
from typing import Tuple

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/arial.ttf", "Arial", "Arial-Bold"),
    ("C:/Windows/Fonts/tahoma.ttf", "Tahoma", "Tahoma-Bold"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVu", "DejaVu-Bold"),
]

_cache: Tuple[str, str] = None


def register_vietnamese_fonts() -> Tuple[str, str]:
    """Register the first available Vietnamese-capable TTF (Arial -> Tahoma -> DejaVu) with
    ReportLab and return (regular_font_name, bold_font_name). Falls back to Helvetica (which
    cannot render Vietnamese diacritics) if none of the candidates exist on the host."""
    global _cache
    if _cache is not None:
        return _cache

    font_name = "Helvetica"
    font_bold = "Helvetica-Bold"
    for ttf_path, name, bold_name in _FONT_CANDIDATES:
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

    _cache = (font_name, font_bold)
    return _cache
