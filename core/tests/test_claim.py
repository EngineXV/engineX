import threading
import time
from datetime import datetime
from pathlib import Path

import pytest

from engine.schemas.session_state import SessionState, SessionTimestamps
from engine.storage.session_store import SessionStore


@pytest.fixture
def store(tmp_path: Path) -> SessionStore:
    return SessionStore(tmp_path)


@pytest.fixture
def session_state() -> SessionState:
    now = datetime.utcnow().isoformat()
    return SessionState(
        session_id="test-session",
        graph_name="test",
        goal_id="test-goal",
        timestamps=SessionTimestamps(
            created_at=now,
            updated_at=now,
            started_at=now,  # required field
        ),
    )


def test_claim_success(store: SessionStore, session_state: SessionState):
    store.write_state_sync("test-session", session_state)  # now exists
    from engine.worker.claim import ClaimManager

    mgr = ClaimManager(store)
    assert mgr.try_claim("test-session", "worker1") is True
    state = store.read_state_sync("test-session")
    assert state.claimed_by == "worker1"
    assert state.claimed_at is not None


def test_claim_reject_if_already_claimed(store: SessionStore, session_state: SessionState):
    store.write_state_sync("test-session", session_state)
    from engine.worker.claim import ClaimManager

    mgr = ClaimManager(store)
    assert mgr.try_claim("test-session", "worker1") is True
    assert mgr.try_claim("test-session", "worker2") is False


def test_claim_expires(store: SessionStore, session_state: SessionState):
    store.write_state_sync("test-session", session_state)
    from engine.worker.claim import ClaimManager

    mgr = ClaimManager(store)
    assert mgr.try_claim("test-session", "worker1", ttl_seconds=0) is True
    time.sleep(0.01)
    assert mgr.try_claim("test-session", "worker2", ttl_seconds=0) is True


def test_release(store: SessionStore, session_state: SessionState):
    store.write_state_sync("test-session", session_state)
    from engine.worker.claim import ClaimManager

    mgr = ClaimManager(store)
    assert mgr.try_claim("test-session", "worker1") is True
    assert mgr.release("test-session", "worker1") is True
    state = store.read_state_sync("test-session")
    assert state.claimed_by is None
    assert state.claimed_at is None
    assert mgr.release("test-session", "worker2") is False


def test_concurrent_claims(store: SessionStore, session_state: SessionState):
    store.write_state_sync("test-session", session_state)
    from engine.worker.claim import ClaimManager

    mgr = ClaimManager(store)
    results = []

    def claim_worker(worker_id):
        time.sleep(0.05)
        results.append(mgr.try_claim("test-session", worker_id))

    threads = [threading.Thread(target=claim_worker, args=(f"w{i}",)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sum(results) == 1
