"""Redis-backed cache implementation."""

from __future__ import annotations

import json
import time
from typing import Any, Optional

try:
    import redis
except ImportError:
    redis = None  # type: ignore[assignment]


class RedisCache:
    """Redis cache with TTL, namespacing, and connection pooling."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        key_prefix: str = "apex",
        default_ttl: int = 3600,
        socket_timeout: float = 5.0,
    ) -> None:
        if redis is None:
            raise ImportError("redis package is required for RedisCache")
        self._client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            socket_timeout=socket_timeout,
            decode_responses=True,
        )
        self._prefix = key_prefix
        self._default_ttl = default_ttl

    def _make_key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from Redis. Returns None if not found or expired."""
        raw = self._client.get(self._make_key(key))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Store a value in Redis with an optional TTL (seconds)."""
        full_key = self._make_key(key)
        serialized = json.dumps(value)
        expire = ttl if ttl is not None else self._default_ttl
        return bool(self._client.set(full_key, serialized, ex=expire))

    def delete(self, key: str) -> bool:
        """Delete a key from Redis. Returns True if the key existed."""
        return bool(self._client.delete(self._make_key(key)))

    def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        return bool(self._client.exists(self._make_key(key)))

    def ttl(self, key: str) -> int:
        """Return remaining TTL in seconds, -2 if key doesn't exist, -1 if no expiry."""
        return int(self._client.ttl(self._make_key(key)))

    def flush(self) -> bool:
        """Flush all keys with the configured prefix."""
        pattern = f"{self._prefix}:*"
        keys = list(self._client.scan_iter(match=pattern))
        if keys:
            self._client.delete(*keys)
        return True

    def mget(self, keys: list[str]) -> dict[str, Optional[Any]]:
        """Batch-get multiple keys. Returns a dict of key -> value."""
        if not keys:
            return {}
        full_keys = [self._make_key(k) for k in keys]
        raw_values = self._client.mget(full_keys)
        result: dict[str, Optional[Any]] = {}
        for k, raw in zip(keys, raw_values):
            if raw is None:
                result[k] = None
            else:
                try:
                    result[k] = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    result[k] = raw
        return result

    def mset(self, mapping: dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Batch-set multiple key-value pairs."""
        if not mapping:
            return True
        expire = ttl if ttl is not None else self._default_ttl
        pipe = self._client.pipeline()
        for key, value in mapping.items():
            serialized = json.dumps(value)
            pipe.set(self._make_key(key), serialized, ex=expire)
        pipe.execute()
        return True

    def increment(self, key: str, amount: int = 1) -> int:
        """Atomically increment a counter."""
        return int(self._client.incrby(self._make_key(key), amount))

    def expire(self, key: str, seconds: int) -> bool:
        """Set or update the TTL on an existing key."""
        return bool(self._client.expire(self._make_key(key), seconds))

    def keys(self, pattern: str = "*") -> list[str]:
        """List keys matching a pattern (without prefix)."""
        full_pattern = f"{self._prefix}:{pattern}"
        raw_keys = list(self._client.scan_iter(match=full_pattern))
        prefix_len = len(self._prefix) + 1
        return [k[prefix_len:] for k in raw_keys]

    def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            return bool(self._client.ping())
        except Exception:
            return False

    def close(self) -> None:
        """Close the Redis connection."""
        self._client.close()
