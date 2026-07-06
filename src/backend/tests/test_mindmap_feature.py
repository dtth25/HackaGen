"""
Test suite for interactive 3-level Mindmap feature: book plan normalization, quality gate, and endpoints.
"""
import json
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend import main
from backend.services.resource_gen import ResourceGenerator


@pytest.fixture
def sample_book():
    return {
        "title": "Nhập môn Mạng nơ-ron và Học sâu",
        "chapters": [
            {
                "chapter_id": "ch_1",
                "title": "Chương 1: Nền tảng Mạng nơ-ron",
                "summary": "Giới thiệu về perceptron và hàm kích hoạt.",
                "importance": "high",
                "source_chunk_ids": ["chunk_1", "chunk_2"],
                "lessons": [
                    {
                        "lesson_id": "les_1_1",
                        "title": "Mô hình Perceptron",
                        "content": "Perceptron là đơn vị tính toán cơ bản.",
                        "short_name": "Perceptron",
                        "keywords": ["perceptron", "weights"],
                        "importance": "high",
                        "source_chunk_ids": ["chunk_1"],
                        "quick_check": [{"answer": "Đơn vị tính toán tuyến tính kết hợp hàm ngưỡng."}],
                        "flashcards": [{"front": "Perceptron là gì?", "back": "Mô hình nơ-ron nhân tạo đơn giản nhất."}]
                    },
                    {
                        "lesson_id": "les_1_2",
                        "title": "Hàm kích hoạt (Activation Functions)",
                        "content": "Sigmoid, ReLU và Tanh.",
                        "short_name": "Activation",
                        "keywords": ["ReLU", "Sigmoid"],
                        "importance": "medium",
                        "source_chunk_ids": ["chunk_2"],
                    }
                ]
            }
        ]
    }


def test_build_mindmap_from_book(sample_book):
    rag = MagicMock()
    rag.course_id = "test_course_123"
    rag.vectorstore = MagicMock()
    gen = ResourceGenerator(rag)
    mindmap = gen.build_mindmap_from_book(sample_book)

    assert mindmap["title"] == "Nhập môn Mạng nơ-ron và Học sâu"
    assert "root" in mindmap
    assert mindmap["root"]["id"] == "root"
    assert mindmap["root"]["title"] == "Nhập môn Mạng nơ-ron và Học sâu"
    assert mindmap["root"]["type"] == "root"
    assert mindmap["root"]["importance"] == "high"

    # Check 3-level tree structure via ID references
    root_children_ids = mindmap["root"]["children"]
    assert len(root_children_ids) == 1
    ch_id = root_children_ids[0]
    ch_node = next(n for n in mindmap["nodes"] if n["id"] == ch_id)
    assert ch_node["title"] == "Chương 1: Nền tảng Mạng nơ-ron"
    assert ch_node["type"] == "chapter"
    assert len(ch_node["children"]) == 2

    les_id = ch_node["children"][0]
    les_node = next(n for n in mindmap["nodes"] if n["id"] == les_id)
    assert les_node["title"] == "Mô hình Perceptron"
    assert les_node["type"] == "lesson"
    assert les_node["summary"] == "Perceptron là đơn vị tính toán cơ bản."

    # Check flat nodes list
    assert "nodes" in mindmap
    assert len(mindmap["nodes"]) == 3  # 1 chapter + 2 lessons
    assert "edges" in mindmap
    assert len(mindmap["edges"]) == 3  # root->ch1, ch1->les1, ch1->les2
    assert "quality_report" in mindmap
    assert mindmap["quality_report"]["is_usable"] is True
    assert mindmap["quality_report"]["score"] >= 80


def test_evaluate_mindmap_quality_gate():
    rag = MagicMock()
    rag.course_id = "test_course_gate"
    rag.vectorstore = MagicMock()
    gen = ResourceGenerator(rag)
    
    # Good mindmap
    good_mm = {
        "title": "Good Topic",
        "root": {"id": "root", "title": "Good Topic", "children": []},
        "nodes": [
            {"id": "c1", "title": "Chapter 1", "summary": "Detailed summary of chapter 1.", "source_chunk_ids": ["chk1"]},
            {"id": "l1", "title": "Lesson 1", "summary": "Core concept explanation.", "source_chunk_ids": ["chk1"]}
        ],
        "edges": [{"from": "root", "to": "c1"}, {"from": "c1", "to": "l1"}]
    }
    report = gen._evaluate_mindmap_quality_gate(good_mm)
    assert report["score"] >= 80
    assert report["is_usable"] is True
    assert len(report["warnings"]) == 0

    # Bad mindmap with filler and dot leaders
    bad_mm = {
        "title": "Bad Topic",
        "root": {"id": "root", "title": "Bad Topic", "children": []},
        "nodes": [
            {"id": "c1", "title": "Contents...", "summary": "Ý chính.....", "source_chunk_ids": []},
            {"id": "l1", "title": "...", "summary": "dot leader test...", "source_chunk_ids": []}
        ],
        "edges": []
    }
    report_bad = gen._evaluate_mindmap_quality_gate(bad_mm)
    assert report_bad["score"] < report["score"]
    assert len(report_bad["warnings"]) > 0


def test_mindmap_endpoints(monkeypatch, sample_book, tmp_path):
    # Mock CourseManager and auth
    class FakeRag:
        def __init__(self, course_id):
            self.course_id = course_id
            self.vectorstore = None

        def get_resource_generator(self):
            return ResourceGenerator(self)

    class FakeManager:
        def contains(self, course_id): return True
        def get_course(self, course_id): return FakeRag(course_id)

    monkeypatch.setattr(main, "course_manager", FakeManager())
    main.app.dependency_overrides[main.get_current_user] = lambda: main.UserInDB(
        id="test_admin", email="admin@example.com", password_hash="pwd", role="admin", is_active=True
    )
    
    # Mock get_course_path to use tmp_path
    def fake_path(course_id):
        return {
            "meta": str(tmp_path / f"meta_{course_id}.json"),
            "book": str(tmp_path / f"book_{course_id}.json"),
            "mindmap": str(tmp_path / f"mindmap_{course_id}.json"),
            "questions": str(tmp_path / f"questions_{course_id}.json"),
        }
    monkeypatch.setattr(main, "get_course_path", fake_path)
    monkeypatch.setattr("backend.core.config.get_course_path", fake_path)
    monkeypatch.setattr("backend.services.resource_gen.get_course_path", fake_path)
    
    # Write sample book to tmp_path
    with open(tmp_path / "book_test_course.json", "w", encoding="utf-8") as f:
        json.dump(sample_book, f)

    client = TestClient(main.app)

    # Test GET /api/course/test_course/mindmap (should build from book on first call)
    res = client.get("/api/course/test_course/mindmap")
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Nhập môn Mạng nơ-ron và Học sâu"
    assert "root" in data
    assert len(data["nodes"]) == 3

    # Test POST /api/course/test_course/mindmap/regenerate
    res_regen = client.post("/api/course/test_course/mindmap/regenerate")
    assert res_regen.status_code == 200
    data_regen = res_regen.json()
    assert data_regen["title"] == "Nhập môn Mạng nơ-ron và Học sâu"
    assert data_regen["quality_report"]["is_usable"] is True

    # Clean up overrides
    main.app.dependency_overrides.clear()
