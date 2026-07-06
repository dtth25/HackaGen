from fastapi.testclient import TestClient

from backend import main
from backend.vector_db.base import VectorSearchResult


class FakeResourceGenerator:
    def generate_book(self, user_prompt: str, target_audience: str, learning_mode: str = "normal", **kwargs):
        return {
            "book": {"title": "Book", "chapters": [], "quality_report": {"score": 90}},
            "pdf_url": "/api/course/course123/book.pdf",
        }

    def generate_slides_v2(self, topic: str, num_slides: int, learning_mode: str = "normal", **kwargs):
        return {
            "slides": [{"title": "Slide 1", "content": "Content"}],
            "pptx_url": "/api/course/course123/slide.pptx",
            "quality_report": {"score": 90},
        }

    def generate_quiz_v2(self, topic: str, quantity: int, difficulty: str, learning_mode: str = "normal", **kwargs):
        return {
            "questions": [
                {
                    "question": "Question?",
                    "options": ["A", "B"],
                    "correct": 0,
                    "explanation": "Because A.",
                }
            ],
            "answer_key_url": "/api/course/course123/quiz-key.pdf",
            "quality_report": {"score": 90},
        }

    def generate_vid(
        self,
        topic: str,
        duration_minutes: int,
        learning_mode: str = "normal",
        video_renderer: str = "simple_templates",
        allow_renderer_fallback: bool = True,
        *args,
        **kwargs,
    ):
        return {"vid": {"filename": "vid.mp4", "url": "/api/course/course123/vid/file", "scenes": []}}


class FakeVectorStore:
    def get_document_chunks(self, document_id: str):
        return [
            VectorSearchResult(
                chunk_id="0",
                source_chunk_id="chunk_0",
                text="page: 1 source: secret.pdf chunk_id: 0 Nội dung quan trọng về AI và dữ liệu.",
                metadata={"page": 1, "source_chunk_id": "chunk_0", "chunk_id": 0, "source_file": "secret.pdf"},
            ),
            VectorSearchResult(
                chunk_id="1",
                source_chunk_id="chunk_1",
                text="Nội dung thứ hai về kiểm tra kiến thức.",
                metadata={"page": 2, "source_chunk_id": "chunk_1", "chunk_id": 1},
            ),
        ]


class FakeRag:
    vectorstore = FakeVectorStore()

    def get_resource_generator(self):
        return FakeResourceGenerator()


class FakeCourseManager:
    def __init__(self):
        self.registered_paths = []
        self.courses = {"course123": True}

    def get_course_status(self, course_id: str):
        return "ready"

    def get_course(self, course_id: str):
        return FakeRag()

    def list_courses(self):
        return list(self.courses.keys())

    def contains(self, course_id: str):
        return course_id in self.courses

    def add_course(self, course_id: str, source_path: str):
        self.courses[course_id] = True

    def remove_course(self, course_id: str):
        self.courses.pop(course_id, None)

    def register_course_id(self, course_id: str, source_path, user_id=None):
        self.registered_paths = source_path if isinstance(source_path, list) else [source_path]
        self.courses[course_id] = True

    def process_new_course(self, course_id: str, source_path):
        return None


def client(monkeypatch):
    fake_manager = FakeCourseManager()
    monkeypatch.setattr(main, "CourseManager", lambda: fake_manager)
    monkeypatch.setattr(main, "course_manager", fake_manager)
    main.app.dependency_overrides[main.get_current_user] = lambda: main.UserInDB(
        id="test_admin", email="admin@example.com", password_hash="pwd", role="admin", is_active=True
    )
    return TestClient(main.app)


def assert_no_public_source_metadata(payload):
    text = str(payload)
    assert "citations" not in text
    assert "chunk_id" not in text
    assert "'page'" not in text
    assert '"page"' not in text
    assert "'source'" not in text
    assert '"source"' not in text


def test_readiness_health_contract(monkeypatch):
    test_client = client(monkeypatch)
    monkeypatch.setitem(main.startup_state, "status", "ok")
    monkeypatch.setitem(main.startup_state, "ready", True)
    monkeypatch.setitem(
        main.startup_state,
        "details",
        {
            "upload_dir": True,
            "output_dir": True,
            "vector_db": True,
            "config_loaded": True,
        },
    )

    response = test_client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["ready"] is True
    assert payload["details"] == {
        "upload_dir": True,
        "output_dir": True,
        "vector_db": True,
        "config_loaded": True,
    }


def test_generation_contract_outputs(monkeypatch):
    test_client = client(monkeypatch)

    requests = [
        ("/api/generate-book", {"course_id": "course123"}),
        ("/api/generate-slide", {"course_id": "course123", "topic": "topic"}),
        ("/api/generate-quiz", {"course_id": "course123", "topic": "topic"}),
        ("/api/generate-vid", {"course_id": "course123", "topic": "topic"}),
    ]

    for path, body in requests:
        response = test_client.post(path, json=body)
        assert response.status_code == 200
        assert_no_public_source_metadata(response.json())

        if path == "/api/generate-slide":
            assert response.json()["pptx_url"].endswith("/slide.pptx")
            assert "json_url" not in response.json()
            assert "pdf_url" not in response.json()
        if path == "/api/generate-quiz":
            assert response.json()["answer_key_url"].endswith("/quiz-key.pdf")
            assert "json_url" not in response.json()

    sp_res = test_client.get("/api/course/course123/study-pack")
    assert sp_res.status_code == 200
    sp_data = sp_res.json()
    assert "study_pack" in sp_data
    assert "readiness" in sp_data["study_pack"]
    assert "quality_scores" in sp_data["study_pack"]


def test_removed_generation_routes_are_not_registered(monkeypatch):
    test_client = client(monkeypatch)

    removed_routes = [
        "/api/chat",
        "/api/custom-prompt",
        "/api/generate-course",
        "/api/generate-summary",
        "/api/generate-flashcards",
        "/api/generate-mindmap",
    ]

    for path in removed_routes:
        response = test_client.post(path, json={"course_id": "course123"})
        assert response.status_code == 404


def test_deprecated_json_and_pdf_downloads_are_not_public(monkeypatch):
    test_client = client(monkeypatch)

    deprecated_downloads = [
        "/api/course/course123/slide.json",
        "/api/course/course123/slide.pdf",
        "/api/course/course123/quiz.json",
        "/api/course/course123/quiz.pdf",
    ]

    for path in deprecated_downloads:
        response = test_client.get(path)
        assert response.status_code == 404


def test_upload_rejects_unsupported_extension(monkeypatch):
    test_client = client(monkeypatch)

    response = test_client.post(
        "/api/upload",
        files={"file": ("notes.exe", b"bad", "application/octet-stream")},
    )

    assert response.status_code == 400


def test_upload_accepts_multiple_documents(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "UPLOAD_DIR", str(tmp_path))
    test_client = client(monkeypatch)

    response = test_client.post(
        "/api/upload",
        files=[
            ("files", ("a.txt", b"hello", "text/plain")),
            ("files", ("b.txt", b"world", "text/plain")),
        ],
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["file_count"] == 2
    assert payload["filenames"] == ["a.txt", "b.txt"]
    assert payload["status"] == "processing"


def test_delete_document_endpoint(monkeypatch):
    test_client = client(monkeypatch)
    mgr = main._get_course_manager()
    mgr.add_course("test_doc_to_delete", "a.txt")

    response = test_client.delete("/api/documents/test_doc_to_delete")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    assert not mgr.contains("test_doc_to_delete")


def test_delete_document_unprefixed_alias(monkeypatch):
    test_client = client(monkeypatch)
    mgr = main._get_course_manager()
    mgr.add_course("test_doc_to_delete_alias", "a.txt")

    response = test_client.delete("/documents/test_doc_to_delete_alias")

    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    assert not mgr.contains("test_doc_to_delete_alias")


def test_document_sources_hide_internal_ids_by_default(monkeypatch):
    test_client = client(monkeypatch)

    response = test_client.get("/api/documents/course123/sources?ids=chunk_0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_id"] == "course123"
    assert payload["matched_source_chunks"] == 1
    assert payload["sources"][0]["page"] == 1
    assert "source_chunk_id" not in payload["sources"][0]
    assert "chunk_id" not in payload["sources"][0]["excerpt"]
    assert "source:" not in payload["sources"][0]["excerpt"].lower()


def test_document_sources_can_show_internal_ids_in_developer_mode(monkeypatch):
    test_client = client(monkeypatch)
    main.app.dependency_overrides[main.get_current_user] = lambda: main.UserInDB(
        id="admin_user", email="admin@example.com", password_hash="pwd", role="admin", is_active=True
    )

    response = test_client.get("/api/documents/course123/sources?ids=chunk_1&developer=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["matched_source_chunks"] == 1
    assert payload["sources"][0]["source_chunk_id"] == "chunk_1"
