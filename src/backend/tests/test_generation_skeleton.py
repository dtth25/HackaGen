"""Automated tests for Generation Service Skeleton (Checkpoint 6)."""

from app.services.generator import MAX_REGENERATIONS


def get_auth_headers_and_course(client, email: str = "gen_user@example.com"):
    """Register/login user and create an uploaded course."""
    reg_data = {"email": email, "password": "password123", "full_name": "Gen User"}
    res = client.post("/api/auth/register", json=reg_data)
    if res.status_code == 201:
        res = client.post("/api/auth/verify-email", json={"email": email, "code": "000000"})
    else:
        res = client.post(
            "/api/auth/login", json={"email": email, "password": "password123"}
        )
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload a dummy file to create a course
    files = [("files", ("study_doc.pdf", b"dummy pdf content", "application/pdf"))]
    res_upload = client.post("/api/upload", headers=headers, files=files)
    assert res_upload.status_code == 201
    course_id = res_upload.json()["course_id"]

    return headers, course_id


def test_get_study_pack_skeleton(client):
    headers, course_id = get_auth_headers_and_course(client, "study_pack@example.com")

    # Test both /api/course/{id}/study-pack and /api/courses/{id}/study-pack
    for prefix in ["/api/course", "/api/courses"]:
        res = client.get(f"{prefix}/{course_id}/study-pack", headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["course_id"] == course_id

        # Verify study_pack structure
        sp = data["study_pack"]
        assert sp["title"] == "Course Title"
        assert sp["book"] is None
        assert sp["slides"] is None
        assert sp["quiz"] == []
        assert sp["vid"] is None
        assert sp["readiness"]["study_guide_pdf"] is False
        assert sp["quality_scores"]["study_guide_pdf"] == 0
        assert sp["grounding"]["num_chunks"] == 0

        # Verify stats object for frontend compatibility
        assert data["stats"]["course_id"] == course_id


def test_generate_endpoints_queued(client):
    headers, course_id = get_auth_headers_and_course(client, "generate@example.com")

    endpoints = [
        "/api/generate-book",
        "/api/generate-slide",
        "/api/generate-quiz",
        "/api/generate-vid",
    ]

    for ep in endpoints:
        # Test with query parameter
        res_query = client.post(f"{ep}?course_id={course_id}", headers=headers)
        assert res_query.status_code == 200, res_query.text
        data_q = res_query.json()
        assert data_q["course_id"] == course_id
        assert data_q["status"] == "queued"
        assert data_q["message"] == "Generation started..."
        # Vid renders real TTS+ffmpeg media, so it advertises a longer estimate than the
        # single-LLM-call Book/Slide/Quiz artifacts.
        expected_time = "3-5 minutes" if ep == "/api/generate-vid" else "2 minutes"
        assert data_q["estimated_time"] == expected_time

        # Test with JSON body
        res_body = client.post(ep, headers=headers, json={"course_id": course_id})
        assert res_body.status_code == 200, res_body.text
        data_b = res_body.json()
        assert data_b["course_id"] == course_id
        assert data_b["status"] == "queued"


def test_artifact_retrieval_null_and_empty(client):
    headers, course_id = get_auth_headers_and_course(client, "retrieve@example.com")

    empty_envelope = {
        "status": "empty", "error": None, "progress": None, "data": None,
        "regen_used": 0, "regen_max": MAX_REGENERATIONS,
        "version_id": None, "active_version": None, "versions": [],
    }

    # book -> status envelope with empty status and null data
    res_book = client.get(f"/api/course/{course_id}/book", headers=headers)
    assert res_book.status_code == 200, res_book.text
    assert res_book.json() == empty_envelope

    # slide -> status envelope with empty status and null data
    res_slide = client.get(f"/api/course/{course_id}/slide", headers=headers)
    assert res_slide.status_code == 200, res_slide.text
    assert res_slide.json() == empty_envelope

    # vid -> status envelope with empty status and null data
    res_vid = client.get(f"/api/course/{course_id}/vid", headers=headers)
    assert res_vid.status_code == 200, res_vid.text
    assert res_vid.json() == empty_envelope

    # quiz -> status envelope with empty status and null data
    res_quiz = client.get(f"/api/course/{course_id}/quiz", headers=headers)
    assert res_quiz.status_code == 200, res_quiz.text
    assert res_quiz.json() == empty_envelope


def test_download_endpoints_404_vietnamese(client):
    headers, course_id = get_auth_headers_and_course(client, "download@example.com")

    downloads = [
        ("/book.pdf", "Chưa có file PDF cho tài liệu này."),
        ("/slide.pptx", "Chưa có file bài giảng PPTX cho tài liệu này."),
        ("/quiz-key.pdf", "Chưa có file đáp án trắc nghiệm PDF cho tài liệu này."),
        ("/vid.mp4", "Chưa có file video cho tài liệu này."),
        ("/vid/file", "Chưa có bản lời thoại (transcript) cho video này."),
    ]

    for path_suffix, expected_msg in downloads:
        res = client.get(f"/api/course/{course_id}{path_suffix}", headers=headers)
        assert res.status_code == 404, res.text
        data = res.json()
        assert data["detail"] == expected_msg


def test_generation_unauthorized_course(client):
    headers1, course_id1 = get_auth_headers_and_course(client, "owner@example.com")
    headers2, _ = get_auth_headers_and_course(client, "attacker@example.com")

    # Attacker tries to access owner's study pack
    res_sp = client.get(f"/api/course/{course_id1}/study-pack", headers=headers2)
    assert res_sp.status_code == 404
    assert res_sp.json()["detail"] == "Khóa học không tồn tại."

    # Attacker tries to generate book for owner's course
    res_gen = client.post(
        f"/api/generate-book?course_id={course_id1}", headers=headers2
    )
    assert res_gen.status_code == 404
    assert res_gen.json()["detail"] == "Khóa học không tồn tại."

    # Attacker tries to retrieve owner's book
    res_ret = client.get(f"/api/course/{course_id1}/book", headers=headers2)
    assert res_ret.status_code == 404

    # Attacker tries to download owner's book.pdf
    res_dl = client.get(f"/api/course/{course_id1}/book.pdf", headers=headers2)
    assert res_dl.status_code == 404
    assert res_dl.json()["detail"] == "Khóa học không tồn tại."
