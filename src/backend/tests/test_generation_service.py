"""Automated tests for Generation Service and AI API completion (Checkpoint 8 / Prompt 5)."""

import os
from app.models.course import Course
from app.services.database import SessionLocal
from app.services.generator import Generator
from app.services.llm import LLMService
from app.services.vector_store import Document, get_vector_store


def test_llm_service_and_prompts():
    """Test LLMService initialization, prompt loading, and structured output generation."""
    llm = LLMService(model="gemini-2.5-flash")
    assert llm.prompts_dir is not None
    assert os.path.exists(os.path.join(llm.prompts_dir, "book.txt"))
    assert os.path.exists(os.path.join(llm.prompts_dir, "slides.txt"))
    assert os.path.exists(os.path.join(llm.prompts_dir, "quiz.txt"))
    assert os.path.exists(os.path.join(llm.prompts_dir, "vid.txt"))

    # Test generation methods
    context = "[Chunk ID: chunk_1] (Tài liệu: doc.pdf, Trang: 1): Trí tuệ nhân tạo là lĩnh vực khoa học máy tính."
    valid_cids = ["chunk_1", "chunk_2"]

    book = llm.generate_book(context=context, target_audience="Students", valid_chunk_ids=valid_cids)
    assert book.title != ""
    assert len(book.chapters) > 0
    assert len(book.chapters[0].source_chunk_ids) > 0

    slides = llm.generate_slides(context=context, topic="AI", num_slides=3, valid_chunk_ids=valid_cids)
    assert slides.title != ""
    assert len(slides.slides) > 0
    assert len(slides.slides[0].source_chunk_ids) > 0

    quiz = llm.generate_quiz(context=context, topic="AI", quantity=3, valid_chunk_ids=valid_cids)
    assert quiz.title != ""
    assert len(quiz.questions) > 0
    assert len(quiz.questions[0].options) == 4
    assert quiz.questions[0].correct_answer in ["A", "B", "C", "D"]
    assert len(quiz.questions[0].source_chunk_ids) > 0

    vid = llm.generate_vid(context=context, topic="AI", duration=180, valid_chunk_ids=valid_cids)
    assert vid.title != ""
    assert len(vid.scenes) > 0
    assert len(vid.scenes[0].source_chunk_ids) > 0


def test_generator_all_artifacts_and_validation(client):
    """Test Generator service RAG retrieval, scoring > 70, filesystem saving, and PDF/PPTX generation."""
    db = SessionLocal()
    try:
        # Create a dummy course
        course_id = "test_gen_srv"
        course = Course(
            id=course_id,
            user_id="user_gen_srv",
            filenames=["ai_doc.pdf"],
            status="ready",
            stage="completed",
            progress=100,
            chunk_count=2,
            embedding_status="completed",
            quality_score=0,
        )
        db.add(course)
        db.commit()
    finally:
        db.close()

    vs = get_vector_store()
    vs.add_documents(
        [
            Document(content="Trí tuệ nhân tạo là mô phỏng trí tuệ con người.", metadata={"chunk_id": "chunk_1", "source_file": "ai_doc.pdf", "page": 1}),
            Document(content="Học sâu (Deep Learning) là tập con của học máy.", metadata={"chunk_id": "chunk_2", "source_file": "ai_doc.pdf", "page": 2}),
        ],
        course_id=course_id,
    )

    llm = LLMService()
    gen = Generator(vs, llm)

    # Generate all 4 artifacts
    book_out = gen.generate_book(course_id=course_id, target_audience="Students")
    slides_out = gen.generate_slides(course_id=course_id, topic="AI", num_slides=3)
    quiz_out = gen.generate_quiz(course_id=course_id, topic="AI", quantity=3)
    vid_out = gen.generate_vid(course_id=course_id, topic="AI", duration=180)

    assert book_out.title != ""
    assert slides_out.title != ""
    assert quiz_out.title != ""
    assert vid_out.title != ""

    # Verify filesystem storage
    art_dir = gen._get_artifact_dir(course_id)
    for fname in ["book.json", "book.pdf", "slides.json", "slide.pptx", "quiz.json", "quiz-key.pdf", "vid.json", "vid_script.txt"]:
        fpath = os.path.join(art_dir, fname)
        assert os.path.exists(fpath), f"Expected file {fname} to exist at {fpath}"
        assert os.path.getsize(fpath) > 0, f"File {fname} is empty"

    # Verify quality score > 70 and readiness flags in DB
    db = SessionLocal()
    try:
        import json
        course_upd = db.query(Course).filter(Course.id == course_id).first()
        assert course_upd.quality_score > 70, f"Expected quality score > 70, got {course_upd.quality_score}"
        meta_dict = json.loads(course_upd.metadata_json) if isinstance(course_upd.metadata_json, str) else course_upd.metadata_json
        sp_meta = meta_dict["study_pack"]
        assert sp_meta["readiness"]["study_guide_pdf"] is True
        assert sp_meta["readiness"]["mindmap"] is True
        assert sp_meta["readiness"]["quiz"] is True
        assert sp_meta["readiness"]["summary"] is True
        assert sp_meta["readiness"]["flashcards"] is True
    finally:
        db.close()

    # Clean up Chroma
    vs.delete_course(course_id)


def test_generation_api_endpoints_complete(client):
    """Test full generation API flow: trigger background generation, verify study pack, retrieval, and downloads."""
    # Register & login
    reg_data = {"email": "gen_api@example.com", "password": "password123", "full_name": "Gen API User"}
    res = client.post("/api/auth/register", json=reg_data)
    if res.status_code != 201:
        res = client.post("/api/auth/login", json={"email": "gen_api@example.com", "password": "password123"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload a dummy file to create a course
    files = [("files", ("test_gen_api.pdf", b"Dummy AI doc content for API testing", "application/pdf"))]
    res_upload = client.post("/api/upload", headers=headers, files=files)
    assert res_upload.status_code == 201
    course_id = res_upload.json()["course_id"]

    # Trigger generation endpoints
    for ep in ["/api/generate-book", "/api/generate-slide", "/api/generate-quiz", "/api/generate-vid"]:
        res_gen = client.post(f"{ep}?course_id={course_id}", headers=headers)
        assert res_gen.status_code == 200, res_gen.text
        assert res_gen.json()["status"] == "queued"

    # Verify study pack stats and readiness (BackgroundTasks executed synchronously by TestClient)
    res_sp = client.get(f"/api/course/{course_id}/study-pack", headers=headers)
    assert res_sp.status_code == 200, res_sp.text
    sp_data = res_sp.json()
    assert sp_data["stats"]["has_book"] is True
    assert sp_data["stats"]["has_book_pdf"] is True
    assert sp_data["stats"]["has_slide"] is True
    assert sp_data["stats"]["has_slide_pptx"] is True
    assert sp_data["stats"]["has_quiz"] is True
    assert sp_data["stats"]["has_quiz_answer_key"] is True
    assert sp_data["stats"]["has_vid"] is True
    assert sp_data["stats"]["quality_score"] > 70

    # Verify retrieval endpoints return generated JSON
    res_book = client.get(f"/api/course/{course_id}/book", headers=headers)
    assert res_book.status_code == 200
    assert res_book.json()["title"] != ""
    assert len(res_book.json()["chapters"]) > 0

    res_slide = client.get(f"/api/course/{course_id}/slide", headers=headers)
    assert res_slide.status_code == 200
    assert len(res_slide.json()["slides"]) > 0

    res_quiz = client.get(f"/api/course/{course_id}/quiz", headers=headers)
    assert res_quiz.status_code == 200
    assert len(res_quiz.json()) > 0  # quiz endpoint returns list of questions

    res_vid = client.get(f"/api/course/{course_id}/vid", headers=headers)
    assert res_vid.status_code == 200
    assert len(res_vid.json()["scenes"]) > 0

    # Verify download endpoints return 200 OK with file content
    for file_ep, content_type in [
        ("/book.pdf", "application/pdf"),
        ("/slide.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        ("/quiz-key.pdf", "application/pdf"),
        ("/vid/file", "text/plain"),
    ]:
        res_dl = client.get(f"/api/course/{course_id}{file_ep}", headers=headers)
        assert res_dl.status_code == 200, f"Failed on {file_ep}: {res_dl.text}"
        assert len(res_dl.content) > 0
        assert content_type in res_dl.headers.get("content-type", "")
