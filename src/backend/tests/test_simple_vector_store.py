from backend.vector_db.simple_store import SimpleLocalVectorStore


def test_simple_vector_store_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.vector_db.simple_store.SIMPLE_VECTOR_DIR", str(tmp_path / "vectors"))

    store = SimpleLocalVectorStore(persist_dir=str(tmp_path / "vectors"))
    inserted = store.add_chunks(
        "doc1",
        ["Python handles AI data pipelines.", "Cooking recipes are unrelated."],
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        [
            {"chunk_id": 0, "page": 1, "source_file": "lesson.txt", "chunk_type": "content"},
            {"chunk_id": 1, "page": 2, "source_file": "lesson.txt", "chunk_type": "content"},
        ],
    )

    assert inserted == 2
    assert store.document_exists("doc1")
    assert store.count_chunks("doc1") == 2

    results = store.similarity_search([1.0, 0.0, 0.0], document_id="doc1", top_k=1)

    assert len(results) == 1
    assert "Python" in results[0].text
    assert results[0].metadata["document_id"] == "doc1"

    copied = store.copy_document("doc1", "doc2")

    assert copied == 2
    assert store.document_exists("doc2")

    store.delete_document("doc1")
    assert not store.document_exists("doc1")
