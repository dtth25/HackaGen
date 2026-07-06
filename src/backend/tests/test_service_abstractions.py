from backend.services.cache import LocalJsonCache
from backend.services.jobs import LocalThreadJobQueue
from backend.services.storage import LocalFileStorage


def test_local_file_storage_round_trip_and_delete(tmp_path):
    storage = LocalFileStorage(upload_dir=str(tmp_path / "uploads"), output_dir=str(tmp_path / "outputs"))

    upload_path = storage.save_upload("doc1", "lesson.txt", b"hello", index=1)
    assert storage.get_upload(upload_path) == b"hello"

    output_path = storage.save_output("doc1", "book/result.txt", b"study guide")
    assert storage.get_output(output_path) == b"study guide"

    health = storage.health_check()
    assert health["provider"] == "local"
    assert health["ready"] is True

    storage.delete_document_files("doc1", [output_path])
    assert not (tmp_path / "uploads" / "doc1").exists()
    assert not (tmp_path / "outputs" / "doc1" / "book" / "result.txt").exists()


def test_local_json_cache_document_hash_and_embedding(tmp_path):
    cache = LocalJsonCache(cache_dir=str(tmp_path / "cache"), embedding_cache_dir=str(tmp_path / "embeddings"))

    cache.set("hello", {"ok": True})
    assert cache.get("hello") == {"ok": True}

    cache.set_document_hash("hash1", "course1")
    assert cache.get_document_hash("hash1") == "course1"

    cache.set_embedding("chunkhash", "model/test", [0.1, 0.2])
    assert cache.get_embedding("chunkhash", "model/test") == [0.1, 0.2]

    cache.delete("hello")
    assert cache.get("hello") is None


def test_local_job_queue_runs_preprocess_job():
    queue = LocalThreadJobQueue()
    state = {"ran": False}

    def handler(value):
        state["ran"] = value

    job = queue.enqueue_preprocess("doc1", handler, True, user_id="user1")

    # LocalThreadJobQueue is async via daemon thread; wait briefly for deterministic test.
    import time

    for _ in range(50):
        status = queue.get_job_status(job.id)
        if status and status["status"] == "completed":
            break
        time.sleep(0.02)

    status = queue.get_job_status(job.id)
    assert state["ran"] is True
    assert status is not None
    assert status["document_id"] == "doc1"
    assert status["job_type"] == "preprocess"
    assert status["status"] == "completed"
