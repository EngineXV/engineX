"""Shared State Manager - Manages state across concurrent executions"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class IsolationLevel(StrEnum):
    """State isolation level for concurrent executions"""

    ISOLATED = "isolated"  # Private state per execution
    SHARED = "shared"  # Shared state (eventual consistency)
    SYNCHRONIZED = "synchronized"  # Shared with write locks (strong consistency)


class StateScope(StrEnum):
    """Scope for state operations"""

    EXECUTION = "execution"  # Local to a single execution
    STREAM = "stream"  # Shared within a stream
    GLOBAL = "global"  # Shared across all streams


@dataclass
class StateChange:
    """Record of a state change"""

    key: str
    old_value: Any
    new_value: Any
    scope: StateScope
    execution_id: str
    stream_id: str
    timestamp: float = field(default_factory=time.time)


class SharedStateManager:
    """Manages shared state across concurrent executions"""

    def __init__(
        self,
        session_store=None,
        session_id: str | None = None,
    ):
        # State storage at each level
        self._global_state: dict[str, Any] = {}
        self._stream_state: dict[str, dict[str, Any]] = {}  # stream_id -> {key: value}
        self._execution_state: dict[str, dict[str, Any]] = {}  # execution_id -> {key: value}

        # Locks for synchronized access.
        # NOTE: asyncio.Lock objects cannot be persisted. They coordinate
        # in-process concurrent writes only; cross-worker consistency will be
        # handled by a claim-based mechanism (see docs/stateless_workers_audit.md).
        self._global_lock = asyncio.Lock()
        self._stream_locks: dict[str, asyncio.Lock] = {}
        self._key_locks: dict[str, asyncio.Lock] = {}

        # Change history for debugging/auditing
        self._change_history: list[StateChange] = []
        self._max_history = 1000

        # Version tracking
        self._version = 0

        # Optional persistence to the session store
        self._session_store = session_store
        self._session_id = session_id
        self._persist_queue: asyncio.Queue | None = None
        self._persist_thread: threading.Thread | None = None
        self._persist_loop: asyncio.AbstractEventLoop | None = None
        self._persist_worker_task: asyncio.Future | None = None
        self._persist_worker: asyncio.Task | None = None  # strong ref on the persist loop
        self._persist_seq = 0  # last enqueued snapshot id
        self._persist_written = 0  # last snapshot id written to disk
        if self._session_store is not None and self._session_id is not None:
            self._restore()

    # === PERSISTENCE ===

    def _restore(self) -> None:
        """Load persisted shared state from the session store (if any)."""
        if self._session_store is None or self._session_id is None:
            return

        # Attempt a synchronous load; if a loop is running, fall back to the
        # async path and wait for it (used when constructed inside a task).
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            state = self._session_store.read_state_sync(self._session_id)
        else:
            state = self._run_async(self._session_store.read_state(self._session_id))
        if state is None:
            return

        persisted = state.shared_state or {}
        self._global_state = dict(persisted.get("global", {}))
        self._stream_state = {k: dict(v) for k, v in persisted.get("streams", {}).items()}
        self._execution_state = {k: dict(v) for k, v in persisted.get("executions", {}).items()}
        self._version = persisted.get("version", 0)
        logger.debug(
            "Restored shared state for session %s (global=%d, streams=%d, executions=%d)",
            self._session_id,
            len(self._global_state),
            len(self._stream_state),
            len(self._execution_state),
        )

    def _serialize(self) -> dict[str, Any]:
        """Snapshot current in-memory state into a persistable dict."""
        return {
            "global": dict(self._global_state),
            "streams": {sid: dict(s) for sid, s in self._stream_state.items()},
            "executions": {eid: dict(e) for eid, e in self._execution_state.items()},
            "version": self._version,
        }

    def _persist(self) -> None:
        """Queue a snapshot of current shared state for the session store.

        Writes are serialized through a single worker (coalescing redundant
        snapshots) and use read-modify-write on ``state.shared_state`` so
        concurrent writers (e.g. the executor writing session output) are not
        clobbered. asyncio.Lock objects are intentionally excluded — they are
        process-local and cannot be persisted.
        """
        if self._session_store is None or self._session_id is None:
            return

        snapshot = self._serialize()
        self._persist_seq += 1
        snapshot["_seq"] = self._persist_seq
        if self._persist_queue is None:
            # No running loop: spin up a dedicated loop + worker thread.
            self._persist_loop = asyncio.new_event_loop()
            self._persist_queue = asyncio.Queue()
            self._persist_thread = threading.Thread(
                target=self._persist_loop.run_forever,
                name=f"shared-state-persist-{self._session_id}",
                daemon=True,
            )
            self._persist_thread.start()
            self._persist_worker_task = asyncio.run_coroutine_threadsafe(
                self._ensure_persist_worker(), self._persist_loop
            )

        asyncio.run_coroutine_threadsafe(self._persist_queue.put(snapshot), self._persist_loop)

    async def _ensure_persist_worker(self) -> None:
        """Start the serialized writer task on the persist loop (idempotent)."""
        if self._persist_worker is None:
            self._persist_worker = asyncio.create_task(self._persist_worker_loop())

    async def _persist_worker_loop(self) -> None:
        """Serialized writer: persist one snapshot at a time (latest wins)."""
        while True:
            snapshot = await self._persist_queue.get()
            # Coalesce: skip stale queued snapshots, keep the newest.
            while not self._persist_queue.empty():
                try:
                    snapshot = self._persist_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            await self._write_snapshot(snapshot)
            self._persist_written = snapshot.get("_seq", self._persist_written)
            self._persist_queue.task_done()

    async def _write_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Read-modify-write one snapshot into the session's state.json."""
        payload = {k: v for k, v in snapshot.items() if k != "_seq"}
        state = await self._session_store.read_state(self._session_id)
        if state is None:
            return
        state.shared_state = payload
        await self._session_store.write_state(self._session_id, state)

    async def flush(self) -> None:
        """Wait until all queued snapshots have been persisted (for shutdown/tests)."""
        if self._persist_queue is None or self._persist_loop is None:
            return
        # Poll until the worker has written the newest enqueued snapshot.
        # (Queue.join cannot be used cross-loop: its waiter can register after
        # the final task_done, hanging forever.)
        deadline = asyncio.get_running_loop().time() + 10
        while self._persist_written < self._persist_seq:
            if asyncio.get_running_loop().time() > deadline:
                raise TimeoutError("timed out waiting for shared state to persist")
            await asyncio.sleep(0.01)

    def close(self) -> None:
        """Stop the persistence worker and its background loop (for shutdown)."""
        if self._persist_loop is None or self._persist_thread is None:
            return
        loop = self._persist_loop
        worker = self._persist_worker
        if worker is not None and not worker.done():
            loop.call_soon_threadsafe(worker.cancel)
            # Run the loop until the cancelled worker has fully finished.
            import time as _time

            deadline = _time.monotonic() + 5
            while not worker.done():
                if _time.monotonic() > deadline:
                    break
                try:
                    asyncio.run_coroutine_threadsafe(asyncio.sleep(0.01), loop).result(timeout=1)
                except Exception:
                    break
        loop.call_soon_threadsafe(loop.stop)
        self._persist_thread.join(timeout=5)
        self._persist_thread = None
        self._persist_loop = None
        self._persist_queue = None
        self._persist_worker_task = None
        self._persist_worker = None

    @staticmethod
    def _run_async(coro) -> Any:
        """Run a coroutine to completion when no loop is running (init path)."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        # A loop is running but we must block: run in a worker thread.
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()

    def create_memory(
        self,
        execution_id: str,
        stream_id: str,
        isolation: IsolationLevel,
    ) -> "StreamMemory":
        """Create a memory instance for an execution"""
        # Initialize execution state
        if execution_id not in self._execution_state:
            self._execution_state[execution_id] = {}

        # Initialize stream state
        if stream_id not in self._stream_state:
            self._stream_state[stream_id] = {}
            self._stream_locks[stream_id] = asyncio.Lock()

        return StreamMemory(
            manager=self,
            execution_id=execution_id,
            stream_id=stream_id,
            isolation=isolation,
        )

    def cleanup_execution(self, execution_id: str) -> None:
        """Clean up state for a completed execution"""
        self._execution_state.pop(execution_id, None)
        self._persist()
        logger.debug(f"Cleaned up state for execution: {execution_id}")

    def cleanup_stream(self, stream_id: str) -> None:
        """Clean up state for a closed stream"""
        self._stream_state.pop(stream_id, None)
        self._stream_locks.pop(stream_id, None)
        self._persist()
        logger.debug(f"Cleaned up state for stream: {stream_id}")

    # === LOW-LEVEL STATE OPERATIONS ===

    async def read(
        self,
        key: str,
        execution_id: str,
        stream_id: str,
        isolation: IsolationLevel,
    ) -> Any:
        """Read a value respecting isolation level"""
        # Always check execution-local first
        if execution_id in self._execution_state:
            if key in self._execution_state[execution_id]:
                return self._execution_state[execution_id][key]

        # Check stream-level (unless isolated)
        if isolation != IsolationLevel.ISOLATED:
            if stream_id in self._stream_state:
                if key in self._stream_state[stream_id]:
                    return self._stream_state[stream_id][key]

            # Check global
            if key in self._global_state:
                return self._global_state[key]

        return None

    async def write(
        self,
        key: str,
        value: Any,
        execution_id: str,
        stream_id: str,
        isolation: IsolationLevel,
        scope: StateScope = StateScope.EXECUTION,
    ) -> None:
        """Write a value respecting isolation level"""
        # Get old value for change tracking
        old_value = await self.read(key, execution_id, stream_id, isolation)

        # ISOLATED can only write to execution scope
        if isolation == IsolationLevel.ISOLATED:
            scope = StateScope.EXECUTION

        # SYNCHRONIZED requires locks for stream/global writes
        if isolation == IsolationLevel.SYNCHRONIZED and scope != StateScope.EXECUTION:
            await self._write_with_lock(key, value, execution_id, stream_id, scope)
        else:
            await self._write_direct(key, value, execution_id, stream_id, scope)

        # Record change
        self._record_change(
            StateChange(
                key=key,
                old_value=old_value,
                new_value=value,
                scope=scope,
                execution_id=execution_id,
                stream_id=stream_id,
            )
        )

    async def _write_direct(
        self,
        key: str,
        value: Any,
        execution_id: str,
        stream_id: str,
        scope: StateScope,
    ) -> None:
        """Write without locking (for ISOLATED and SHARED)"""
        if scope == StateScope.EXECUTION:
            if execution_id not in self._execution_state:
                self._execution_state[execution_id] = {}
            self._execution_state[execution_id][key] = value

        elif scope == StateScope.STREAM:
            if stream_id not in self._stream_state:
                self._stream_state[stream_id] = {}
            self._stream_state[stream_id][key] = value

        elif scope == StateScope.GLOBAL:
            self._global_state[key] = value

        self._version += 1
        self._persist()

    async def _write_with_lock(
        self,
        key: str,
        value: Any,
        execution_id: str,
        stream_id: str,
        scope: StateScope,
    ) -> None:
        """Write with locking (for SYNCHRONIZED)"""
        lock = self._get_lock(scope, key, stream_id)
        async with lock:
            await self._write_direct(key, value, execution_id, stream_id, scope)

    def _get_lock(self, scope: StateScope, key: str, stream_id: str) -> asyncio.Lock:
        """Get appropriate lock for scope and key"""
        if scope == StateScope.GLOBAL:
            lock_key = f"global:{key}"
        elif scope == StateScope.STREAM:
            lock_key = f"stream:{stream_id}:{key}"
        else:
            lock_key = f"exec:{key}"

        if lock_key not in self._key_locks:
            self._key_locks[lock_key] = asyncio.Lock()

        return self._key_locks[lock_key]

    def _record_change(self, change: StateChange) -> None:
        """Record a state change for auditing"""
        self._change_history.append(change)

        # Trim history if too long
        if len(self._change_history) > self._max_history:
            self._change_history = self._change_history[-self._max_history :]

    # === BULK OPERATIONS ===

    async def read_all(
        self,
        execution_id: str,
        stream_id: str,
        isolation: IsolationLevel,
    ) -> dict[str, Any]:
        """Read all visible state for an execution"""
        result = {}

        # Start with global (if visible)
        if isolation != IsolationLevel.ISOLATED:
            result.update(self._global_state)

            # Add stream state (overwrites global)
            if stream_id in self._stream_state:
                result.update(self._stream_state[stream_id])

        # Add execution state (overwrites all)
        if execution_id in self._execution_state:
            result.update(self._execution_state[execution_id])

        return result

    async def write_batch(
        self,
        updates: dict[str, Any],
        execution_id: str,
        stream_id: str,
        isolation: IsolationLevel,
        scope: StateScope = StateScope.EXECUTION,
    ) -> None:
        """Write multiple values atomically"""
        for key, value in updates.items():
            await self.write(key, value, execution_id, stream_id, isolation, scope)

    # === UTILITY ===

    def get_stats(self) -> dict:
        """Get state manager statistics"""
        return {
            "global_keys": len(self._global_state),
            "stream_count": len(self._stream_state),
            "execution_count": len(self._execution_state),
            "total_changes": len(self._change_history),
            "version": self._version,
        }

    def get_recent_changes(self, limit: int = 10) -> list[StateChange]:
        """Get recent state changes"""
        return self._change_history[-limit:]


class StreamMemory:
    """Memory interface for a single execution"""

    def __init__(
        self,
        manager: SharedStateManager,
        execution_id: str,
        stream_id: str,
        isolation: IsolationLevel,
    ):
        self._manager = manager
        self._execution_id = execution_id
        self._stream_id = stream_id
        self._isolation = isolation

        # Permission model (optional, for node-level scoping)
        self._allowed_read: set[str] | None = None
        self._allowed_write: set[str] | None = None

    def with_permissions(
        self,
        read_keys: list[str],
        write_keys: list[str],
    ) -> "StreamMemory":
        """Create a scoped view with read/write permissions"""
        scoped = StreamMemory(
            manager=self._manager,
            execution_id=self._execution_id,
            stream_id=self._stream_id,
            isolation=self._isolation,
        )
        scoped._allowed_read = set(read_keys)
        scoped._allowed_write = set(write_keys)
        return scoped

    async def read(self, key: str) -> Any:
        """Read a value from state"""
        # Check permissions
        if self._allowed_read is not None and key not in self._allowed_read:
            raise PermissionError(f"Not allowed to read key: {key}")

        return await self._manager.read(
            key=key,
            execution_id=self._execution_id,
            stream_id=self._stream_id,
            isolation=self._isolation,
        )

    async def write(
        self,
        key: str,
        value: Any,
        scope: StateScope = StateScope.EXECUTION,
    ) -> None:
        """Write a value to state"""
        # Check permissions
        if self._allowed_write is not None and key not in self._allowed_write:
            raise PermissionError(f"Not allowed to write key: {key}")

        await self._manager.write(
            key=key,
            value=value,
            execution_id=self._execution_id,
            stream_id=self._stream_id,
            isolation=self._isolation,
            scope=scope,
        )

    async def read_all(self) -> dict[str, Any]:
        """Read all visible state"""
        all_state = await self._manager.read_all(
            execution_id=self._execution_id,
            stream_id=self._stream_id,
            isolation=self._isolation,
        )

        # Filter by permissions if set
        if self._allowed_read is not None:
            return {k: v for k, v in all_state.items() if k in self._allowed_read}

        return all_state

    # === SYNC API (for backward compatibility with SharedMemory) ===

    def read_sync(self, key: str) -> Any:
        """Synchronous read (for compatibility with existing code)"""
        # Direct access for sync usage
        if self._allowed_read is not None and key not in self._allowed_read:
            raise PermissionError(f"Not allowed to read key: {key}")

        # Check execution state
        exec_state = self._manager._execution_state.get(self._execution_id, {})
        if key in exec_state:
            return exec_state[key]

        # Check stream/global if not isolated
        if self._isolation != IsolationLevel.ISOLATED:
            stream_state = self._manager._stream_state.get(self._stream_id, {})
            if key in stream_state:
                return stream_state[key]

            if key in self._manager._global_state:
                return self._manager._global_state[key]

        return None

    def write_sync(self, key: str, value: Any) -> None:
        """Synchronous write (for compatibility with existing code)"""
        if self._allowed_write is not None and key not in self._allowed_write:
            raise PermissionError(f"Not allowed to write key: {key}")

        if self._execution_id not in self._manager._execution_state:
            self._manager._execution_state[self._execution_id] = {}

        self._manager._execution_state[self._execution_id][key] = value
        self._manager._version += 1
        self._manager._persist()

    def read_all_sync(self) -> dict[str, Any]:
        """Synchronous read all"""
        result = {}

        # Global (if visible)
        if self._isolation != IsolationLevel.ISOLATED:
            result.update(self._manager._global_state)
            if self._stream_id in self._manager._stream_state:
                result.update(self._manager._stream_state[self._stream_id])

        # Execution
        if self._execution_id in self._manager._execution_state:
            result.update(self._manager._execution_state[self._execution_id])

        # Filter by permissions
        if self._allowed_read is not None:
            result = {k: v for k, v in result.items() if k in self._allowed_read}

        return result
