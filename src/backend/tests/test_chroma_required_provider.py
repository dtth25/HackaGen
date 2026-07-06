from backend.vector_db import manager


def test_legacy_local_providers_fall_back_to_chroma(monkeypatch):
    monkeypatch.setattr(manager, "VECTOR_DB_PROVIDER", "simple_dev_only")
    assert manager.get_vector_db_provider() == "chroma"

    monkeypatch.setattr(manager, "VECTOR_DB_PROVIDER", "faiss")
    assert manager.get_vector_db_provider() == "chroma"


def test_future_production_provider_reports_not_ready(monkeypatch):
    monkeypatch.setattr(manager, "VECTOR_DB_PROVIDER", "qdrant")

    assert manager.get_vector_db_provider() == "qdrant"
    health = manager.health_check()

    assert health["provider"] == "qdrant"
    assert health["ready"] is False
    assert "future production" in health["error"]


def test_list_all_vector_courses_reads_only_chroma(monkeypatch):
    monkeypatch.setattr(manager, "list_chroma_courses", lambda: ["doc2", "doc1", "doc1"])

    assert manager.list_all_vector_courses() == ["doc1", "doc2"]
