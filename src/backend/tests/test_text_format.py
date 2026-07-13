"""Unit tests for text_format.clean_text — the Unicode-flattening fallback used only for
static PDF/PPTX export (see pdf_utils.prepare_pdf_text). The live React UI no longer goes
through this function; it renders raw Markdown/LaTeX via KaTeX instead."""

from app.services.text_format import clean_text


def test_fraction_stripped():
    assert clean_text(r"\frac{a}{b}") == "a/b"


def test_wrap_command_stripped():
    assert clean_text(r"\text{hello world}") == "hello world"


def test_latex_named_functions_kept_as_words():
    # \log must survive as the word "log", not be silently deleted like a generic
    # leftover command (regression: "O(n \cdot \log n)" used to become "O(n · n)").
    assert clean_text(r"O(n \cdot \log n)") == "O(n · log n)"


def test_greek_letters_mapped():
    assert clean_text(r"\alpha + \beta") == "α + β"


def test_comparison_operators_mapped():
    assert clean_text(r"x \leq y \geq z") == "x ≤ y ≥ z"


def test_unicode_escape_decoded():
    # A literal "\\u2264"-style escape sequence (e.g. from a double-encoded JSON string)
    # must be decoded to the real "≤" character, not left as escaped-looking text.
    assert clean_text("x \\u2264 y") == "x ≤ y"


def test_bold_and_italic_markdown_stripped():
    assert clean_text("**quan trọng**") == "quan trọng"
    assert clean_text("*quan trọng*") == "quan trọng"


def test_commonmark_flanking_rule_preserves_multiplication():
    # Real model output observed in production: spaced "*" is multiplication, not markdown
    # emphasis, and must survive untouched (CommonMark flanking rule: no whitespace touching
    # the delimiters counts as emphasis).
    text = "w * cnt(u) * (K - cnt(u))"
    assert clean_text(text) == text


def test_tight_arithmetic_asterisks_preserved():
    assert clean_text("2*3*4 = 24") == "2*3*4 = 24"


def test_heading_and_blockquote_stripped():
    assert clean_text("## Tiêu đề") == "Tiêu đề"
    assert clean_text("> trích dẫn") == "trích dẫn"


def test_missing_subscript_letters_do_not_crash():
    # Unicode has no subscript codepoints for b, c, d, f, g, q, w, y, z — clean_text must
    # degrade gracefully (leave the letter as-is) instead of raising or mangling the string.
    for letter in "bcdfgqwyz":
        result = clean_text(f"x_{letter}")
        assert isinstance(result, str)
        assert letter in result


def test_simple_subscript_brace_converts_known_letters():
    result = clean_text(r"VT_{size}")
    assert "VT" in result
    # 's', 'i', 'e' have subscript glyphs; 'z' does not and stays plain — this is the
    # documented mixed-baseline limitation of the Unicode-flattening fallback.
    assert "z" in result


def test_complex_subscript_expression_unwraps_with_space():
    result = clean_text(r"\lim_{x \to \infty} f(x)")
    assert "lim" in result
    assert "x → ∞" in result


def test_idempotent():
    samples = [
        r"\frac{a}{b} + \alpha \leq \beta",
        "**bold** and *italic* and `code`",
        "w * cnt(u) * (K - cnt(u))",
        r"O(n \log n)",
        "Tiếng Việt bình thường, không LaTeX.",
    ]
    for s in samples:
        once = clean_text(s)
        twice = clean_text(once)
        assert once == twice


def test_empty_and_none_are_noop():
    assert clean_text("") == ""
    assert clean_text(None) is None


def test_bracket_array_indexing_survives_untouched():
    # Literal square-bracket array/DP-table notation (the convention prompts now instruct
    # the LLM to use instead of "_"-subscripts) must pass through clean_text unchanged —
    # no rule here strips or reinterprets "[" / "]".
    assert clean_text("P[i]") == "P[i]"
    assert clean_text("DP[i][j]") == "DP[i][j]"
    assert clean_text("A[i][j-1]") == "A[i][j-1]"
