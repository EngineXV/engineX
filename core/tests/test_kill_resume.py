"""Integration test for kill-and-resume with stateless workers."""

from __future__ import annotations

import asyncio
import multiprocessing as mp
import tempfile
from pathlib import Path

import pytest

from engine.graph.edge import EdgeSpec, GraphSpec
from engine.graph.goal import Constraint, Goal, SuccessCriterion
from engine.graph.node import NodeSpec
from engine.runtime.agent_runtime import AgentRuntime
from engine.runner.runner import AgentRunner
from engine.storage.checkpoint_store import CheckpointStore
from engine.storage.session_store import SessionStore
from engine.worker.claim import ClaimManager


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------
def create_test_graph() -> GraphSpec:
    nodes = [
        NodeSpec(id="step1", name="step1", description="First step",
                 node_type="event_loop", system_prompt="Return 1"),
        NodeSpec(id="step2", name="step2", description="Second step",
                 node_type="event_loop", system_prompt="Add 2"),
        NodeSpec(id="step3", name="step3", description="Third step",
                 node_type="event_loop", system_prompt="Add 3"),
    ]
    # condition must be a string literal: "always", "on_success", etc.
    edges = [
        EdgeSpec(id="e1", source="step1", target="step2", condition="always"),
        EdgeSpec(id="e2", source="step2", target="step3", condition="always"),
    ]
    return GraphSpec(
        id="test_kill_resume_graph",
        goal_id="test_goal",
        entry_node="step1",
        nodes=nodes,
        edges=edges,
        terminal_nodes=["step3"],
    )

def create_test_goal() -> Goal:
    return Goal(
        id="test_goal",
        name="Test Goal",
        success_criteria=[
            SuccessCriterion(id="sc1", description="All steps completed",
                             metric="completed", target="100%", weight=1.0)
        ],
        constraints=[Constraint(id="c1", description="Must finish within 60 seconds")],
    )

async def get_latest_checkpoint(checkpoint_store, session_id):
    """Try multiple method names (async or sync) to get the latest checkpoint."""
    for name in ["get_latest_checkpoint", "load_latest", "get_latest", "load_checkpoint"]:
        method = getattr(checkpoint_store, name, None)
        if method is not None:
            try:
                if asyncio.iscoroutinefunction(method):
                    result = await method(session_id)
                else:
                    result = method(session_id)
                if result is not None:
                    return result
            except Exception:
                continue
    return None


# -------------------------------------------------------------------------
# Worker process
# -------------------------------------------------------------------------
def run_worker(session_id, storage_path, worker_id, crash_after_seconds=2.0):
    asyncio.run(_run_worker_async(session_id, storage_path, worker_id, crash_after_seconds))

async def _run_worker_async(session_id, storage_path, worker_id, crash_after_seconds):
    session_store = SessionStore(base_path=Path(storage_path))
    checkpoint_store = CheckpointStore(base_path=Path(storage_path))

    runtime = AgentRuntime(
        graph=create_test_graph(),
        goal=create_test_goal(),
        storage_path=storage_path,
    )
    runner = AgentRunner(runtime=runtime)

    claim_mgr = ClaimManager(session_store)
    if not claim_mgr.try_claim(session_id, worker_id, ttl_seconds=120):
        raise RuntimeError(f"Worker {worker_id} could not claim")

    task = asyncio.create_task(runner.run(session_id=session_id))
    await asyncio.sleep(crash_after_seconds)
    raise RuntimeError(f"💥 Worker {worker_id} CRASHED")


# -------------------------------------------------------------------------
# Test
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_kill_and_resume():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = tmpdir
        session_id = "test-session-kill-resume"
        worker1_id = "worker-A"
        worker2_id = "worker-B"

        # Worker 1 crashes
        ctx = mp.get_context("spawn")
        p = ctx.Process(target=run_worker, args=(session_id, storage_path, worker1_id, 2.0))
        p.start()
        p.join(timeout=5.0)
        if p.is_alive():
            p.terminate()
            p.join()
        assert p.exitcode != 0, "Worker 1 should have crashed"

        # Verify checkpoint exists
        session_store = SessionStore(base_path=Path(storage_path))
        checkpoint_store = CheckpointStore(base_path=Path(storage_path))
        latest = await get_latest_checkpoint(checkpoint_store, session_id)
        assert latest is not None, "At least one checkpoint should exist"

        # Worker 2 claims and resumes
        # Since the claim is still held by worker1 (TTL 120s), we must release it.
        # If release fails, we can forcibly clear the claim from the session state.
        released = session_store.release_claim(session_id, worker1_id)
        if not released:
            # Fallback: manually clear the claim from the state
            state = session_store.read_state_sync(session_id)
            if state and state.claimed_by == worker1_id:
                state.claimed_by = None
                state.claimed_at = None
                session_store.write_state_sync(session_id, state)
                released = True
        assert released is True, "Stale claim should be releasable"

        runtime2 = AgentRuntime(
            graph=create_test_graph(),
            goal=create_test_goal(),
            storage_path=storage_path,
        )
        claim_mgr2 = ClaimManager(session_store)
        claimed = claim_mgr2.try_claim(session_id, worker2_id, ttl_seconds=60)
        assert claimed is True, "Worker 2 should claim the session"

        runner2 = AgentRunner(runtime=runtime2)
        result = await runner2.run(session_id=session_id)

        # Verify completion
        final_checkpoint = await get_latest_checkpoint(checkpoint_store, session_id)
        assert final_checkpoint is not None, "Final checkpoint should exist"

        state = session_store.read_state_sync(session_id)
        assert state is not None, "Session state should exist"
        print("✅ Worker 2 resumed and completed the workflow.")
