from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.models.schemas import AskJobResponse
from backend.app.services.qa import QAService


class AskJobManager:
    def __init__(self, qa_factory, max_workers: int = 2):
        self._qa_factory = qa_factory
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="veriagent-qa")
        self._jobs: dict[str, AskJobResponse] = {}
        self._lock = Lock()

    def submit(self, query: str, top_k: int, generate_selenium: bool) -> AskJobResponse:
        if not query.strip():
            raise ValidationError("A query is required.")

        now = datetime.now(timezone.utc)
        job = AskJobResponse(
            job_id=uuid4().hex,
            status="queued",
            query=query,
            top_k=top_k,
            generate_selenium=generate_selenium,
            submitted_at=now,
        )
        with self._lock:
            self._jobs[job.job_id] = job
        self._executor.submit(self._run_job, job.job_id)
        return job.model_copy(deep=True)

    def get(self, job_id: str) -> AskJobResponse:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise NotFoundError(f"QA job not found: {job_id}")
            return job.model_copy(deep=True)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=False)

    def _run_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            query = job.query
            top_k = job.top_k
            generate_selenium = job.generate_selenium

        try:
            qa_service: QAService = self._qa_factory()
            result = qa_service.answer(query=query, top_k=top_k, generate_selenium=generate_selenium)
            with self._lock:
                job = self._jobs[job_id]
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)
                job.result = result
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                job = self._jobs[job_id]
                job.status = "failed"
                job.completed_at = datetime.now(timezone.utc)
                job.error = str(exc)
