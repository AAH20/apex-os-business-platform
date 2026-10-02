"""Thread-safe in-memory cache with TTL support."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Optional


class MemoryCache:
    """LRU in-memory cache with per-entry TTL and max-size eviction."""

    def __init__(self, max_size: int = 1024, default_ttl: int = 300) -> None:
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get a value. Returns None if missing or expired. Refreshes LRU order."""
        with self._lock:
            if key not in self._store:
                return None
            value, expires_at = self._store[key]
            if time.monotonic() >= expires_at:
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return value

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """Store a value with an optional TTL (seconds)."""
        expire = ttl if ttl is not None else self._default_ttl
        expires_at = time.monotonic() + expire
        with self._lock:
            if key in self._store:
                del self._store[key]
            self._store[key] = (value, expires_at)
            self._store.move_to_end(key)
            self._evict_if_needed()

    def delete(self, key: str) -> bool:
        """Delete a key. Returns True if it existed."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        """Check if a key exists and is not expired."""
        with self._lock:
            if key not in self._store:
                return False
            _, expires_at = self._store[key]
            if time.monotonic() >= expires_at:
                del self._store[key]
                return False
            return True

    def ttl(self, key: str) -> int:
        """Return remaining TTL in seconds. -2 if missing, -1 if no expiry."""
        with self._lock:
            if key not in self._store:
                return -2
            _, expires_at = self._store[key]
            remaining = expires_at - time.monotonic()
            if remaining <= 0:
                del self._store[key]
                return -2
            return int(remaining)

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._store.clear()

    def keys(self) -> list[str]:
        """Return all non-expired keys."""
        with self._lock:
            now = time.monotonic()
            expired = [k for k, (_, exp) in self._store.items() if now >= exp]
            for k in expired:
                del self._store[k]
            return list(self._store.keys())

    def size(self) -> int:
        """Return the number of entries (including not-yet-evicted expired ones)."""
        with self._lock:
            return len(self._store)

    def _evict_if_needed(self) -> None:
        """Evict oldest entries if over capacity. Must be called under lock."""
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def get_or_set(
        self,
        key: str,
        factory: callable,
        ttl: Optional[int] = None,
    ) -> Any:
        """Get a value or compute and store it if missing."""
        value = self.get(key)
        if value is not None:
            return value
        value = factory()
        self.set(key, value, ttl=ttl)
        return value
