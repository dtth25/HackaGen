"""
Test suite for the upgraded Quiz feature: schema normalization, quality gate, and endpoints.
"""
from langchain_core.documents import Document
from fastapi.testclient import TestClient

from backend import main
from backend.services import resource_gen
from backend.services.resource_gen import ResourceGenerator


def _generator() -> ResourceGenerator:
    gen = object.__new__(ResourceGenerator)
    gen.course_id = "quiztest"
    gen.vectorstore = None
    return gen


def _docs():
    return [
        Document(
            page_content="Perceptron là đơn vị tính toán cơ bản của mạng nơ-ron, nhận đầu vào và trọng số.",
            metadata={"chunk_id": "chunk_1"},
        ),
        Document(
            page_content="Backpropagation dùng chain rule để lan truyền ngược sai số qua các lớp.",
            metadata={"chunk_id": "chunk_2"},
        ),
    ]


def test_normalize_quiz_full_schema():
    gen = _generator()
    raw = {
        "quiz_title": "Quiz: Mạng nơ-ron",
        "questions": [
            {
                "id": "q1",
                "type": "mcq",
                "question": "Perceptron nhận đầu vào và làm gì tiếp theo?",
                "options": ["Nhân trọng số và cộng bias", "Xóa dữ liệu", "Không làm gì", "Ngắt kết nối"],
                "correct_answer": "Nhân trọng số và cộng bias",
                "explanation": "Theo tài liệu, perceptron nhân từng đầu vào với trọng số tương ứng rồi cộng bias trước khi qua hàm kích hoạt.",
                "why_wrong_options_are_wrong": [
                    "Xóa dữ liệu không phải là phép toán của perceptron.",
                    "Perceptron luôn thực hiện phép tính tuyến tính, không phải không làm gì.",
                    "Ngắt kết nối không liên quan tới cơ chế tính toán của perceptron.",
                ],
                "difficulty": "easy",
                "concept_tags": ["perceptron"],
                "source_chunk_ids": ["chunk_1"],
            },
            {
                "id": "q2",
                "type": "true_false",
                "question": "Backpropagation sử dụng chain rule để tính gradient.",
                "correct_answer": "Đúng",
                "explanation": "Tài liệu nêu rõ backpropagation áp dụng chain rule để lan truyền ngược sai số.",
                "difficulty": "medium",
                "concept_tags": ["backpropagation"],
                "source_chunk_ids": ["chunk_2"],
            },
            {
                "id": "q3",
                "type": "short_answer",
                "question": "Giải thích ngắn gọn vai trò của chain rule trong backpropagation.",
                "correct_answer": "Chain rule cho phép tính đạo hàm của hàm mất mát theo từng trọng số qua các lớp.",
                "explanation": "Chain rule là nền tảng toán học giúp lan truyền gradient ngược từ lớp đầu ra về lớp đầu vào.",
                "difficulty": "hard",
                "concept_tags": ["backpropagation", "chain rule"],
                "source_chunk_ids": ["chunk_2"],
            },
        ],
    }

    normalized = gen._normalize_quiz(raw, quantity=10, docs=_docs(), difficulty="medium")
    assert len(normalized) == 3

    mcq = normalized[0]
    assert mcq["id"] == "q1"
    assert mcq["type"] == "mcq"
    assert mcq["options"] == raw["questions"][0]["options"]
    assert mcq["correct"] == 0
    assert mcq["correct_answer"] == "Nhân trọng số và cộng bias"
    assert len(mcq["why_wrong_options_are_wrong"]) == 3
    assert mcq["concept_tags"] == ["perceptron"]
    assert mcq["source_chunk_ids"] == ["chunk_1"]

    tf = normalized[1]
    assert tf["type"] == "true_false"
    assert tf["options"] == ["Đúng", "Sai"]
    assert tf["correct_answer"] == "Đúng"
    assert tf["correct"] == 0

    sa = normalized[2]
    assert sa["type"] == "short_answer"
    assert sa["options"] == []
    assert "chain rule" in sa["correct_answer"].lower()


def test_normalize_quiz_rejects_duplicate_questions():
    gen = _generator()
    raw = {
        "questions": [
            {"question": "AI là gì?", "options": ["A", "B"], "correct": 0, "explanation": "Vì đây là A theo tài liệu."},
            {"question": "AI  là gì???", "options": ["A", "B"], "correct": 0, "explanation": "Câu hỏi trùng lặp về AI."},
            {"question": "Machine learning là gì?", "options": ["C", "D"], "correct": 0, "explanation": "Vì đây là C theo tài liệu."},
        ]
    }
    normalized = gen._normalize_quiz(raw, quantity=10, docs=_docs(), difficulty="medium")
    assert len(normalized) == 2
    questions_text = {q["question"] for q in normalized}
    assert "AI là gì?" in questions_text
    assert "Machine learning là gì?" in questions_text


def test_build_fallback_quiz_is_grounded_and_deduped():
    gen = _generator()
    questions = gen._build_fallback_quiz(_docs(), quantity=5, difficulty="medium")
    assert len(questions) >= 1
    texts = [q["question"] for q in questions]
    assert len(texts) == len(set(texts))
    for q in questions:
        assert q["source_chunk_ids"]
        assert q["type"] == "mcq"
        assert len(q["why_wrong_options_are_wrong"]) == 3


def test_evaluate_quiz_quality_gate_good_vs_bad():
    gen = _generator()

    good_quiz = {
        "questions": [
            {
                "question": "Perceptron nhận đầu vào và làm gì?",
                "options": ["Nhân trọng số và cộng bias", "Không làm gì"],
                "correct": 0,
                "explanation": "Theo tài liệu, perceptron nhân từng đầu vào với trọng số rồi cộng bias.",
                "why_wrong_options_are_wrong": ["Không làm gì thì không phải là một phép tính hợp lệ."],
                "source_chunk_ids": ["chunk_1"],
            },
            {
                "question": "Backpropagation dùng nguyên lý toán học nào?",
                "options": ["Chain rule", "Định lý Pytago"],
                "correct": 0,
                "explanation": "Tài liệu nêu rõ backpropagation áp dụng chain rule để lan truyền ngược sai số.",
                "why_wrong_options_are_wrong": ["Định lý Pytago không liên quan tới đạo hàm hàm hợp."],
                "source_chunk_ids": ["chunk_2"],
            },
        ]
    }
    report = gen._evaluate_quality_gate(good_quiz, "quiz")
    assert report["score"] >= 80
    assert report["is_university_ready"] is True
    assert len(report["warnings"]) == 0

    bad_quiz = {
        "questions": [
            {"question": "Câu hỏi mẫu?", "options": ["A", "B"], "correct": 0, "explanation": "Đúng.", "source_chunk_ids": []},
            {"question": "Câu hỏi mẫu?", "options": ["A", "B"], "correct": 0, "explanation": "Đúng.", "source_chunk_ids": []},
        ]
    }
    bad_report = gen._evaluate_quality_gate(bad_quiz, "quiz")
    assert bad_report["score"] < report["score"]
    assert bad_report["is_university_ready"] is False
    assert len(bad_report["warnings"]) > 0


def test_quiz_endpoints(monkeypatch, tmp_path):
    class FakeRetriever:
        def invoke(self, query):
            return _docs()

    class FakeVectorStore:
        def as_retriever(self, **kwargs):
            return FakeRetriever()

    class FakeRag:
        def __init__(self, course_id):
            self.course_id = course_id
            self.vectorstore = FakeVectorStore()

        def get_resource_generator(self):
            return ResourceGenerator(self)

    class FakeManager:
        def contains(self, course_id):
            return True

        def get_course_status(self, course_id):
            return "ready"

        def get_course(self, course_id):
            return FakeRag(course_id)

    monkeypatch.setattr(main, "course_manager", FakeManager())
    main.app.dependency_overrides[main.get_current_user] = lambda: main.UserInDB(
        id="test_admin", email="admin@example.com", password_hash="pwd", role="admin", is_active=True
    )

    def fake_path(course_id):
        return {
            "meta": str(tmp_path / f"meta_{course_id}.json"),
            "book": str(tmp_path / f"book_{course_id}.json"),
            "questions": str(tmp_path / f"questions_{course_id}.json"),
            "questions_pdf": str(tmp_path / f"questions_{course_id}.pdf"),
            "questions_key_pdf": str(tmp_path / f"key_{course_id}.pdf"),
            "mindmap": str(tmp_path / f"mindmap_{course_id}.json"),
            "flashcards": str(tmp_path / f"flashcards_{course_id}.json"),
        }

    monkeypatch.setattr(main, "get_course_path", fake_path)
    monkeypatch.setattr("backend.services.resource_gen.get_course_path", fake_path)
    # Force the LLM path to fail deterministically so generation exercises the grounded
    # fallback quiz builder instead of depending on network access in tests.
    monkeypatch.setattr(resource_gen, "get_llm", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("no llm in tests")))

    client = TestClient(main.app)
    res = client.post("/api/generate-quiz", json={"course_id": "quiztest", "topic": "tổng quan", "quantity": 4, "difficulty": "medium"})
    assert res.status_code == 200
    data = res.json()
    assert data["quiz_title"]
    assert data["total_questions"] >= 1
    assert isinstance(data["difficulty_mix"], dict)
    assert data["quality_report"]["score"] >= 0
    assert data["answer_key_url"].endswith("/quiz-key.pdf")
    for q in data["questions"]:
        assert "id" in q
        assert "type" in q
        assert "correct_answer" in q
        assert "concept_tags" in q
        assert "source_chunk_ids" in q

    res_get = client.get("/api/course/quiztest/quiz")
    assert res_get.status_code == 200
    get_data = res_get.json()
    assert get_data["total_questions"] == data["total_questions"]
    assert get_data["quiz_title"]

    main.app.dependency_overrides.clear()
