"""Simple in-memory TTL cache to reduce Kubernetes API calls."""

from __future__ import annotations

import time
from typing import Any


class TTLCache:
    """Thread-safe-ish in-memory cache with per-key TTL."""

    def __init__(self, default_ttl: int = 15):
        self._store: dict[str, tuple[float, Any]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        t = ttl if ttl is not None else self._default_ttl
        self._store[key] = (time.time() + t, value)

    def invalidate(self, prefix: str = "") -> None:
        """Remove all keys starting with prefix, or all if empty."""
        if not prefix:
            self._store.clear()
        else:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]


cache = TTLCache()
