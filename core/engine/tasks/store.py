"""File-backed task store for session action plans."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

from engine.tasks.models import (
    TaskListDocument,
    TaskListMeta,
    TaskListRole,
    TaskRecord,
    TaskStatus,
)
from engine.utils.io import atomic_write

logger = logging.getLogger(__name__)

DOC_FILENAME = "tasks.json"
_INPROC_LOCKS: dict[str, threading.Lock] = {}
_INPROC_GUARD = threading.Lock()


def _engine_root() -> Path:
    return Path(os.environ.get("ENGINE_HOME", str(Path.home() / ".engine")))


def task_list_path(task_list_id: str, *, engine_root: Path | None = None) -> Path:
    root = engine_root or _engine_root()
    if task_list_id.startswith("session:"):
        rest = task_list_id[len("session:") :]
        agent_id, _, session_id = rest.partition(":")
        if not session_id:
            raise ValueError(f"Malformed session task_list_id: {task_list_id!r}")
        return root / "agents" / agent_id / "sessions" / session_id
    if task_list_id.startswith("template:"):
        template_id = task_list_id[len("template:") :]
        return root / "templates" / template_id
    if task_list_id.startswith("supervisor:"):
        session_id = task_list_id[len("supervisor:") :]
        return root / "supervisor_sessions" / session_id
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in task_list_id)
    return root / "task_lists" / safe


def _lock_for(task_list_id: str) -> threading.Lock:
    with _INPROC_GUARD:
        lock = _INPROC_LOCKS.get(task_list_id)
        if lock is None:
            lock = threading.Lock()
            _INPROC_LOCKS[task_list_id] = lock
        return lock


class TaskStore:
    """Async façade over on-disk task documents."""

    def __init__(self, *, engine_root: Path | None = None) -> None:
        self._engine_root = engine_root

    def _doc_path(self, task_list_id: str) -> Path:
        return task_list_path(task_list_id, engine_root=self._engine_root) / DOC_FILENAME

    async def list_exists(self, task_list_id: str) -> bool:
        return await asyncio.to_thread(self._doc_path(task_list_id).exists)

    async def ensure_task_list(
        self,
        task_list_id: str,
        *,
        role: TaskListRole = TaskListRole.SESSION,
        creator_agent_id: str | None = None,
    ) -> TaskListMeta:
        return await asyncio.to_thread(
            self._ensure_sync,
            task_list_id,
            role,
            creator_agent_id,
        )

    async def list_tasks(self, task_list_id: str) -> list[TaskRecord]:
        return await asyncio.to_thread(self._list_sync, task_list_id)

    async def create_tasks_batch(
        self,
        task_list_id: str,
        specs: list[dict[str, Any]],
    ) -> list[TaskRecord]:
        return await asyncio.to_thread(self._create_batch_sync, task_list_id, specs)

    async def update_task(
        self,
        task_list_id: str,
        task_id: int,
        *,
        status: TaskStatus | None = None,
        subject: str | None = None,
        description: str | None = None,
    ) -> TaskRecord | None:
        return await asyncio.to_thread(
            self._update_sync,
            task_list_id,
            task_id,
            status,
            subject,
            description,
        )

    def _ensure_sync(
        self,
        task_list_id: str,
        role: TaskListRole,
        creator_agent_id: str | None,
    ) -> TaskListMeta:
        with _lock_for(task_list_id):
            doc = self._read_unsafe(task_list_id)
            if doc is None:
                meta = TaskListMeta(
                    task_list_id=task_list_id,
                    role=role,
                    creator_agent_id=creator_agent_id,
                )
                doc = TaskListDocument(meta=meta)
                self._write_unsafe(task_list_id, doc)
                return meta
            return doc.meta

    def _read_unsafe(self, task_list_id: str) -> TaskListDocument | None:
        path = self._doc_path(task_list_id)
        if not path.exists():
            return None
        try:
            return TaskListDocument.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Corrupt tasks.json at %s", path, exc_info=True)
            return None

    def _write_unsafe(self, task_list_id: str, doc: TaskListDocument) -> None:
        path = self._doc_path(task_list_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with atomic_write(path) as f:
            f.write(doc.model_dump_json(indent=2))

    def _list_sync(self, task_list_id: str) -> list[TaskRecord]:
        doc = self._read_unsafe(task_list_id)
        if doc is None:
            return []
        return sorted(doc.tasks, key=lambda r: r.id)

    def _next_id(self, doc: TaskListDocument) -> int:
        max_existing = max((r.id for r in doc.tasks), default=0)
        return max(max_existing, doc.highwatermark) + 1

    def _create_batch_sync(
        self,
        task_list_id: str,
        specs: list[dict[str, Any]],
    ) -> list[TaskRecord]:
        if not specs:
            return []
        for i, spec in enumerate(specs):
            subject = spec.get("subject")
            if not isinstance(subject, str) or not subject.strip():
                raise ValueError(f"specs[{i}].subject must be a non-empty string")

        with _lock_for(task_list_id):
            doc = self._read_unsafe(task_list_id)
            if doc is None:
                role = (
                    TaskListRole.TEMPLATE
                    if task_list_id.startswith("template:")
                    else TaskListRole.SESSION
                )
                doc = TaskListDocument(meta=TaskListMeta(task_list_id=task_list_id, role=role))

            base_id = self._next_id(doc)
            now = time.time()
            records: list[TaskRecord] = []
            for offset, spec in enumerate(specs):
                rec = TaskRecord(
                    id=base_id + offset,
                    subject=spec["subject"],
                    description=spec.get("description", ""),
                    active_form=spec.get("active_form"),
                    owner=spec.get("owner"),
                    status=TaskStatus.PENDING,
                    metadata=dict(spec.get("metadata") or {}),
                    created_at=now,
                    updated_at=now,
                )
                records.append(rec)
            doc.tasks.extend(records)
            doc.highwatermark = records[-1].id
            self._write_unsafe(task_list_id, doc)
            return records

    def _update_sync(
        self,
        task_list_id: str,
        task_id: int,
        status: TaskStatus | None,
        subject: str | None,
        description: str | None,
    ) -> TaskRecord | None:
        with _lock_for(task_list_id):
            doc = self._read_unsafe(task_list_id)
            if doc is None:
                return None
            target = next((r for r in doc.tasks if r.id == task_id), None)
            if target is None:
                return None
            if status is not None:
                target.status = status
            if subject is not None:
                target.subject = subject
            if description is not None:
                target.description = description
            target.updated_at = time.time()
            self._write_unsafe(task_list_id, doc)
            return target


_default_store: TaskStore | None = None


def get_task_store() -> TaskStore:
    global _default_store
    if _default_store is None:
        _default_store = TaskStore()
    return _default_store
