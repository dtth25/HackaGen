"""Regression coverage for the QA-sweep findings: a real lost-update race in version
reservation, missing cross-user isolation coverage on version endpoints, and a defensive
key-redaction guarantee on the admin diagnostics probe."""

import json
import threading
import time
from datetime import datetime, timedelta

from app.models.course import Course
from app.routers.admin import _probe_result
from app.services.generator import Generator
from app.services.versioning import GenerationInFlightError, VersionCapReachedError

import app.services.database as db_service


def get_auth_headers(client, email: str):
    reg_data = {"email": email, "password": "password123", "full_name": "Owner Test"}
    res = client.post("/api/auth/register", json=reg_data)
    if res.status_code == 201:
        res = client.post("/api/auth/verify-email", json={"email": email, "code": "000000"})
    else:
        res = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- Concurrency: prepare_artifact_version must never lose a reservation -----------------


def _slow_commit_session_factory(delay_seconds: float):
    """A session whose commit() sleeps briefly before actually committing — widens the
    critical-section window so a second, concurrently-started caller has a real chance to
    interleave if the reservation lock isn't actually serializing them."""
    def factory():
        session = db_service.SessionLocal()
        original_commit = session.commit

        def _slow_commit():
            time.sleep(delay_seconds)
            return original_commit()

        session.commit = _slow_commit
        return session

    return factory


def _seed_course_with_book_version(course_id: str, version_id: str, status: str, updated_at_iso: str, label: str):
    """Directly write a book version into Course.metadata_json, bypassing
    prepare_artifact_version — lets a test start from a specific pre-existing state
    (e.g. a stale in-flight job, or several already-terminal versions) instead of only
    being able to reach states prepare_artifact_version itself would produce."""
    with db_service.SessionLocal() as db:
        db.add(Course(id=course_id, user_id="u1", status="ready", stage="completed", progress=100))
        db.commit()
        course = db.query(Course).filter(Course.id == course_id).first()
        course.metadata_json = json.dumps({
            "study_pack": {"artifacts": {"book": {"active": None, "versions": {
                version_id: {
                    "options": {"detail_level": "Tiêu chuẩn"}, "label": label, "topic": None,
                    "user_prompt": "", "path": version_id, "status": status, "error": None,
                    "progress": 50, "created_at": updated_at_iso, "started_at": updated_at_iso,
                    "updated_at": updated_at_iso,
                }
            }}}}
        })
        db.commit()


def test_prepare_artifact_version_concurrent_retries_of_a_stale_job_never_both_win():
    """Confirmed bug from the QA sweep: a book version stuck 'processing' past the 10-minute
    stale threshold (job genuinely still running, just slow) gets reaped and re-admitted for
    retry. Two concurrent retry requests for that SAME stale version (e.g. a double-click)
    must not both succeed — if they did, two background generation tasks would both call
    AtomicArtifactDirectory(version_id).prepare(), which destructively rmtrees the shared
    .tmp staging directory, so the second writer wipes whatever the first was mid-write on.
    The lock must ensure exactly one caller reaps+re-reserves the slot; the other must see
    the now-freshly-updated 'processing' entry and correctly back off with
    GenerationInFlightError instead of also reaping it."""
    course_id = "race_course_stale_retry"
    version_id = "stale-version-1"
    stale_updated_at = (datetime.utcnow() - timedelta(minutes=15)).isoformat()  # past book's 10-min threshold
    _seed_course_with_book_version(course_id, version_id, "processing", stale_updated_at, "Tiêu chuẩn")

    generator = Generator(vector_store=None, llm=None)
    results = {}

    def _retry(name: str, delay: float):
        try:
            results[name] = generator.prepare_artifact_version(
                course_id, "book", {"detail_level": "Tiêu chuẩn"}, retry_version_id=version_id,
                db_session_factory=_slow_commit_session_factory(delay),
            )
        except Exception as e:
            results[name] = e

    t1 = threading.Thread(target=_retry, args=("first", 0.05))
    t2 = threading.Thread(target=_retry, args=("second", 0.0))
    t1.start()
    time.sleep(0.01)  # let t1 acquire the lock and enter its slow commit first
    t2.start()
    t1.join()
    t2.join()

    outcomes = list(results.values())
    successes = [o for o in outcomes if isinstance(o, str)]
    blocked = [o for o in outcomes if isinstance(o, GenerationInFlightError)]
    assert len(successes) == 1, f"expected exactly one winner, got: {outcomes}"
    assert len(blocked) == 1, f"expected the loser to be blocked as in-flight, got: {outcomes}"
    assert successes[0] == version_id


def test_prepare_artifact_version_lock_is_per_course_and_artifact():
    """Different (course, artifact) pairs must not serialize against each other — the lock
    is scoped, not global, so unrelated reservations aren't needlessly blocked."""
    from app.services.generator import _get_version_reservation_lock

    lock_a = _get_version_reservation_lock("course_x", "book")
    lock_b = _get_version_reservation_lock("course_x", "book")
    lock_c = _get_version_reservation_lock("course_x", "quiz")
    lock_d = _get_version_reservation_lock("course_y", "book")

    assert lock_a is lock_b
    assert lock_a is not lock_c
    assert lock_a is not lock_d


def test_prepare_artifact_version_rejects_a_new_version_once_cap_is_reached():
    """Deterministic pin for the cap boundary (>= not >, per the QA sweep's read of the
    code): with 3 terminal book versions already on a course (the cap), a 4th NEW
    reservation must be rejected, not silently accepted as a 4th slot. Not written as a
    concurrency test — under the fix above, a NEW reservation always immediately becomes
    'processing' and blocks any other concurrent attempt via GenerationInFlightError before
    it could ever race the cap check itself, so the interesting boundary condition here is
    just the plain `>=` comparison, which is what this pins."""
    course_id = "cap_boundary_course"
    now_iso = datetime.utcnow().isoformat()
    with db_service.SessionLocal() as db:
        db.add(Course(id=course_id, user_id="u1", status="ready", stage="completed", progress=100))
        db.commit()
        course = db.query(Course).filter(Course.id == course_id).first()
        versions = {
            f"existing-{i}": {
                "options": {"detail_level": "Tiêu chuẩn"}, "label": f"Bản {i}", "topic": None,
                "user_prompt": "", "path": f"existing-{i}", "status": "ready", "error": None,
                "progress": 100, "created_at": now_iso, "started_at": now_iso,
                "updated_at": now_iso, "finished_at": now_iso,
            }
            for i in range(3)  # already at cap
        }
        course.metadata_json = json.dumps({"study_pack": {"artifacts": {"book": {"active": "existing-0", "versions": versions}}}})
        db.commit()

    generator = Generator(vector_store=None, llm=None)
    try:
        generator.prepare_artifact_version(course_id, "book", {"detail_level": "Chuyên sâu"})
        assert False, "expected VersionCapReachedError"
    except VersionCapReachedError as exc:
        assert len(exc.versions) == 3

    _, versions_after = generator.artifact_versions(course_id, "book")
    assert len(versions_after) == 3, "a rejected reservation must not have been persisted anyway"


# --- Cross-user ownership on version endpoints ---------------------------------------------


def test_version_endpoints_reject_access_from_a_different_user(client):
    """Confirmed gap from the QA sweep: no automated test previously proved user A can't
    reach user B's course versions. Code inspection showed every version endpoint routes
    through get_valid_course (404 on ownership mismatch) — this pins that behavior."""
    owner_headers = get_auth_headers(client, "owner_a@example.com")
    other_headers = get_auth_headers(client, "intruder_b@example.com")

    content = b"Artificial Intelligence course content with enough real words to pass filters."
    files = [("files", ("owned.txt", content, "text/plain"))]
    res_upload = client.post("/api/upload", headers=owner_headers, files=files)
    assert res_upload.status_code == 201, res_upload.text
    course_id = res_upload.json()["course_id"]

    # study-pack, book/slide/quiz/vid GET, and downloads must all 404 for a non-owner.
    for path in (
        f"/api/course/{course_id}/study-pack",
        f"/api/course/{course_id}/book",
        f"/api/course/{course_id}/slide",
        f"/api/course/{course_id}/quiz",
        f"/api/course/{course_id}/vid",
        f"/api/course/{course_id}/book.pdf",
    ):
        res = client.get(path, headers=other_headers)
        assert res.status_code == 404, f"{path} leaked to a non-owner: {res.status_code} {res.text}"

    # Version rename/delete must 404 too, even with a made-up version id (ownership is
    # checked before the version itself is ever looked up).
    res_rename = client.patch(
        f"/api/course/{course_id}/artifacts/book/versions/whatever",
        headers=other_headers,
        json={"label": "Hacked"},
    )
    assert res_rename.status_code == 404

    res_delete = client.delete(
        f"/api/course/{course_id}/artifacts/book/versions/whatever", headers=other_headers
    )
    assert res_delete.status_code == 404

    # And a non-owner must not even be able to trigger generation on someone else's course.
    res_generate = client.post(
        "/api/generate-book", headers=other_headers, json={"course_id": course_id}
    )
    assert res_generate.status_code == 404

    # Sanity: the actual owner is not blocked by the same checks.
    res_owner = client.get(f"/api/course/{course_id}/study-pack", headers=owner_headers)
    assert res_owner.status_code == 200


# --- Diagnostics: API key must never leak in a probe-failure detail ------------------------


def test_probe_result_redacts_the_api_key_from_failure_detail(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "sk-or-v1-super-secret-test-key")

    def _boom():
        raise RuntimeError("upstream said: sk-or-v1-super-secret-test-key is invalid")

    result = _probe_result(_boom)

    assert "sk-or-v1-super-secret-test-key" not in result["detail"]
    assert "[redacted]" in result["detail"]
