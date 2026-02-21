"""Unit tests for the TTL cache."""

import time

from app.services.cache import TTLCache


class TestTTLCache:
    def test_set_and_get(self):
        cache = TTLCache(default_ttl=10)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_expired_entry_returns_none(self):
        cache = TTLCache(default_ttl=1)
        cache.set("key1", "value1", ttl=0)
        # TTL of 0 means it expires immediately (at the same second)
        time.sleep(0.1)
        assert cache.get("key1") is None

    def test_custom_ttl_per_key(self):
        cache = TTLCache(default_ttl=1)
        cache.set("short", "val", ttl=0)
        cache.set("long", "val", ttl=60)
        time.sleep(0.1)
        assert cache.get("short") is None
        assert cache.get("long") == "val"

    def test_invalidate_all(self):
        cache = TTLCache(default_ttl=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.invalidate()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_invalidate_by_prefix(self):
        cache = TTLCache(default_ttl=60)
        cache.set("ns:list", ["a", "b"])
        cache.set("ns:summary:default", {"health": "ok"})
        cache.set("pod:default:test", {"name": "test"})
        cache.invalidate("ns:")
        assert cache.get("ns:list") is None
        assert cache.get("ns:summary:default") is None
        assert cache.get("pod:default:test") == {"name": "test"}

    def test_overwrite_value(self):
        cache = TTLCache(default_ttl=60)
        cache.set("key", "old")
        cache.set("key", "new")
        assert cache.get("key") == "new"

    def test_get_nonexistent_key(self):
        cache = TTLCache(default_ttl=60)
        assert cache.get("missing") is None
