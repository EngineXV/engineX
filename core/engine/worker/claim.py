"""Claim manager for stateless workers."""
from engine.storage.session_store import SessionStore

class ClaimManager:
    def __init__(self, session_store: SessionStore):
        self._store = session_store

    def try_claim(self, session_id: str, worker_id: str, ttl_seconds: int = 60) -> bool:
        return self._store.try_claim_session(session_id, worker_id, ttl_seconds)

    def release(self, session_id: str, worker_id: str) -> bool:
        return self._store.release_claim(session_id, worker_id)

    def is_claimed_by_me(self, session_id: str, worker_id: str) -> bool:
        state = self._store.read_state_sync(session_id)
        return state is not None and state.claimed_by == worker_id
