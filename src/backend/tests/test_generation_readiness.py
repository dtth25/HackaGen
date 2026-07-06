from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from backend import main
from backend.services.generation_readiness import evaluate_document_readiness
from backend.services.resource_gen import ResourceGenerator


def test_evaluate_document_readiness_empty():
    report = evaluate_document_readiness([], document_id="test_empty")
    assert report["overall_quality_score"] == 0
    assert report["clean_chunks_count"] == 0
    assert report["generation_readiness"]["book"]["status"] == "not_enough_context"
    assert "chưa đọc được đủ text" in report["warnings"][0].lower() or "bản scan" in report["warnings"][0].lower()


def test_evaluate_document_readiness_sufficient():
    docs = [
        Document(
            page_content=f"=== BẮT ĐẦU DỮ LIỆU TRUY XUẤT ===\nNội dung chi tiết chương {i} về Trí tuệ nhân tạo và Mạng nơ-ron CNN ứng dụng thực tế phong phú với nhiều ví dụ minh họa chuyên sâu trong khoa học máy tính, kèm theo phân tích chuyên sâu về kiến trúc mô hình và các trường hợp áp dụng thực tế trong công nghiệp.",
            metadata={"source": "test.pdf", "page": i, "chunk_id": f"chunk_{i}"}
        ) for i in range(1, 15)
    ]
    report = evaluate_document_readiness(docs, document_id="test_suff")
    assert report["clean_chunks_count"] >= 8
    assert report["generation_readiness"]["book"]["status"] == "ready"
    assert "book" in report["safe_outputs_available"]


def test_readiness_and_fallback_api(monkeypatch):
    # /readiness and /generate-fallback now require an authenticated, owning user
    # (see main._verify_course_access); dependency_overrides is monkeypatched via
    # setitem so it's automatically reverted after this test.
    monkeypatch.setitem(
        main.app.dependency_overrides,
        main.get_current_user,
        lambda: main.UserInDB(id="test_admin", email="admin@example.com", password_hash="pwd", role="admin", is_active=True),
    )
    client = TestClient(main.app)

    # Mock generator for readiness check
    mock_gen = MagicMock()
    mock_gen.evaluate_readiness.return_value = {
        "document_id": "test_api_course",
        "overall_quality_score": 40,
        "clean_chunks_count": 2,
        "generation_readiness": {
            "book": {"status": "not_enough_context", "reason": "Chưa đủ dữ liệu.", "recommended_fallback": "summary"}
        },
        "safe_outputs_available": ["summary", "flashcards"]
    }
    mock_gen.generate_fallback_summary.return_value = {
        "title": "Tóm tắt tài liệu",
        "summary": "Nội dung tóm tắt dự phòng an toàn.",
        "main_points": ["Điểm 1", "Điểm 2"],
        "source_chunk_ids": ["chunk_1"]
    }
    
    monkeypatch.setattr(main, "_get_generator_for_readiness", lambda cid: mock_gen)
    
    # Test GET readiness endpoint
    res_readiness = client.get("/api/course/test_api_course/readiness")
    assert res_readiness.status_code == 200
    data_r = res_readiness.json()
    assert data_r["overall_quality_score"] == 40
    assert "summary" in data_r["safe_outputs_available"]
    
    # Test POST generate-fallback endpoint
    res_fb = client.post("/api/course/test_api_course/generate-fallback", json={"fallback_type": "summary"})
    assert res_fb.status_code == 200
    data_fb = res_fb.json()
    assert data_fb["status"] == "success"
    assert data_fb["fallback_type"] == "summary"
    assert data_fb["result"]["summary"] == "Nội dung tóm tắt dự phòng an toàn."


def _fake_rag_chains(vectorstore=None, course_id="test_resource_gen"):
    rag = MagicMock()
    rag.course_id = course_id
    rag.vectorstore = vectorstore
    return rag


def test_resource_generator_evaluate_readiness_without_vectorstore():
    """evaluate_readiness must not crash when no vectorstore is attached yet."""
    generator = ResourceGenerator(_fake_rag_chains(vectorstore=None))
    report = generator.evaluate_readiness()

    assert report["document_id"] == "test_resource_gen"
    assert report["overall_quality_score"] == 0
    assert report["generation_readiness"]["book"]["status"] == "not_enough_context"
    # Public response must not leak internal chunk/page/source metadata.
    assert "cleaned_docs" not in report
    assert "stats" not in report


def test_resource_generator_evaluate_readiness_with_docs():
    """evaluate_readiness reflects real retrieved docs through the actual generator."""
    docs = [
        Document(
            page_content=f"Nội dung chi tiết chương {i} về Trí tuệ nhân tạo và Mạng nơ-ron CNN ứng dụng thực tế phong phú với nhiều ví dụ minh họa chuyên sâu trong khoa học máy tính và công nghiệp.",
            metadata={"chunk_id": f"chunk_{i}"},
        )
        for i in range(1, 15)
    ]
    vectorstore = MagicMock()
    vectorstore.as_retriever.return_value.invoke.return_value = docs

    generator = ResourceGenerator(_fake_rag_chains(vectorstore=vectorstore))
    report = generator.evaluate_readiness()

    assert report["clean_chunks_count"] >= 8
    assert report["generation_readiness"]["book"]["status"] == "ready"
    assert "book" in report["safe_outputs_available"]


def test_resource_generator_fallback_methods_without_docs():
    """Fallback generators must degrade gracefully with no usable context."""
    generator = ResourceGenerator(_fake_rag_chains(vectorstore=None))

    summary = generator.generate_fallback_summary("Tóm tắt", [])
    assert summary["main_points"] == []
    assert summary["key_terms"] == []
    assert summary["limitations"]
    assert summary["source_chunk_ids"] == []

    outline = generator.generate_fallback_outline("Dàn ý", [])
    assert outline["detected_topics"] == []
    assert outline["possible_sections"] == []
    assert outline["missing_context_warning"]

    key_terms = generator.generate_fallback_key_terms("Thuật ngữ", [])
    assert key_terms["terms"] == []

    high_yield = generator.generate_fallback_high_yield("Trọng tâm", [])
    assert high_yield["core_ideas"] == []
    assert high_yield["must_know_points"] == []
    assert high_yield["quick_review_questions"] == []


def test_resource_generator_fallback_methods_with_docs():
    """Fallback generators produce grounded, non-empty content from real chunks."""
    docs = [
        Document(
            page_content=f"Định nghĩa khái niệm số {i}: mạng nơ-ron nhân tạo là một mô hình tính toán.",
            metadata={"chunk_id": f"chunk_{i}"},
        )
        for i in range(1, 6)
    ]
    generator = ResourceGenerator(_fake_rag_chains(vectorstore=None))

    summary = generator.generate_fallback_summary("Tóm tắt", docs)
    assert summary["summary"]
    assert summary["source_chunk_ids"]
    assert "MÃ ĐỊNH DANH TRANG" not in summary["summary"]

    key_terms = generator.generate_fallback_key_terms("Thuật ngữ", docs)
    assert key_terms["terms"]
    assert all(t["term"] and t["definition"] for t in key_terms["terms"])

    high_yield = generator.generate_fallback_high_yield("Trọng tâm", docs)
    assert high_yield["core_ideas"]
    assert high_yield["quick_review_questions"]
    assert high_yield["source_chunk_ids"]

    outline = generator.generate_fallback_outline("Dàn ý", docs)
    assert outline["detected_topics"]
    assert outline["possible_sections"]
    assert all(s["heading"] for s in outline["possible_sections"])
    assert outline["source_chunk_ids"]
