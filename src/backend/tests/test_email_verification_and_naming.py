"""Tests for resend-verification cooldown, admin bootstrap, the simplified (single-attempt)
course auto-naming behavior, and the OpenRouter fallback in LLMService."""

import time

from app.core.config import settings
from app.models.course import Course
from app.models.user import User
from app.services.database import SessionLocal
from app.services.document_processor import DocumentProcessor


def _auth_headers(client, email: str) -> dict:
    reg_data = {"email": email, "password": "password123", "full_name": "Test"}
    res = client.post("/api/auth/register", json=reg_data)
    if res.status_code == 201:
        res = client.post("/api/auth/verify-email", json={"email": email, "code": "000000"})
    else:
        res = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_resend_verification_is_generic_for_unknown_email(client):
    res = client.post("/api/auth/resend-verification", json={"email": "nobody@example.com"})
    assert res.status_code == 200
    assert "mã mới đã được gửi" in res.json()["message"]


def test_resend_verification_cooldown(client, monkeypatch):
    sent = []
    from app.services import email_service

    monkeypatch.setattr(email_service, "send_verification_code", lambda email, code: sent.append(code))

    client.post(
        "/api/auth/register",
        json={"email": "cooldown@example.com", "password": "password123"},
    )
    first_len = len(sent)
    assert first_len == 1  # register itself sends one

    # Immediate resend should be swallowed by the cooldown — no second send.
    client.post("/api/auth/resend-verification", json={"email": "cooldown@example.com"})
    assert len(sent) == first_len


def test_admin_bootstrap_is_idempotent(monkeypatch):
    from app.services.admin_seed import seed_default_admin

    monkeypatch.setattr(settings, "CREATE_DEFAULT_ADMIN", True)
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "boss@example.com")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "adminpass123")

    seed_default_admin()
    seed_default_admin()

    db = SessionLocal()
    try:
        admins = db.query(User).filter(User.email == "boss@example.com").all()
        assert len(admins) == 1
        assert admins[0].role == "admin"
        assert admins[0].is_verified is True
    finally:
        db.close()


def test_filename_fallback_title_strips_timestamp_and_extension():
    assert DocumentProcessor._filename_fallback_title("1730000000_Virtual Tree.pdf") == "Virtual Tree"
    assert DocumentProcessor._filename_fallback_title("notes.docx") == "notes"
    # No digits-only prefix before the underscore -> not treated as a timestamp.
    assert DocumentProcessor._filename_fallback_title("mid_term_notes.txt") == "mid_term_notes"


def test_course_naming_falls_back_to_filename_when_ai_unavailable(client, test_upload_dir):
    """No Gemini client in test/mock mode -> AI naming returns None -> the course must still
    end up with a real `name` (the cleaned filename), never left null waiting for a retry
    that no longer exists."""
    headers = _auth_headers(client, "naming_fallback@example.com")
    content = ("Nội dung tài liệu mẫu. " * 50).encode("utf-8")
    files = [("files", ("Bai Giang Vat Ly.txt", content, "text/plain"))]
    res = client.post("/api/upload", headers=headers, files=files)
    assert res.status_code == 201, res.text
    course_id = res.json()["course_id"]

    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        assert course.status == "ready", course.error_message
        assert course.name == "Bai Giang Vat Ly"
    finally:
        db.close()


def test_openrouter_fallback_used_when_gemini_exhausted(monkeypatch):
    """When Gemini's own retries are exhausted, _call_gemini_strict must try OpenRouter
    once (if configured) before giving up — transparent to callers."""
    from app.services.llm import LLMService
    from app.schemas.generator_output import CourseTitleOutput

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setattr(settings, "OPENROUTER_MODEL", "google/gemini-2.5-flash")

    service = LLMService()

    class _FakeModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("Gemini quota exhausted")

    class _FakeGeminiClient:
        models = _FakeModels()

    service.client = _FakeGeminiClient()

    class _FakeMessage:
        content = CourseTitleOutput(title="Đại Số Tuyến Tính").model_dump_json()

    class _FakeChoice:
        message = _FakeMessage()

    class _FakeCompletion:
        choices = [_FakeChoice()]

    class _FakeCompletions:
        def create(self, **kwargs):
            assert kwargs["model"] == "google/gemini-2.5-flash"
            return _FakeCompletion()

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeOpenRouterClient:
        chat = _FakeChat()

    monkeypatch.setattr(service, "_openrouter_client", _FakeOpenRouterClient())
    monkeypatch.setattr(time, "sleep", lambda *_: None)

    result = service._call_gemini_strict(
        prompt="test prompt",
        schema_model=CourseTitleOutput,
        fallback_fn=lambda: CourseTitleOutput(title=""),
        max_output_tokens=100,
        attempts=1,
    )
    assert result.title == "Đại Số Tuyến Tính"


def test_openrouter_not_configured_still_raises(monkeypatch):
    """Without OPENROUTER_API_KEY, behavior is unchanged — Gemini failure still raises."""
    from app.services.llm import LLMService, LLMGenerationError
    from app.schemas.generator_output import CourseTitleOutput

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")

    service = LLMService()

    class _FakeModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("Gemini quota exhausted")

    class _FakeGeminiClient:
        models = _FakeModels()

    service.client = _FakeGeminiClient()
    monkeypatch.setattr(time, "sleep", lambda *_: None)

    try:
        service._call_gemini_strict(
            prompt="test prompt",
            schema_model=CourseTitleOutput,
            fallback_fn=lambda: CourseTitleOutput(title=""),
            max_output_tokens=100,
            attempts=1,
        )
        assert False, "expected LLMGenerationError"
    except LLMGenerationError:
        pass
