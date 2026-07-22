"""Fault-injection tests for upload-pipeline hardening: stage-preserving failures,
classified error messages, DB write retry, the startup stale-course sweep, and the admin
diagnostics endpoint's probe classification. All network calls are faked — nothing here
spends real OpenRouter quota."""

import tempfile
import shutil
from datetime import datetime, timedelta

from sqlalchemy.exc import OperationalError

from app.models.course import Course
from app.services.document_processor import DocumentProcessor, _classify_pipeline_error
from app.services.vector_store import VectorStore
from app.routers.admin import _classify_network_probe, _probe_result
from main import fail_stale_processing_courses

import app.services.database as db_service


def get_auth_headers(client, email: str = "diag_user@example.com"):
    reg_data = {"email": email, "password": "password123", "full_name": "Diag User"}
    res = client.post("/api/auth/register", json=reg_data)
    if res.status_code == 201:
        res = client.post("/api/auth/verify-email", json={"email": email, "code": "000000"})
    else:
        res = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- _classify_pipeline_error -----------------------------------------------------------


def test_classify_error_extraction_value_error_is_content_bucket():
    msg = _classify_pipeline_error(ValueError("No valid text could be extracted."), stage="extracting")
    assert "trích xuất" in msg.lower()


def test_classify_error_connection_failure_is_network_bucket():
    msg = _classify_pipeline_error(ConnectionError("Connection refused"), stage="embedding")
    assert "mạng" in msg.lower() or "kết nối" in msg.lower()


def test_classify_error_timeout_is_network_bucket():
    msg = _classify_pipeline_error(TimeoutError("Request timed out after 30s"), stage="embedding")
    assert "kết nối" in msg.lower()


def test_classify_error_auth_failure_is_config_bucket():
    msg = _classify_pipeline_error(Exception("401 Unauthorized: invalid_api_key"), stage="embedding")
    assert "api key" in msg.lower()


def test_classify_error_rate_limit_is_quota_bucket():
    msg = _classify_pipeline_error(Exception("429 rate limit exceeded"), stage="embedding")
    assert "hạn mức" in msg.lower() or "quá tải" in msg.lower()


def test_classify_error_unknown_embedding_failure_falls_back_to_provider_bucket():
    msg = _classify_pipeline_error(RuntimeError("something weird happened"), stage="embedding")
    assert "openrouter" in msg.lower()


# --- process_course stage preservation ----------------------------------------------------


def _write_sample_txt(tmp_dir: str) -> str:
    path = f"{tmp_dir}/sample.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            "Artificial Intelligence is transforming education and learning systems globally. "
            "This document has enough real words to survive the low-information chunk filter."
        )
    return path


def test_process_course_preserves_extracting_stage_on_failure(monkeypatch):
    temp_dir = tempfile.mkdtemp()
    try:
        vs = VectorStore(collection_name="test_diag_extract", persist_directory=temp_dir)
        processor = DocumentProcessor(vector_store=vs, chunk_size=200, chunk_overlap=20)

        def _boom(path, course_id):
            raise ValueError("Simulated corrupt file")

        monkeypatch.setattr(processor, "extract_and_chunk_file", _boom)

        result = processor.process_course("course_extract_fail", [_write_sample_txt(temp_dir)])

        assert result.status == "failed"
        assert "trích xuất" in result.error.lower() or "định dạng" in result.error.lower()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_process_course_preserves_embedding_stage_on_failure(monkeypatch):
    temp_dir = tempfile.mkdtemp()
    try:
        vs = VectorStore(collection_name="test_diag_embed", persist_directory=temp_dir)
        processor = DocumentProcessor(vector_store=vs, chunk_size=200, chunk_overlap=20)

        def _boom(*args, **kwargs):
            raise ConnectionError("Connection refused")

        monkeypatch.setattr(vs, "add_documents", _boom)

        result = processor.process_course("course_embed_fail", [_write_sample_txt(temp_dir)])

        assert result.status == "failed"
        assert "kết nối" in result.error.lower()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_process_course_end_to_end_status_reflects_db_stage(client, monkeypatch):
    """Full HTTP path: upload -> background pipeline fails at embedding -> /status shows
    stage="embedding" (not the old literal "failed") and a network-classified error."""
    from app.services import document_processor as dp_module

    headers = get_auth_headers(client, "diag_stage@example.com")

    def _boom(*args, **kwargs):
        raise ConnectionError("Connection refused")

    processor = dp_module.get_document_processor()
    monkeypatch.setattr(processor.vector_store, "add_documents", _boom)

    content = b"Artificial Intelligence course content with enough real words to pass filters."
    files = [("files", ("diag.txt", content, "text/plain"))]
    res_upload = client.post("/api/upload", headers=headers, files=files)
    assert res_upload.status_code == 201, res_upload.text
    course_id = res_upload.json()["course_id"]

    res_status = client.get(f"/api/course/{course_id}/status", headers=headers)
    data = res_status.json()
    assert data["status"] == "failed"
    assert data["stage"] == "embedding"
    assert "kết nối" in data["error"].lower()


# --- _update_course_db retry on OperationalError --------------------------------------------


def test_update_course_db_retries_on_operational_error_then_succeeds():
    temp_dir = tempfile.mkdtemp()
    try:
        vs = VectorStore(collection_name="test_diag_retry", persist_directory=temp_dir)
        processor = DocumentProcessor(vector_store=vs)

        course_id = "course_retry"
        real_factory = db_service.SessionLocal
        with real_factory() as db:
            db.add(Course(id=course_id, user_id="u1", status="processing", stage="extracting", progress=20))
            db.commit()

        calls = {"n": 0}
        real_session = real_factory()

        class _FlakyFactory:
            def __call__(self):
                calls["n"] += 1
                if calls["n"] < 3:
                    raise OperationalError("statement", {}, Exception("database is locked"))
                return real_session

        processor._update_course_db(
            course_id,
            status="ready",
            stage="completed",
            progress=100,
            db_session_factory=_FlakyFactory(),
        )

        with real_factory() as db:
            course = db.query(Course).filter(Course.id == course_id).first()
            assert course.status == "ready"
        assert calls["n"] == 3
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_update_course_db_gives_up_after_max_attempts_without_crashing():
    temp_dir = tempfile.mkdtemp()
    try:
        vs = VectorStore(collection_name="test_diag_giveup", persist_directory=temp_dir)
        processor = DocumentProcessor(vector_store=vs)

        def _always_locked():
            raise OperationalError("statement", {}, Exception("database is locked"))

        # Must not raise — a lost terminal write should be logged, not crash the pipeline.
        processor._update_course_db(
            "course_never_written",
            status="ready",
            stage="completed",
            progress=100,
            db_session_factory=_always_locked,
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# --- startup stale-processing sweep ----------------------------------------------------------


def test_fail_stale_processing_courses_sweeps_old_courses_only():
    factory = db_service.SessionLocal
    with factory() as db:
        stale = Course(
            id="course_stale",
            user_id="u1",
            status="processing",
            stage="embedding",
            progress=75,
            created_at=datetime.utcnow() - timedelta(minutes=30),
        )
        fresh = Course(
            id="course_fresh",
            user_id="u1",
            status="processing",
            stage="extracting",
            progress=20,
            created_at=datetime.utcnow(),
        )
        db.add_all([stale, fresh])
        db.commit()

    swept = fail_stale_processing_courses(db_session_factory=factory)
    assert swept == 1

    with factory() as db:
        stale_after = db.query(Course).filter(Course.id == "course_stale").first()
        fresh_after = db.query(Course).filter(Course.id == "course_fresh").first()
        assert stale_after.status == "failed"
        assert "gián đoạn" in stale_after.error_message
        assert fresh_after.status == "processing"


# --- admin diagnostics probe classification --------------------------------------------------


def test_probe_result_ok_when_prober_succeeds():
    assert _probe_result(lambda: None) == {"status": "ok"}


def test_probe_result_classifies_connection_error_as_unreachable():
    def _boom():
        raise ConnectionError("Connection refused")

    result = _probe_result(_boom)
    assert result["status"] == "unreachable"


def test_probe_result_classifies_auth_error_as_unauthorized():
    def _boom():
        raise Exception("401 Unauthorized")

    result = _probe_result(_boom)
    assert result["status"] == "unauthorized"


def test_classify_network_probe_generic_error_falls_back_to_error():
    assert _classify_network_probe(RuntimeError("mystery failure")) == "error"


def test_diagnostics_endpoint_requires_admin(client):
    headers = get_auth_headers(client, "diag_nonadmin@example.com")
    res = client.get("/api/admin/diagnostics", headers=headers)
    assert res.status_code == 403


def test_diagnostics_endpoint_skips_network_calls_in_test_mode(client):
    """PYTEST_CURRENT_TEST is always set while pytest runs, so the OpenRouter probes must
    short-circuit to "skipped" — this test would otherwise spend real API quota."""
    reg = client.post(
        "/api/auth/register",
        json={"email": "diag_admin@example.com", "password": "password123", "full_name": "Diag Admin"},
    )
    assert reg.status_code == 201
    client.post("/api/auth/verify-email", json={"email": "diag_admin@example.com", "code": "000000"})

    from app.services.database import SessionLocal
    from app.models.user import User

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "diag_admin@example.com").first()
        user.role = "admin"
        db.commit()

    login = client.post(
        "/api/auth/login", json={"email": "diag_admin@example.com", "password": "password123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    res = client.get("/api/admin/diagnostics", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["openrouter_key"]["status"] == "skipped"
    assert data["openrouter_embedding"]["status"] == "skipped"
    assert data["database"]["status"] == "ok"
