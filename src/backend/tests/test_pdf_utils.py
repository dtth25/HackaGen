"""Unit tests for pdf_utils.prepare_pdf_text — the chokepoint that turns raw LLM prose into
text safe to hand to a ReportLab Paragraph() (Unicode-flattened, glyph-checked, XML-escaped)."""

from app.services.pdf_utils import prepare_pdf_plain_text, prepare_pdf_text


def test_escapes_xml_special_characters():
    result = prepare_pdf_text("n < m && List<T> AT&T")
    assert "<" not in result.replace("&lt;", "").replace("&amp;", "")
    assert "&lt;" in result
    assert "&amp;" in result


def test_newline_becomes_br_tag():
    assert prepare_pdf_text("dòng 1\ndòng 2") == "dòng 1<br/>dòng 2"


def test_flattens_latex_before_escaping():
    result = prepare_pdf_text(r"\alpha \leq \beta")
    assert result == "α ≤ β"


def test_none_and_empty_input_safe():
    assert prepare_pdf_text(None) == ""
    assert prepare_pdf_text("") == ""


def test_glyph_filter_swaps_unsupported_codepoint():
    # A Private-Use-Area codepoint is guaranteed to have no glyph in any real font — must
    # degrade to '?' instead of silently producing a .notdef tofu box downstream.
    result = prepare_pdf_plain_text(chr(0xE000))
    assert result == "?"


def test_glyph_filter_preserves_vietnamese_diacritics():
    text = "Tiếng Việt bình thường"
    assert prepare_pdf_plain_text(text) == text


def test_plain_text_variant_does_not_escape():
    # Used for text drawn directly via canvas.drawString (no XML parsing) — escaping here
    # would make literal "&" render as the text "&amp;" instead of "&".
    assert prepare_pdf_plain_text("AT&T") == "AT&T"
