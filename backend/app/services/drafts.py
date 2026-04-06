from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from backend.app.core.exceptions import NotFoundError
from backend.app.models.schemas import DraftRecord, DraftSaveRequest


class DraftStore:
    def __init__(self, path: Path):
        self.path = path
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list(self, limit: int = 20) -> list[DraftRecord]:
        with self._lock:
            payload = self._read_raw()
        drafts = [DraftRecord(**item) for item in payload]
        drafts.sort(key=lambda item: item.updated_at, reverse=True)
        return drafts[:limit]

    def get(self, draft_id: str) -> DraftRecord:
        with self._lock:
            payload = self._read_raw()
        for item in payload:
            if item.get("draft_id") == draft_id:
                return DraftRecord(**item)
        raise NotFoundError(f"Draft '{draft_id}' was not found.")

    def save(self, request: DraftSaveRequest) -> DraftRecord:
        now = datetime.now(timezone.utc)
        with self._lock:
            payload = self._read_raw()
            if request.draft_id:
                for index, item in enumerate(payload):
                    if item.get("draft_id") == request.draft_id:
                        created_at = item.get("created_at") or now.isoformat()
                        status = item.get("status") or "draft"
                        published_at = item.get("published_at")
                        updated = DraftRecord(
                            draft_id=request.draft_id,
                            title=request.title.strip() or item.get("title") or "Untitled Draft",
                            target=request.target,
                            raw_input=request.raw_input,
                            structured_markdown=request.structured_markdown,
                            preview_html=request.preview_html,
                            source=request.source or item.get("source") or "dashboard",
                            status=status,
                            metadata=request.metadata,
                            created_at=_coerce_datetime(created_at),
                            updated_at=now,
                            published_at=_coerce_datetime(published_at) if published_at else None,
                        )
                        payload[index] = updated.model_dump(mode="json")
                        self._write_raw(payload)
                        return updated

            created = DraftRecord(
                draft_id=request.draft_id or uuid4().hex[:12],
                title=request.title.strip() or "Untitled Draft",
                target=request.target,
                raw_input=request.raw_input,
                structured_markdown=request.structured_markdown,
                preview_html=request.preview_html,
                source=request.source or "dashboard",
                status="draft",
                metadata=request.metadata,
                created_at=now,
                updated_at=now,
            )
            payload.append(created.model_dump(mode="json"))
            self._write_raw(payload)
            return created

    def mark_published(self, draft_id: str, *, metadata: dict) -> DraftRecord:
        now = datetime.now(timezone.utc)
        with self._lock:
            payload = self._read_raw()
            for index, item in enumerate(payload):
                if item.get("draft_id") != draft_id:
                    continue
                item["status"] = "published"
                item["published_at"] = now.isoformat()
                item["updated_at"] = now.isoformat()
                item["metadata"] = {**(item.get("metadata") or {}), **metadata}
                payload[index] = item
                self._write_raw(payload)
                return DraftRecord(**item)
        raise NotFoundError(f"Draft '{draft_id}' was not found.")

    def _read_raw(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def _write_raw(self, payload: list[dict]) -> None:
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _coerce_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
