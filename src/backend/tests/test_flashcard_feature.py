"""
Test suite for the dedicated Flashcard generator: schema normalization, quality gate, and endpoints.
"""
from langchain_core.documents import Document
from fastapi.testclient import TestClient

from backend import main
from backend.services import resource_gen
from backend.services.resource_gen import ResourceGenerator


def _generator() -> ResourceGenerator:
    gen = object.__new__(ResourceGenerator)
    gen.course_id = "flashcardtest"
    gen.vectorstore = None
    return gen


def _docs():
    return [
        Document(
            page_content="Perceptron là đơn vị tính toán cơ bản của mạng nơ-ron, nhận đầu vào và trọng số.",
            metadata={"chunk_id": "chunk_1"},
        ),
        Document(
            page_content="ReLU trả về max(0, x) và giúp tránh vanishing gradient trong mạng sâu.",
            metadata={"chunk_id": "chunk_2"},
        ),
    ]


def test_normalize_flashcards_full_schema():
    gen = _generator()
    raw = {
        "deck_title": "Flashcards: Mạng nơ-ron",
        "cards": [
            {
                "id": "c1",
                "front": "Perceptron là gì?",
                "back": "Đơn vị tính toán cơ bản của mạng nơ-ron, nhận đầu vào nhân trọng số rồi cộng bias.",
                "card_type": "definition",
                "difficulty": "easy",
                "concept_tags": ["perceptron"],
                "source_chunk_ids": ["chunk_1"],
            },
            {
                "id": "c2",
                "front": "ReLU(x) khi x = -3 bằng bao nhiêu?",
                "back": "Bằng 0, vì ReLU trả về max(0, x) và -3 nhỏ hơn 0.",
                "card_type": "formula",
                "difficulty": "medium",
                "concept_tags": ["relu"],
                "source_chunk_ids": ["chunk_2"],
            },
        ],
    }
    normalized = gen._normalize_flashcards(raw, quantity=10, docs=_docs())
    assert len(normalized) == 2
    c1 = normalized[0]
    assert c1["id"] == "c1"
    assert c1["card_type"] == "definition"
    assert c1["concept_tags"] == ["perceptron"]
    assert c1["source_chunk_ids"] == ["chunk_1"]
    c2 = normalized[1]
    assert c2["card_type"] == "formula"


def test_normalize_flashcards_rejects_duplicates_and_missing_back():
    gen = _generator()
    raw = {
        "cards": [
            {"front": "AI là gì?", "back": "Trí tuệ nhân tạo, mô phỏng khả năng suy luận của con người."},
            {"front": "AI  là gì???", "back": "Một câu trả lời gần giống hệt câu trên."},
            {"front": "Không có mặt sau", "back": ""},
            {"front": "Machine learning là gì?", "back": "Máy học, tự động rút ra quy luật từ dữ liệu."},
        ]
    }
    normalized = gen._normalize_flashcards(raw, quantity=10, docs=_docs())
    assert len(normalized) == 2
    fronts = {c["front"] for c in normalized}
    assert "AI là gì?" in fronts
    assert "Machine learning là gì?" in fronts


def test_build_fallback_flashcards_grounded_and_deduped():
    gen = _generator()
    cards = gen._build_fallback_flashcards(_docs(), quantity=5)
    assert len(cards) >= 1
    fronts = [c["front"] for c in cards]
    assert len(fronts) == len(set(fronts))
    for c in cards:
        assert c["source_chunk_ids"]
        assert c["card_type"] == "quick_recall"


def test_evaluate_flashcard_quality_gate_good_vs_bad():
    gen = _generator()

    good_deck = {
        "cards": [
            {
                "front": "Perceptron là gì?",
                "back": "Đơn vị tính toán cơ bản của mạng nơ-ron, nhận đầu vào nhân trọng số rồi cộng bias.",
                "source_chunk_ids": ["chunk_1"],
            },
            {
                "front": "ReLU dùng để làm gì?",
                "back": "Tạo tính phi tuyến và giúp tránh vanishing gradient trong mạng sâu.",
                "source_chunk_ids": ["chunk_2"],
            },
        ]
    }
    report = gen._evaluate_quality_gate(good_deck, "flashcards")
    assert report["score"] >= 80
    assert report["is_university_ready"] is True
    assert len(report["warnings"]) == 0

    bad_deck = {
        "cards": [
            {"front": "Thẻ mẫu", "back": "Thẻ mẫu", "source_chunk_ids": []},
            {"front": "Thẻ mẫu", "back": "Thẻ mẫu", "source_chunk_ids": []},
        ]
    }
    bad_report = gen._evaluate_quality_gate(bad_deck, "flashcards")
    assert bad_report["score"] < report["score"]
    assert bad_report["is_university_ready"] is False
    assert len(bad_report["warnings"]) > 0


def test_flashcard_endpoints(monkeypatch, tmp_path):
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
            "mindmap": str(tmp_path / f"mindmap_{course_id}.json"),
            "flashcards": str(tmp_path / f"flashcards_{course_id}.json"),
        }

    monkeypatch.setattr(main, "get_course_path", fake_path)
    monkeypatch.setattr("backend.services.resource_gen.get_course_path", fake_path)
    monkeypatch.setattr(resource_gen, "get_llm", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("no llm in tests")))

    client = TestClient(main.app)
    res = client.get("/api/course/flashcardtest/flashcards")
    assert res.status_code == 200
    data = res.json()
    assert data["deck_title"]
    assert len(data["cards"]) >= 1
    assert data["quality_report"]["score"] >= 0
    for c in data["cards"]:
        assert "id" in c
        assert "card_type" in c
        assert "concept_tags" in c
        assert "source_chunk_ids" in c

    res_regen = client.post("/api/course/flashcardtest/flashcards/regenerate")
    assert res_regen.status_code == 200
    regen_data = res_regen.json()
    assert regen_data["deck_title"]

    main.app.dependency_overrides.clear()
