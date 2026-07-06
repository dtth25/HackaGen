from backend.vector_db.chroma_store import ChromaVectorStore


def test_chroma_vector_store_round_trip(tmp_path):
    store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma"),
        collection_name="test_ai_course_chunks",
    )

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

    store.add_chunks(
        "doc2",
        ["Another document talks about Python but must stay isolated."],
        [[1.0, 0.0, 0.0]],
        [{"chunk_id": 0, "page": 1, "source_file": "other.txt", "chunk_type": "content"}],
    )

    results = store.similarity_search([1.0, 0.0, 0.0], document_id="doc1", top_k=1)

    assert len(results) == 1
    assert "Python" in results[0].text
    assert results[0].metadata["document_id"] == "doc1"
    assert "Another document" not in results[0].text

    try:
        store.similarity_search([1.0, 0.0, 0.0], top_k=1)
        raise AssertionError("Chroma search without document_id should fail")
    except ValueError as exc:
        assert "requires document_id" in str(exc)

    store.delete_document("doc1")
    assert not store.document_exists("doc1")
    assert store.document_exists("doc2")


def test_chroma_copy_document_reuses_vectors_with_new_document_id(tmp_path):
    store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma"),
        collection_name="test_ai_course_copy_chunks",
    )
    store.add_chunks(
        "original",
        ["Cached chunk for repeated upload."],
        [[0.5, 0.5, 0.0]],
        [{"chunk_id": 0, "source_chunk_id": "chunk_0", "page": 7, "source_file": "lesson.pdf", "user_id": "user_a"}],
    )

    copied = store.copy_document("original", "copy")
    results = store.similarity_search([0.5, 0.5, 0.0], document_id="copy", top_k=1)

    assert copied == 1
    assert store.count_chunks("copy") == 1
    assert results[0].metadata["document_id"] == "copy"
    assert results[0].metadata["cached_from"] == "original"
    # Re-copying without an explicit user_id must not silently keep the source
    # uploader's user_id on the new document.
    assert "user_id" not in results[0].metadata

    copied_for_new_user = store.copy_document("original", "copy2", user_id="user_b")
    results_new_user = store.similarity_search([0.5, 0.5, 0.0], document_id="copy2", top_k=1)
    assert copied_for_new_user == 1
    assert results_new_user[0].metadata["user_id"] == "user_b"


def test_similarity_search_excludes_toc_and_noisy_chunks_by_default(tmp_path):
    store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma"),
        collection_name="test_ai_course_filter_chunks",
    )
    store.add_chunks(
        "doc_filter",
        [
            "Mục lục Chương 1 . . . . . . 5",
            "Định nghĩa gradient descent là thuật toán tối ưu.",
            "Ví dụ minh họa: phân loại ảnh chữ số viết tay.",
        ],
        [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        [
            {"chunk_id": 0, "page": 1, "chunk_type": "toc", "use_for_generation": False},
            {"chunk_id": 1, "page": 2, "chunk_type": "definition", "use_for_generation": True},
            {"chunk_id": 2, "page": 3, "chunk_type": "example", "use_for_generation": True},
        ],
    )

    filtered = store.similarity_search([1.0, 0.0, 0.0], document_id="doc_filter", top_k=5)
    filtered_types = {item.metadata.get("chunk_type") for item in filtered}
    assert "toc" not in filtered_types
    assert filtered_types <= {"definition", "example"}

    unfiltered = store.similarity_search([1.0, 0.0, 0.0], document_id="doc_filter", top_k=5, exclude_noisy=False)
    assert len(unfiltered) == 3
    assert "toc" in {item.metadata.get("chunk_type") for item in unfiltered}


def test_similarity_search_backward_compatible_with_legacy_content_chunk_type(tmp_path):
    """Chunks indexed before classification existed only have chunk_type='content'."""
    store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma"),
        collection_name="test_ai_course_legacy_chunks",
    )
    store.add_chunks(
        "doc_legacy",
        ["Legacy chunk with no classification metadata."],
        [[1.0, 0.0, 0.0]],
        [{"chunk_id": 0, "page": 1, "chunk_type": "content"}],
    )
    results = store.similarity_search([1.0, 0.0, 0.0], document_id="doc_legacy", top_k=5)
    assert len(results) == 1


def test_similarity_search_dedupes_and_diversifies_pages(tmp_path):
    store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma"),
        collection_name="test_ai_course_diversify_chunks",
    )
    # 4 near-identical chunks on the same page + 1 distinct chunk on another page.
    texts = [
        "Gradient descent cập nhật trọng số theo đạo hàm.",
        "Gradient descent cập nhật trọng số theo đạo hàm.",
        "Gradient descent cập nhật trọng số theo đạo hàm!",
        "Gradient descent cập nhật trọng số theo đạo hàm?",
        "Hàm kích hoạt ReLU cắt bỏ phần âm của tín hiệu.",
    ]
    store.add_chunks(
        "doc_diverse",
        texts,
        [[1.0, 0.0, 0.0]] * 5,
        [
            {"chunk_id": 0, "page": 1, "chunk_type": "body", "use_for_generation": True},
            {"chunk_id": 1, "page": 1, "chunk_type": "body", "use_for_generation": True},
            {"chunk_id": 2, "page": 1, "chunk_type": "body", "use_for_generation": True},
            {"chunk_id": 3, "page": 1, "chunk_type": "body", "use_for_generation": True},
            {"chunk_id": 4, "page": 2, "chunk_type": "body", "use_for_generation": True},
        ],
    )
    results = store.similarity_search([1.0, 0.0, 0.0], document_id="doc_diverse", top_k=3)
    pages = [item.metadata.get("page") for item in results]
    assert pages.count(1) <= 2  # max_per_page cap keeps page 1 from dominating
    assert 2 in pages  # the distinct chunk on page 2 survives diversification


def test_reset_collection_clears_all_documents(tmp_path):
    store = ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma"),
        collection_name="test_ai_course_reset_chunks",
    )
    store.add_chunks("doc_a", ["Some text."], [[1.0, 0.0, 0.0]], [{"chunk_id": 0}])
    assert store.document_exists("doc_a")

    store.reset_collection()

    assert not store.document_exists("doc_a")
    assert store.count_chunks() == 0
