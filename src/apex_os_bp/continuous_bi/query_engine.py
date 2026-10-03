"""Real-time query engine with TTL-based caching."""

import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Optional


class QueryCache:
    """Thread-safe LRU cache with TTL support."""

    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                expiry, value = self._cache[key]
                if time.time() < expiry:
                    self._cache.move_to_end(key)
                    return value
                del self._cache[key]
            return None

    def put(self, key: str, value: Any, ttl: float):
        with self._lock:
            self._cache[key] = (time.time() + ttl, value)
            self._cache.move_to_end(key)
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def invalidate(self, key: str):
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        with self._lock:
            self._cache.clear()


class QueryEngine:
    """Executes queries with caching and hook support."""

    def __init__(self, cache_size: int = 1000):
        self._cache = QueryCache(cache_size)
        self._hooks: list[Callable] = []

    def register_hook(self, hook: Callable[[str, Any], None]):
        self._hooks.append(hook)

    def execute(
        self,
        query_func: Callable[..., Any],
        cache_key: str,
        ttl: float = 60,
        **kwargs: Any,
    ) -> Any:
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        result = query_func(**kwargs)
        self._cache.put(cache_key, result, ttl)
        for hook in self._hooks:
            hook(cache_key, result)
        return result

    def invalidate(self, cache_key: str):
        self._cache.invalidate(cache_key)

    def clear_cache(self):
        self._cache.clear()
