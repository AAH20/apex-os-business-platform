"""Cache invalidation strategies and tag-based invalidation."""

from __future__ import annotations

from typing import Any, Callable, Iterable, Optional, Protocol



class CacheBackend(Protocol):
    """Protocol for cache backends that support basic operations."""

    def get(self, key: str) -> Optional[Any]: ...
    def delete(self, key: str) -> bool: ...
    def keys(self, pattern: str = "*") -> list[str]: ...
    def flush(self) -> bool: ...


class CacheInvalidator:
    """Invalidates cache entries by key, pattern, tag, or callback."""

    def __init__(self, backend: CacheBackend) -> None:
        self._backend = backend
        self._tag_index: dict[str, set[str]] = {}

    def invalidate(self, key: str) -> bool:
        """Invalidate a single cache entry."""
        self._remove_from_tags(key)
        return self._backend.delete(key)

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a glob pattern. Returns count removed."""
        matching = self._backend.keys(pattern=pattern)
        count = 0
        for key in matching:
            if self._backend.delete(key):
                count += 1
                self._remove_from_tags(key)
        return count

    def invalidate_tags(self, tags: Iterable[str]) -> int:
        """Invalidate all entries associated with any of the given tags."""
        keys_to_invalidate: set[str] = set()
        for tag in tags:
            keys_to_invalidate.update(self._tag_index.get(tag, set()))
        count = 0
        for key in keys_to_invalidate:
            if self._backend.delete(key):
                count += 1
        # Clean up tag index
        for tag in tags:
            self._tag_index.pop(tag, None)
        return count

    def invalidate_all(self) -> bool:
        """Flush the entire cache."""
        self._tag_index.clear()
        return self._backend.flush()

    def register_tag(self, key: str, tag: str) -> None:
        """Associate a cache key with a tag for later invalidation."""
        if tag not in self._tag_index:
            self._tag_index[tag] = set()
        self._tag_index[tag].add(key)

    def register_tags(self, key: str, tags: Iterable[str]) -> None:
        """Associate a cache key with multiple tags."""
        for tag in tags:
            self.register_tag(key, tag)

    def _remove_from_tags(self, key: str) -> None:
        """Remove a key from the tag index."""
        for tag_keys in self._tag_index.values():
            tag_keys.discard(key)

    def invalidate_with_callback(
        self,
        key: str,
        callback: Callable[[], Any],
    ) -> Any:
        """Invalidate a key then execute a callback. Returns the callback result."""
        self.invalidate(key)
        return callback()

    def invalidate_conditional(
        self,
        key: str,
        condition: Callable[[Any], bool],
    ) -> bool:
        """Invalidate a key only if the current value satisfies the condition."""
        value = self._backend.get(key)
        if value is not None and condition(value):
            return self.invalidate(key)
        return False


class MultiLevelInvalidator:
    """Invalidates across multiple cache tiers (e.g., memory + Redis)."""

    def __init__(self, *backends: CacheBackend) -> None:
        self._backends = list(backends)
        self._invalidators = [CacheInvalidator(b) for b in backends]

    def invalidate(self, key: str) -> bool:
        """Invalidate a key across all tiers. Returns True if any tier had the key."""
        results = [inv.invalidate(key) for inv in self._invalidators]
        return any(results)

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate matching keys across all tiers. Returns total count."""
        return sum(inv.invalidate_pattern(pattern) for inv in self._invalidators)

    def invalidate_all(self) -> bool:
        """Flush all tiers."""
        results = [inv.invalidate_all() for inv in self._invalidators]
        return all(results)

    def register_tag(self, key: str, tag: str) -> None:
        """Register a tag on all tiers."""
        for inv in self._invalidators:
            inv.register_tag(key, tag)
