from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar('T')


@dataclass
class CacheItem(Generic[T]):
    value: T
    expires_at: float


class TTLCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, CacheItem[object]] = {}

    def get_or_set(self, key: str, producer: Callable[[], T]) -> T:
        now = time.time()
        item = self._store.get(key)
        if item and item.expires_at > now:
            return item.value  # type: ignore[return-value]
        value = producer()
        self._store[key] = CacheItem(value=value, expires_at=now + self.ttl_seconds)
        return value

    def clear(self) -> None:
        self._store.clear()
