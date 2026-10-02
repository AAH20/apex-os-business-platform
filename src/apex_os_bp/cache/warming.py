"""Cache warming strategies — pre-populate cache before it's needed."""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Iterable, Optional

from .memory_cache import MemoryCache
from .redis_cache import RedisCache

logger = logging.getLogger(__name__)


class CacheWarmer:
    """Warms cache entries from a data source."""

    def __init__(
        self,
        backend: Any,
        max_workers: int = 4,
    ) -> None:
        self._backend = backend
        self._max_workers = max_workers

    def warm_entry(
        self,
        key: str,
        loader: Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """Warm a single cache entry by loading and storing its value."""
        try:
            value = loader()
            if hasattr(self._backend, "set"):
                self._backend.set(key, value, ttl=ttl)
            return True
        except Exception as exc:
            logger.warning("Failed to warm cache entry %s: %s", key, exc)
            return False

    def warm_entries(
        self,
        loaders: dict[str, Callable[[], Any]],
        ttl: Optional[int] = None,
    ) -> dict[str, bool]:
        """Warm multiple entries in parallel. Returns per-key success status."""
        results: dict[str, bool] = {}
        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {
                pool.submit(self.warm_entry, key, loader, ttl): key
                for key, loader in loaders.items()
            }
            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception as exc:
                    logger.warning("Failed to warm cache entry %s: %s", key, exc)
                    results[key] = False
        return results

    def warm_from_iterable(
        self,
        items: Iterable[tuple[str, Any]],
        ttl: Optional[int] = None,
    ) -> int:
        """Warm cache from an iterable of (key, value) pairs. Returns count stored."""
        count = 0
        for key, value in items:
            try:
                self._backend.set(key, value, ttl=ttl)
                count += 1
            except Exception as exc:
                logger.warning("Failed to warm cache entry %s: %s", key, exc)
        return count

    def warm_with_refresh(
        self,
        key: str,
        loader: Callable[[], Any],
        ttl: int,
        refresh_threshold: float = 0.8,
    ) -> bool:
        """Warm an entry, refreshing if the remaining TTL is below the threshold."""
        remaining = self._backend.ttl(key) if hasattr(self._backend, "ttl") else -2
        if remaining == -2 or remaining < ttl * refresh_threshold:
            return self.warm_entry(key, loader, ttl=ttl)
        return True

    def schedule_warming(
        self,
        key: str,
        loader: Callable[[], Any],
        interval: int,
        ttl: Optional[int] = None,
        immediate: bool = True,
    ) -> threading.Event:
        """Schedule periodic cache warming in a background thread.

        Returns a threading.Event that can be set to stop the warming loop.
        """
        stop_event = threading.Event()

        def _loop() -> None:
            if immediate:
                self.warm_entry(key, loader, ttl=ttl)
            while not stop_event.wait(interval):
                self.warm_entry(key, loader, ttl=ttl)

        thread = threading.Thread(target=_loop, daemon=True, name=f"cache-warmer-{key}")
        thread.start()
        return stop_event


class WarmingScheduler:
    """Manages scheduled warming jobs for multiple cache entries."""

    def __init__(self, warmer: CacheWarmer) -> None:
        self._warmer = warmer
        self._stop_events: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def schedule(
        self,
        key: str,
        loader: Callable[[], Any],
        interval: int,
        ttl: Optional[int] = None,
        immediate: bool = True,
    ) -> None:
        """Schedule a warming job, replacing any existing job for the same key."""
        with self._lock:
            if key in self._stop_events:
                self._stop_events[key].set()
            stop_event = self._warmer.schedule_warming(
                key, loader, interval, ttl=ttl, immediate=immediate
            )
            self._stop_events[key] = stop_event

    def cancel(self, key: str) -> bool:
        """Cancel a scheduled warming job. Returns True if one was running."""
        with self._lock:
            event = self._stop_events.pop(key, None)
            if event is not None:
                event.set()
                return True
            return False

    def cancel_all(self) -> None:
        """Cancel all scheduled warming jobs."""
        with self._lock:
            for event in self._stop_events.values():
                event.set()
            self._stop_events.clear()
