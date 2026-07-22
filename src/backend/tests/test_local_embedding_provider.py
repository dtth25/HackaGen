"""Coverage for the local (bge-m3) embedding provider: VectorStore._collection_for now
routes to a real, separate collection per provider instead of hardcoding "openrouter" as the
only valid value, and Generator._get_embedding_provider no longer collapses every non-legacy
value to "openrouter". The real bge-m3 model (~2.2GB, ~260s cold load) is never constructed
in these tests — LocalEmbeddingFunction._get_model is mocked or simply never invoked, since
PYTEST_CURRENT_TEST already short-circuits real embedding-function construction."""

import tempfile
import shutil

import pytest

from app.models.course import Course
from app.services.generator import Generator
from app.services.vector_store import Document, LocalEmbeddingFunction, VectorStore

import app.services.database as db_service


def test_collection_for_local_is_distinct_from_openrouter():
    temp_dir = tempfile.mkdtemp()
    try:
        vs = VectorStore(collection_name="test_local_provider", persist_directory=temp_dir)

        openrouter_collection = vs._collection_for("openrouter")
        local_collection = vs._collection_for("local")

        assert openrouter_collection.name == "test_local_provider_openrouter"
        assert local_collection.name == "test_local_provider_local"
        assert openrouter_collection.name != local_collection.name
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_collection_for_local_is_cached_not_rebuilt_per_call():
    temp_dir = tempfile.mkdtemp()
    try:
        vs = VectorStore(collection_name="test_local_cache", persist_directory=temp_dir)

        first = vs._collection_for("local")
        second = vs._collection_for("local")

        assert first is second
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_collection_for_rejects_unknown_provider():
    temp_dir = tempfile.mkdtemp()
    try:
        vs = VectorStore(collection_name="test_unknown_provider", persist_directory=temp_dir)
        with pytest.raises(ValueError):
            vs._collection_for("gemini")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_add_and_search_documents_round_trips_through_local_collection():
    """End-to-end (within Chroma's own default test-mode embedding function, not bge-m3):
    documents added with provider="local" must be retrievable via provider="local" search,
    and must NOT be visible when searching provider="openrouter" — the two collections are
    genuinely isolated, not just differently-named views of the same data."""
    temp_dir = tempfile.mkdtemp()
    try:
        vs = VectorStore(collection_name="test_local_roundtrip", persist_directory=temp_dir)
        course_id = "course_local_1"

        vs.add_documents(
            [Document(content="Nội dung học về mạng nơ-ron nhân tạo.", metadata={"page": 1, "source_file": "a.pdf", "chunk_id": "c1"})],
            course_id=course_id,
            provider="local",
        )

        local_results = vs.search("mạng nơ-ron", course_id=course_id, k=5, provider="local")
        openrouter_results = vs.search("mạng nơ-ron", course_id=course_id, k=5, provider="openrouter")

        assert len(local_results) == 1
        assert len(openrouter_results) == 0


    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_local_embedding_function_model_is_a_process_singleton(monkeypatch):
    """The bge-m3 model must be loaded once per process (class-level cache), never rebuilt
    per LocalEmbeddingFunction instance or per call — construction takes minutes."""
    LocalEmbeddingFunction._model = None
    build_calls = []

    class _FakeModel:
        def encode(self, texts):
            class _Arr(list):
                def tolist(self):
                    return self

            return _Arr([[0.1, 0.2] for _ in texts])

    class _FakeSentenceTransformer:
        def __init__(self, model_name, device):
            build_calls.append((model_name, device))
            self._model = _FakeModel()

        def encode(self, texts):
            return self._model.encode(texts)

    monkeypatch.setattr("sentence_transformers.SentenceTransformer", _FakeSentenceTransformer)

    ef1 = LocalEmbeddingFunction()
    ef2 = LocalEmbeddingFunction()
    ef1(["a"])
    ef2(["b"])

    assert len(build_calls) == 1, "model should only be constructed once across two instances"
    LocalEmbeddingFunction._model = None


def test_get_embedding_provider_honors_local_without_collapsing_to_openrouter():
    """Confirmed bug from the QA sweep's OCR/embedding pivot research: _get_embedding_provider
    used to collapse ANY non-'gemini' value straight to 'openrouter', silently ignoring a
    course's real 'local' setting."""
    course_id = "course_local_provider_check"
    with db_service.SessionLocal() as db:
        db.add(Course(id=course_id, user_id="u1", status="ready", stage="completed", progress=100, embedding_provider="local"))
        db.commit()

    generator = Generator(vector_store=None, llm=None)
    provider = generator._get_embedding_provider(course_id)

    assert provider == "local"


def test_get_embedding_provider_still_defaults_openrouter_courses_correctly():
    course_id = "course_openrouter_provider_check"
    with db_service.SessionLocal() as db:
        db.add(Course(id=course_id, user_id="u1", status="ready", stage="completed", progress=100, embedding_provider="openrouter"))
        db.commit()

    generator = Generator(vector_store=None, llm=None)
    provider = generator._get_embedding_provider(course_id)

    assert provider == "openrouter"
