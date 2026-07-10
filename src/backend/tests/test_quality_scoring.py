"""Tests for validate_and_score_output's citation-validity grounding checks."""

from app.schemas.generator_output import (
    BookChapter,
    BookOutput,
    BookSection,
    QuizOption,
    QuizOutput,
    QuizQuestion,
    SlideItem,
    SlidesOutput,
    validate_and_score_output,
)

_LONG_SECTION = " ".join(["noi dung"] * 200)  # >= 400 words across intro+sections


def _make_chapter(title: str, source_chunk_ids):
    return BookChapter(
        chapter_title=title,
        introduction=_LONG_SECTION,
        objectives=["Hieu duoc khai niem"],
        sections=[BookSection(title="Muc 1", content=_LONG_SECTION)],
        key_points=["Diem chinh"],
        review_questions=["Cau hoi on tap?"],
        source_chunk_ids=source_chunk_ids,
    )


def _make_book(chapters):
    return BookOutput(title="Sach", summary="Tom tat", preface="Loi noi dau", chapters=chapters)


def test_book_valid_citation_boosts_score():
    book = _make_book([_make_chapter(f"Chuong {i}", ["c1"]) for i in range(4)])
    _, score, warnings = validate_and_score_output(book, "book", valid_chunk_ids=["c1", "c2"])
    assert warnings == []
    assert score == 90  # base 80 + grounding boost (100% grounded ratio)


def test_book_invalid_citation_penalized_not_just_warned():
    """A chapter citing a chunk ID that was never retrieved must cost points, not just
    log a warning (this was the bug: invalid_refs were appended to warnings but never
    subtracted from the score)."""
    chapters = [_make_chapter(f"Chuong {i}", ["c1"]) for i in range(3)]
    chapters.append(_make_chapter("Chuong bia", ["chunk_khong_ton_tai"]))
    book = _make_book(chapters)

    _, score, warnings = validate_and_score_output(book, "book", valid_chunk_ids=["c1", "c2"])

    assert any("tham chiếu chunk không tồn tại" in w for w in warnings)
    # base 80, no grounding boost (3/4 = 75% < 80% threshold), -5 for the one invalid ref
    assert score == 75


def test_book_score_can_go_below_70_when_warnings_present():
    """Locks in that the old floor-bump (score<=70 with no warnings -> forced to 75) is
    gone: a genuinely bad, warning-covered score must not be silently inflated."""
    chapters = [_make_chapter(f"Chuong {i}", ["ma_bia"]) for i in range(4)]
    book = _make_book(chapters)

    _, score, warnings = validate_and_score_output(book, "book", valid_chunk_ids=["c1"])

    assert warnings  # every chapter's citation is invalid -> warnings must be non-empty
    assert score == 60  # 80 - 5*4 invalid refs, no bump


def test_slides_hallucinated_citation_not_counted_as_grounded():
    slides = SlidesOutput(
        title="Slide deck",
        slides=[
            SlideItem(slide_number=1, title="S1", bullet_points=["y 1"], source_chunk_ids=["ma_bia"]),
        ],
    )
    _, score, warnings = validate_and_score_output(slides, "slides", valid_chunk_ids=["c1"])
    assert any("tham chiếu chunk không tồn tại" in w for w in warnings)
    assert score == 75  # 80 - 5 for the one invalid ref, no grounding boost


def test_slides_valid_citation_counts_as_grounded():
    slides = SlidesOutput(
        title="Slide deck",
        slides=[
            SlideItem(slide_number=1, title="S1", bullet_points=["y 1"], source_chunk_ids=["c1"]),
        ],
    )
    _, score, warnings = validate_and_score_output(slides, "slides", valid_chunk_ids=["c1"])
    assert warnings == []
    assert score == 90


def test_quiz_invalid_citation_penalized_across_all_questions():
    quiz = QuizOutput(
        title="Quiz",
        questions=[
            QuizQuestion(
                question_number=i,
                question_text=f"Cau {i}?",
                options=[QuizOption(key=k, text=f"Dap an {k}") for k in ["A", "B", "C", "D"]],
                correct_answer="A",
                explanation="Vi day la dap an dung.",
                source_chunk_ids=["ma_bia"],
            )
            for i in range(1, 3)
        ],
    )
    _, score, warnings = validate_and_score_output(quiz, "quiz", valid_chunk_ids=["c1"])
    assert len([w for w in warnings if "tham chiếu chunk không tồn tại" in w]) == 2
    assert score == 70  # 80 - 5*2 invalid refs
