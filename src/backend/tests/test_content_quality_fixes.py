"""Tests for the content-generation bug sweep: topic/title ID-stripping, the internal
"chunk mention" leak sanitizer, the quiz-key PDF no longer printing "Mức độ Bloom", and the
course-naming lazy-retry / name_pending flag."""

import json

import fitz
from app.models.course import Course
from app.schemas.generator_output import (
    QuizOption,
    QuizOutput,
    QuizQuestion,
    validate_and_score_output,
)
from app.services.database import SessionLocal
from app.services.document_processor import MAX_TITLE_ATTEMPTS
from app.services.generator import Generator, _strip_leading_id_token
from app.services.vector_store import get_vector_store


def test_strip_leading_id_token_removes_digit_heavy_prefix():
    assert _strip_leading_id_token("NLC416-14jh005357-58048_Tan Trung Hoa Quoc Ngu") == "Tan Trung Hoa Quoc Ngu"


def test_strip_leading_id_token_preserves_short_number_titles():
    # A real title starting with a short number (e.g. "3D Printing") must survive untouched —
    # only leading tokens with >=4 digits are treated as a noise identifier code.
    assert _strip_leading_id_token("3D Printing Basics") == "3D Printing Basics"


def test_strip_leading_id_token_noop_without_separator():
    assert _strip_leading_id_token("Machine Learning 101") == "Machine Learning 101"


def test_resolve_topic_sanitizes_filename_fallback():
    course_id = "topic_sanitize_test"
    db = SessionLocal()
    try:
        course = Course(
            id=course_id,
            user_id="topic_test_user",
            filenames=["NLC416-14jh005357-58048_Tan Trung Hoa.pdf"],
            status="ready",
        )
        db.add(course)
        db.commit()
    finally:
        db.close()

    gen = Generator(vector_store=get_vector_store(), llm=None)
    topic = gen._resolve_topic(course_id, topic=None)
    assert topic == "Tan Trung Hoa"


def test_strip_chunk_mentions_replaces_reference_and_warns():
    quiz = QuizOutput(
        title="Quiz",
        questions=[
            QuizQuestion(
                question_number=1,
                question_text="Cau hoi mau?",
                options=[QuizOption(key=k, text=f"Dap an {k}") for k in ["A", "B", "C", "D"]],
                correct_answer="A",
                explanation="Dua vao chunk_3, day la dap an dung.",
                source_chunk_ids=["chunk_3"],
            )
        ],
    )
    validated, _score, warnings = validate_and_score_output(quiz, "quiz", valid_chunk_ids=["chunk_3"])
    assert "chunk_3" not in validated.questions[0].explanation
    assert "tài liệu" in validated.questions[0].explanation
    assert any("rò rỉ tham chiếu chunk nội bộ" in w for w in warnings)


def test_strip_chunk_mentions_noop_when_clean():
    quiz = QuizOutput(
        title="Quiz",
        questions=[
            QuizQuestion(
                question_number=1,
                question_text="Cau hoi mau?",
                options=[QuizOption(key=k, text=f"Dap an {k}") for k in ["A", "B", "C", "D"]],
                correct_answer="A",
                explanation="Day la dap an dung vi ly do ro rang.",
                source_chunk_ids=["chunk_1"],
            )
        ],
    )
    validated, _score, warnings = validate_and_score_output(quiz, "quiz", valid_chunk_ids=["chunk_1"])
    assert validated.questions[0].explanation == "Day la dap an dung vi ly do ro rang."
    assert not any("rò rỉ tham chiếu chunk nội bộ" in w for w in warnings)


def test_quiz_key_pdf_has_no_bloom_jargon(test_upload_dir):
    quiz = QuizOutput(
        title="Bo De Kiem Tra",
        questions=[
            QuizQuestion(
                question_number=1,
                question_text="Cau hoi mau?",
                difficulty="Medium",
                options=[QuizOption(key=k, text=f"Dap an {k}") for k in ["A", "B", "C", "D"]],
                correct_answer="A",
                explanation="Day la dap an dung.",
                source_chunk_ids=["chunk_1"],
            )
        ],
    )
    gen = Generator(vector_store=get_vector_store(), llm=None)
    course_id = "quiz_key_pdf_test"
    pdf_path = gen._generate_pdf_quiz_key(course_id, quiz)

    doc = fitz.open(pdf_path)
    full_text = "\n".join(page.get_text() for page in doc)
    doc.close()

    assert "Bloom" not in full_text
    assert "Mức độ Bloom" not in full_text
    assert "Vừa" in full_text  # Vietnamese difficulty label instead


def _auth_headers(client, email: str) -> dict:
    reg_data = {"email": email, "password": "password123", "full_name": "Naming Test"}
    res = client.post("/api/auth/register", json=reg_data)
    if res.status_code != 201:
        res = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_name_pending_true_for_untitled_ready_course(client):
    """A ready course with no AI name yet, and attempts not exhausted, must report
    name_pending=True so the frontend shows "Đang đặt tên..." and disables manual rename."""
    headers = _auth_headers(client, "naming_pending@example.com")
    res = client.post("/api/courses", headers=headers, json={"filenames": ["doc.pdf"]})
    course_id = res.json()["id"]

    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        course.status = "ready"
        db.commit()
    finally:
        db.close()

    status_res = client.get(f"/api/course/{course_id}/status", headers=headers)
    assert status_res.status_code == 200
    body = status_res.json()
    assert body["name"] is None
    assert body["name_pending"] is True


def test_name_pending_false_once_attempts_exhausted(client):
    """Once title_attempts reaches MAX_TITLE_ATTEMPTS with still no name, name_pending must
    flip to False so the user can manually rename instead of being stuck forever."""
    headers = _auth_headers(client, "naming_exhausted@example.com")
    res = client.post("/api/courses", headers=headers, json={"filenames": ["doc.pdf"]})
    course_id = res.json()["id"]

    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        course.status = "ready"
        course.metadata_json = json.dumps({"title_attempts": MAX_TITLE_ATTEMPTS})
        db.commit()
    finally:
        db.close()

    status_res = client.get(f"/api/course/{course_id}/status", headers=headers)
    assert status_res.status_code == 200
    body = status_res.json()
    assert body["name"] is None
    assert body["name_pending"] is False


def test_name_pending_false_once_name_set():
    """Once a name exists (AI-generated or manually renamed), name_pending must be False
    regardless of attempt count."""
    from app.routers.courses import _title_pending

    course = Course(id="x", user_id="u", name="Đã có tên", status="ready")
    assert _title_pending(course) is False
