from backend.vector_db import faiss_manager as fm


class FakeEmbeddings:
    def __init__(self):
        self.calls = 0
        self.batches = []

    def embed_documents(self, batch):
        self.calls += 1
        self.batches.append(list(batch))
        return [[float(len(text)), 1.0, 0.0] for text in batch]


def test_extract_retry_delay_from_gemini_quota_error():
    exc = RuntimeError(
        "Error embedding content: 429 quota exceeded "
        "retry_delay { seconds: 29 } Please retry in 29.339755837s."
    )

    assert fm._is_quota_error(exc)
    assert fm._extract_retry_delay_seconds(exc) == 29


def test_batch_embedding_uses_chunk_cache_and_dedupes(tmp_path, monkeypatch):
    monkeypatch.setattr(fm, "EMBEDDING_CACHE_DIR", str(tmp_path))
    from services.cache import LocalJsonCache
    monkeypatch.setattr(fm, "get_cache_provider", lambda: LocalJsonCache(embedding_cache_dir=str(tmp_path)))

    first_embeddings = FakeEmbeddings()
    first_stats = {}
    vectors = fm._batch_embed_texts(
        ["same chunk", "same chunk", "other chunk"],
        first_embeddings,
        batch_size=10,
        stats=first_stats,
    )

    assert len(vectors) == 3
    assert first_embeddings.calls == 1
    assert first_embeddings.batches == [["same chunk", "other chunk"]]
    assert first_stats["embedding_requests_sent"] == 2
    assert first_stats["embedding_duplicate_hits"] == 1
    assert first_stats["embedding_cache_hits"] == 0

    second_embeddings = FakeEmbeddings()
    second_stats = {}
    cached_vectors = fm._batch_embed_texts(
        ["same chunk", "other chunk"],
        second_embeddings,
        batch_size=10,
        stats=second_stats,
    )

    assert len(cached_vectors) == 2
    assert second_embeddings.calls == 0
    assert second_stats["embedding_requests_sent"] == 0
    assert second_stats["embedding_cache_hits"] == 2
