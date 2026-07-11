"""Tests for the regeneration cap: the first generation of an artifact is always free,
only subsequent manual regenerations (after the artifact already reached ready/error)
count against Generator.MAX_REGENERATIONS."""

import json
from app.models.course import Course
from app.services.database import SessionLocal
from app.services.generator import MAX_REGENERATIONS, Generator


def _make_course(course_id: str, artifact_status: dict | None = None) -> None:
    db = SessionLocal()
    try:
        meta = {"study_pack": {"artifacts": artifact_status or {}}}
        course = Course(
            id=course_id,
            user_id="regen_test_user",
            filenames=["doc.pdf"],
            status="ready",
            metadata_json=json.dumps(meta, ensure_ascii=False),
        )
        db.add(course)
        db.commit()
    finally:
        db.close()


def test_first_generation_never_counted_or_blocked():
    """An artifact with no prior status (never generated) is always allowed and free."""
    course_id = "regen_first_gen"
    _make_course(course_id, artifact_status={})
    gen = Generator(vector_store=None, llm=None)

    allowed, used, max_allowed = gen.check_and_record_regen_attempt(course_id, "book")

    assert allowed is True
    assert used == 0
    assert max_allowed == MAX_REGENERATIONS
    assert gen.get_regen_usage(course_id).get("book", 0) == 0


def test_processing_status_is_not_a_regen_either():
    """A currently-in-progress artifact (status="processing") is also not a completed
    prior attempt, so a concurrent trigger still doesn't count against the cap."""
    course_id = "regen_processing"
    _make_course(course_id, artifact_status={"book": {"status": "processing"}})
    gen = Generator(vector_store=None, llm=None)

    allowed, used, _ = gen.check_and_record_regen_attempt(course_id, "book")

    assert allowed is True
    assert used == 0


def test_regen_allowed_up_to_max_then_blocked():
    """Once an artifact has reached ready/error, subsequent calls count against the cap —
    allowed up to MAX_REGENERATIONS, then blocked without incrementing further."""
    course_id = "regen_capped"
    _make_course(course_id, artifact_status={"book": {"status": "ready"}})
    gen = Generator(vector_store=None, llm=None)

    for i in range(1, MAX_REGENERATIONS + 1):
        allowed, used, max_allowed = gen.check_and_record_regen_attempt(course_id, "book")
        assert allowed is True, f"attempt {i} should be allowed"
        assert used == i
        assert max_allowed == MAX_REGENERATIONS

    # One more than the cap must be rejected, and the counter must not exceed the cap.
    allowed, used, max_allowed = gen.check_and_record_regen_attempt(course_id, "book")
    assert allowed is False
    assert used == MAX_REGENERATIONS

    # Rejected attempts don't silently keep incrementing past the cap either.
    allowed2, used2, _ = gen.check_and_record_regen_attempt(course_id, "book")
    assert allowed2 is False
    assert used2 == MAX_REGENERATIONS


def test_regen_after_error_status_also_counts():
    """A regen triggered after a failed ("error") attempt counts the same as after "ready" —
    both represent "this artifact was already attempted once"."""
    course_id = "regen_after_error"
    _make_course(course_id, artifact_status={"quiz": {"status": "error"}})
    gen = Generator(vector_store=None, llm=None)

    allowed, used, _ = gen.check_and_record_regen_attempt(course_id, "quiz")

    assert allowed is True
    assert used == 1


def test_regen_counts_isolated_per_artifact():
    """Regenerating "book" must not consume "slides"'s separate budget."""
    course_id = "regen_isolated"
    _make_course(
        course_id,
        artifact_status={"book": {"status": "ready"}, "slides": {"status": "ready"}},
    )
    gen = Generator(vector_store=None, llm=None)

    for _ in range(MAX_REGENERATIONS):
        allowed, _, _ = gen.check_and_record_regen_attempt(course_id, "book")
        assert allowed is True

    # Book is now exhausted...
    allowed_book, _, _ = gen.check_and_record_regen_attempt(course_id, "book")
    assert allowed_book is False

    # ...but slides, never touched, still has its full budget.
    allowed_slides, used_slides, _ = gen.check_and_record_regen_attempt(course_id, "slides")
    assert allowed_slides is True
    assert used_slides == 1


def test_generate_endpoint_returns_429_when_limit_reached(client):
    """End-to-end: once an artifact's regen budget is exhausted, POST /api/generate-book
    must return 429 with a clear message instead of silently queueing another job."""
    reg_data = {"email": "regen_api@example.com", "password": "password123", "full_name": "Regen User"}
    res = client.post("/api/auth/register", json=reg_data)
    if res.status_code == 201:
        res = client.post("/api/auth/verify-email", json={"email": "regen_api@example.com", "code": "000000"})
    else:
        res = client.post("/api/auth/login", json={"email": "regen_api@example.com", "password": "password123"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    files = [("files", ("regen_test.pdf", b"Dummy AI doc content for regen limit testing", "application/pdf"))]
    res_upload = client.post("/api/upload", headers=headers, files=files)
    assert res_upload.status_code == 201
    course_id = res_upload.json()["course_id"]

    # First generation always succeeds and is free (background task runs synchronously
    # under TestClient, so the artifact reaches "ready" before the request returns).
    res_gen = client.post(f"/api/generate-book?course_id={course_id}", headers=headers)
    assert res_gen.status_code == 200
    assert res_gen.json()["regen_used"] == 0

    # Each subsequent regeneration counts, up to the cap.
    for i in range(1, MAX_REGENERATIONS + 1):
        res_regen = client.post(f"/api/generate-book?course_id={course_id}", headers=headers)
        assert res_regen.status_code == 200, res_regen.text
        assert res_regen.json()["regen_used"] == i

    # One more than the cap must be rejected with 429.
    res_blocked = client.post(f"/api/generate-book?course_id={course_id}", headers=headers)
    assert res_blocked.status_code == 429
    assert "giới hạn" in res_blocked.json()["detail"]

    # The artifact-status envelope must also reflect the exhausted budget.
    res_status = client.get(f"/api/course/{course_id}/book", headers=headers)
    assert res_status.status_code == 200
    body = res_status.json()
    assert body["regen_used"] == MAX_REGENERATIONS
    assert body["regen_max"] == MAX_REGENERATIONS
