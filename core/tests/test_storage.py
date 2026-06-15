"""Tests for storage cache helpers."""

import time

from engine.storage.concurrent import CacheEntry


class TestCacheEntry:
    def test_is_expired_false_when_fresh(self):
        entry = CacheEntry(value="test", timestamp=time.time())
        assert entry.is_expired(ttl=60.0) is False

    def test_is_expired_true_when_old(self):
        entry = CacheEntry(value="test", timestamp=time.time() - 120)
        assert entry.is_expired(ttl=60.0) is True
