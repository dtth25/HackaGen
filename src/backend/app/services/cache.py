"""Simple in-memory thread-safe cache service."""

import time
from threading import Lock
from typing import Any, Dict, Optional


class InMemoryCache:
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self):
        self._store: Dict[str, tuple[Any, Optional[float]]] = {}
        self._lock = Lock()

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        with self._lock:
            expire_at = time.time() + ttl_seconds if ttl_seconds is not None else None
            self._store[key] = (value, expire_at)

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._store:
                return None
            value, expire_at = self._store[key]
            if expire_at is not None and time.time() > expire_at:
                del self._store[key]
                return None
            return value

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def exists(self, key: str) -> bool:
        return self.get(key) is not None


# Global cache instance for token blacklisting and general usage
cache = InMemoryCache()
