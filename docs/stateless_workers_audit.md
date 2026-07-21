# Stateless Workers – In‑memory State Audit

This document lists the in‑memory state in the EngineX runtime that must be
externalised for stateless, horizontally‑scalable workers.

## Methodology

Every module under `core/engine/runtime/`, `core/engine/runner/`, and
`core/engine/server/` was inspected for state that is not persisted to
`ENGINE_HOME` (or another durable store) on every change.

---

## 1. AgentRuntime (`core/engine/runtime/agent_runtime.py`)

| State | Location | Persisted? | Notes |
|-------|----------|------------|-------|
| `_entry_points` (dict) | `AgentRuntime.__init__` | ❌ | Registered entry points are held in memory only. |
| `_streams` (dict of `ExecutionStream`) | `AgentRuntime.__init__` | ❌ | Active execution streams. |
| `_timer_tasks` (list) | `AgentRuntime.__init__` | ❌ | Timer tasks for interval/cron entry points. |
| `_running` (bool) | `AgentRuntime.__init__` | ❌ | Lifecycle flag. |

---

## 2. ExecutionStream (`core/engine/runtime/execution_stream.py`)

| State | Location | Persisted? | Notes |
|-------|----------|------------|-------|
| `_execution_tasks` (dict) | `ExecutionStream.__init__` | ❌ | Active asyncio tasks. |
| `_pending` (list) | `ExecutionStream.__init__` | ❌ | Queued execution requests. |
| `_paused_nodes` (dict) | `ExecutionStream.__init__` | ❌ | Nodes waiting for human input. |
| `_current_node_id` | `ExecutionStream.__init__` | ❌ | The node currently being executed. |

---

## 3. SharedStateManager (`core/engine/runtime/shared_state.py`)

| State | Location | Persisted? | Notes |
|-------|----------|------------|-------|
| `_memory` (dict) | `SharedStateManager.__init__` | ❌ | Key‑value store shared across nodes. |
| `_locks` (dict) | `SharedStateManager.__init__` | ❌ | Threading locks. |

---

## 4. EventBus (`core/engine/runtime/event_bus.py`)

| State | Location | Persisted? | Notes |
|-------|----------|------------|-------|
| `_subscribers` (dict) | `EventBus.__init__` | ❌ | Event subscription callbacks. |
| `_streams` (dict) | `EventBus.__init__` | ❌ | Async queues for stream‑based subscribers. |

---

## 5. SessionStore (`core/engine/storage/session_store.py`)

| State | Location | Persisted? | Notes |
|-------|----------|------------|-------|
| Session metadata | `sessions/{id}/state.json` | ✅ | Already persisted. |
| Node outputs | `sessions/{id}/state.json` | ✅ | Already persisted. |
| Checkpoint data | `sessions/{id}/checkpoint.json` | ✅ | Already persisted. |

---

## 6. CheckpointStore (`core/engine/storage/checkpoint_store.py`)

| State | Location | Persisted? | Notes |
|-------|----------|------------|-------|
| Checkpoint records | `sessions/{id}/checkpoint.json` | ✅ | Already persisted. |

---

## Summary

**What is already persisted:** session metadata, node outputs, checkpoint data.

**What is in‑memory only (needs externalisation):**
- Entry point registrations
- Active execution streams and their task queues
- Timer task handles
- Shared memory (`SharedStateManager`)
- Event bus subscriptions
- Worker claim/lock state

---

## Next steps

1. Design a claim‑based worker API so any process can pick up a pending session.
2. Externalise `SharedStateManager` to the session store.
3. Store pending and paused execution state in the session store so a new
   worker can resume execution.
4. Write a kill‑and‑resume integration test.

This audit follows Issue #46.
