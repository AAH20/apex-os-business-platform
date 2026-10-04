"""Cache statistics collection and reporting."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class CacheStatsSnapshot:
    """Immutable snapshot of cache statistics at a point in time."""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    total_latency_ms: float = 0.0
    operations: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        total = self.hits + self.misses
        return self.misses / total if total > 0 else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.operations if self.operations > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "evictions": self.evictions,
            "hit_rate": self.hit_rate,
            "miss_rate": self.miss_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "operations": self.operations,
        }


class CacheStats:
    """Thread-safe cache statistics collector."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._deletes = 0
        self._evictions = 0
        self._total_latency_ms = 0.0
        self._operations = 0
        self._started_at = time.monotonic()

    def record_hit(self, latency_ms: float = 0.0) -> None:
        """Record a cache hit."""
        with self._lock:
            self._hits += 1
            self._operations += 1
            self._total_latency_ms += latency_ms

    def record_miss(self, latency_ms: float = 0.0) -> None:
        """Record a cache miss."""
        with self._lock:
            self._misses += 1
            self._operations += 1
            self._total_latency_ms += latency_ms

    def record_set(self, latency_ms: float = 0.0) -> None:
        """Record a cache set operation."""
        with self._lock:
            self._sets += 1
            self._operations += 1
            self._total_latency_ms += latency_ms

    def record_delete(self, latency_ms: float = 0.0) -> None:
        """Record a cache delete operation."""
        with self._lock:
            self._deletes += 1
            self._operations += 1
            self._total_latency_ms += latency_ms

    def record_eviction(self) -> None:
        """Record a cache eviction."""
        with self._lock:
            self._evictions += 1

    def record_operation(self, latency_ms: float = 0.0) -> None:
        """Record a generic operation."""
        with self._lock:
            self._operations += 1
            self._total_latency_ms += latency_ms

    def get_stats(self) -> CacheStatsSnapshot:
        """Return an immutable snapshot of current statistics."""
        with self._lock:
            return CacheStatsSnapshot(
                hits=self._hits,
                misses=self._misses,
                sets=self._sets,
                deletes=self._deletes,
                evictions=self._evictions,
                total_latency_ms=self._total_latency_ms,
                operations=self._operations,
            )

    def reset(self) -> None:
        """Reset all statistics to zero."""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._sets = 0
            self._deletes = 0
            self._evictions = 0
            self._total_latency_ms = 0.0
            self._operations = 0
            self._started_at = time.monotonic()

    @property
    def uptime_seconds(self) -> float:
        """Return the number of seconds since stats collection started."""
        return time.monotonic() - self._started_at

    def summary(self) -> dict[str, Any]:
        """Return a summary dict including derived metrics."""
        snapshot = self.get_stats()
        data = snapshot.to_dict()
        data["uptime_seconds"] = self.uptime_seconds
        return data


class StatsCacheWrapper:
    """Wraps a cache backend and records statistics for all operations."""

    def __init__(self, backend: Any, stats: Optional[CacheStats] = None) -> None:
        self._backend = backend
        self._stats = stats or CacheStats()

    @property
    def stats(self) -> CacheStats:
        return self._stats

    def get(self, key: str) -> Optional[Any]:
        start = time.monotonic()
        result = self._backend.get(key)
        elapsed_ms = (time.monotonic() - start) * 1000
        if result is not None:
            self._stats.record_hit(elapsed_ms)
        else:
            self._stats.record_miss(elapsed_ms)
        return result

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        start = time.monotonic()
        result = self._backend.set(key, value, ttl=ttl)
        elapsed_ms = (time.monotonic() - start) * 1000
        self._stats.record_set(elapsed_ms)
        return result

    def delete(self, key: str) -> bool:
        start = time.monotonic()
        result = self._backend.delete(key)
        elapsed_ms = (time.monotonic() - start) * 1000
        self._stats.record_delete(elapsed_ms)
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._backend, name)
