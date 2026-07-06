"""Job queue abstractions for preprocess and generation work.

The local queue uses daemon threads so the hackathon demo keeps working without
Redis. Production providers can implement the same contract with Celery/RQ/Arq.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Protocol

from backend.core.config import JOB_QUEUE_PROVIDER, logger

JobType = Literal[
    "preprocess",
    "generate_book",
    "generate_mindmap",
    "generate_quiz",
    "generate_flashcards",
    "generate_video",
    "generate_slides",
]
JobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


@dataclass
class JobRecord:
    """Serializable local job metadata compatible with a future Postgres schema."""

    id: str
    document_id: str
    job_type: str
    status: JobStatus = "queued"
    progress: int = 0
    message: str = "Queued"
    user_id: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "document_id": self.document_id,
            "user_id": self.user_id,
            "job_type": self.job_type,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
        }


class JobQueue(Protocol):
    """Minimal queue contract used by upload and future generation workers."""

    def enqueue_preprocess(
        self,
        document_id: str,
        handler: Callable[..., Any],
        *args: Any,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> JobRecord:
        """Queue document preprocessing work."""

    def enqueue_generation(
        self,
        document_id: str,
        job_type: JobType,
        handler: Callable[..., Any],
        *args: Any,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> JobRecord:
        """Queue output generation work."""

    def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        """Return a serialized job record."""

    def cancel_job(self, job_id: str) -> bool:
        """Mark a queued/running job as cancelled if possible."""

    def health_check(self) -> dict[str, Any]:
        """Return provider readiness."""


class LocalThreadJobQueue:
    """Local thread-backed queue for development."""

    provider = "inline"

    def __init__(self):
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def _create_job(self, document_id: str, job_type: str, user_id: str | None = None) -> JobRecord:
        job = JobRecord(id=uuid.uuid4().hex, document_id=document_id, job_type=job_type, user_id=user_id)
        with self._lock:
            self._jobs[job.id] = job
        logger.info("[JobQueue] Queued job_id=%s document_id=%s type=%s provider=%s", job.id, document_id, job_type, self.provider)
        return job

    def _update(self, job_id: str, **updates: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for key, value in updates.items():
                setattr(job, key, value)
            job.updated_at = time.time()

    def _run_job(self, job: JobRecord, handler: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        self._update(job.id, status="running", progress=max(job.progress, 1), message="Running")
        try:
            with self._lock:
                current = self._jobs.get(job.id)
                if current and current.status == "cancelled":
                    return
            handler(*args, **kwargs)
            self._update(
                job.id,
                status="completed",
                progress=100,
                message="Completed",
                completed_at=time.time(),
            )
            logger.info("[JobQueue] Completed job_id=%s document_id=%s type=%s", job.id, job.document_id, job.job_type)
        except Exception as exc:
            self._update(
                job.id,
                status="failed",
                error=str(exc),
                message="Failed",
                completed_at=time.time(),
            )
            logger.exception("[JobQueue] Failed job_id=%s document_id=%s type=%s: %s", job.id, job.document_id, job.job_type, exc)

    def enqueue_preprocess(
        self,
        document_id: str,
        handler: Callable[..., Any],
        *args: Any,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> JobRecord:
        job = self._create_job(document_id=document_id, job_type="preprocess", user_id=user_id)
        thread = threading.Thread(target=self._run_job, args=(job, handler, args, kwargs), daemon=True)
        thread.start()
        return job

    def enqueue_generation(
        self,
        document_id: str,
        job_type: JobType,
        handler: Callable[..., Any],
        *args: Any,
        user_id: str | None = None,
        **kwargs: Any,
    ) -> JobRecord:
        job = self._create_job(document_id=document_id, job_type=job_type, user_id=user_id)
        thread = threading.Thread(target=self._run_job, args=(job, handler, args, kwargs), daemon=True)
        thread.start()
        return job

    def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.to_dict() if job else None

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status in {"completed", "failed", "cancelled"}:
                return False
            job.status = "cancelled"
            job.message = "Cancelled"
            job.updated_at = time.time()
            job.completed_at = time.time()
            return True

    def health_check(self) -> dict[str, Any]:
        with self._lock:
            counts: dict[str, int] = {}
            for job in self._jobs.values():
                counts[job.status] = counts.get(job.status, 0) + 1
        return {"provider": self.provider, "ready": True, "jobs": counts}


_LOCAL_QUEUE: LocalThreadJobQueue | None = None


def get_job_queue(provider: str | None = None) -> JobQueue:
    """Return the configured job queue provider."""
    global _LOCAL_QUEUE
    selected = (provider or JOB_QUEUE_PROVIDER or "inline").strip().lower()
    if selected in {"inline", "local", "inline_or_local"}:
        if _LOCAL_QUEUE is None:
            _LOCAL_QUEUE = LocalThreadJobQueue()
        return _LOCAL_QUEUE
    if selected in {"redis_celery", "celery", "rq", "arq"}:
        raise NotImplementedError(
            f"JOB_QUEUE_PROVIDER={selected} is planned for production but not implemented yet. "
            "Use JOB_QUEUE_PROVIDER=inline for local/dev mode."
        )
    raise ValueError(f"Unknown JOB_QUEUE_PROVIDER={selected!r}.")
