from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional
import threading
import uuid
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    id: str
    name: str
    status: str = "queued"  # queued | running | success | failed
    created_at: str = field(default_factory=_now_iso)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    # Metrics
    collected: int = 0
    stored: int = 0
    skipped: int = 0
    message: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class JobTracker:
    _lock = threading.Lock()
    _jobs: Dict[str, Job] = {}

    @classmethod
    def create_job(cls, name: str, params: Optional[Dict[str, Any]] = None) -> str:
        job_id = str(uuid.uuid4())
        with cls._lock:
            cls._jobs[job_id] = Job(id=job_id, name=name, params=params or {})
        return job_id

    @classmethod
    def get(cls, job_id: str) -> Optional[Dict[str, Any]]:
        with cls._lock:
            job = cls._jobs.get(job_id)
            return job.to_dict() if job else None

    @classmethod
    def mark_running(cls, job_id: str, message: Optional[str] = None) -> None:
        with cls._lock:
            job = cls._jobs.get(job_id)
            if not job:
                return
            job.status = "running"
            job.started_at = job.started_at or _now_iso()
            job.message = message

    @classmethod
    def update(cls, job_id: str, **metrics: Any) -> None:
        with cls._lock:
            job = cls._jobs.get(job_id)
            if not job:
                return
            for k, v in metrics.items():
                if hasattr(job, k):
                    setattr(job, k, v)

    @classmethod
    def mark_success(
        cls,
        job_id: str,
        message: Optional[str] = None,
        **metrics: Any,
    ) -> None:
        with cls._lock:
            job = cls._jobs.get(job_id)
            if not job:
                return
            for k, v in metrics.items():
                if hasattr(job, k):
                    setattr(job, k, v)
            job.status = "success"
            job.finished_at = _now_iso()
            job.message = message

    @classmethod
    def mark_failed(cls, job_id: str, error: str) -> None:
        with cls._lock:
            job = cls._jobs.get(job_id)
            if not job:
                return
            job.status = "failed"
            job.finished_at = _now_iso()
            job.error = error

