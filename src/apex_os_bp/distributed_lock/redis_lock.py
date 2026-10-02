"""Redis-based distributed lock implementation.

Uses SET key value NX PX for atomic lock acquisition and Lua scripts
for safe release (verify token before deleting).
"""

from __future__ import annotations

import time
from typing import Any, Optional

from .base import BaseDistributedLock, LockMetadata, LockResult, LockStatus


# Lua script for safe release: only delete if token matches
_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

# Lua script for safe renewal: only extend if token matches
_RENEW_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("pexpire", KEYS[1], ARGV[2])
else
    return 0
end
"""


class RedisDistributedLock(BaseDistributedLock):
    """Distributed lock backed by Redis.

    Uses SET NX PX for atomic acquisition and Lua scripts for
    token-verified release and renewal.

    Example:
        >>> lock = RedisDistributedLock("my_resource", ttl_seconds=10)
        >>> result = lock.acquire(blocking=True, timeout=5.0)
        >>> if result.success:
        ...     try:
        ...         # critical section
        ...         pass
        ...     finally:
        ...         lock.release()
    """

    def __init__(
        self,
        lock_name: str,
        ttl_seconds: float = 30.0,
        owner: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        redis_client: Any = None,
        redis_url: Optional[str] = None,
        prefix: str = "apex:lock:",
    ) -> None:
        """Initialize Redis distributed lock.

        Args:
            lock_name: Unique name for the lock.
            ttl_seconds: Time-to-live in seconds.
            owner: Owner identifier (auto-generated if None).
            metadata: Additional metadata to store with the lock.
            redis_client: Existing redis.Redis client instance.
            redis_url: Redis connection URL (used if redis_client is None).
            prefix: Key prefix for Redis.
        """
        super().__init__(lock_name, ttl_seconds, owner, metadata)
        self._prefix = prefix
        self._redis = redis_client
        self._redis_url = redis_url
        self._release_script: Any = None
        self._renew_script: Any = None

        if self._redis is None:
            self._redis = self._create_redis_client()

        self._register_scripts()

    @property
    def redis_key(self) -> str:
        """Return the full Redis key for this lock."""
        return f"{self._prefix}{self._lock_name}"

    def _create_redis_client(self) -> Any:
        """Create a new Redis client from URL."""
        try:
            import redis  # type: ignore
        except ImportError:
            raise ImportError(
                "redis package is required for RedisDistributedLock. "
                "Install it with: pip install redis"
            )

        if self._redis_url:
            return redis.Redis.from_url(self._redis_url, decode_responses=True)
        return redis.Redis(decode_responses=True)

    def _register_scripts(self) -> None:
        """Register Lua scripts with Redis."""
        if self._redis is not None:
            self._release_script = self._redis.register_script(_RELEASE_SCRIPT)
            self._renew_script = self._redis.register_script(_RENEW_SCRIPT)

    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> LockResult:
        """Acquire the Redis lock.

        Uses SET key value NX PX for atomic acquisition.

        Args:
            blocking: If True, retry until acquired or timeout.
            timeout: Maximum wait time in seconds.

        Returns:
            LockResult with acquisition status.
        """
        if self._redis is None:
            return LockResult(
                status=LockStatus.ERROR,
                error="Redis client not available",
            )

        metadata = self._create_metadata()
        full_key = self.redis_key
        token = metadata.token
        ttl_ms = int(self._ttl_seconds * 1000)

        start_time = time.monotonic()
        deadline = start_time + timeout if timeout is not None else None

        while True:
            try:
                acquired = self._redis.set(
                    full_key,
                    token,
                    nx=True,
                    px=ttl_ms,
                )

                if acquired:
                    with self._lock:
                        self._metadata = metadata
                    return LockResult(
                        status=LockStatus.ACQUIRED,
                        metadata=metadata,
                        wait_time=time.monotonic() - start_time,
                    )

                if not blocking:
                    return LockResult(
                        status=LockStatus.NOT_ACQUIRED,
                        wait_time=time.monotonic() - start_time,
                    )

                if deadline is not None and time.monotonic() >= deadline:
                    return LockResult(
                        status=LockStatus.NOT_ACQUIRED,
                        error=f"Timeout after {timeout}s",
                        wait_time=time.monotonic() - start_time,
                    )

                # Exponential backoff with jitter: 50ms base, max 500ms
                elapsed = time.monotonic() - start_time
                sleep_time = min(0.05 * (2 ** min(int(elapsed * 10), 5)), 0.5)
                time.sleep(sleep_time)

            except Exception as e:
                return LockResult(
                    status=LockStatus.ERROR,
                    error=f"Redis error during acquire: {e}",
                    wait_time=time.monotonic() - start_time,
                )

    def release(self) -> LockResult:
        """Release the Redis lock using token-verified Lua script.

        Returns:
            LockResult with release status.
        """
        if self._redis is None:
            return LockResult(status=LockStatus.ERROR, error="Redis client not available")

        with self._lock:
            if self._metadata is None:
                return LockResult(
                    status=LockStatus.NOT_ACQUIRED,
                    error="Lock not held",
                )
            metadata = self._metadata
            self._metadata = None

        try:
            result = self._release_script(
                keys=[self.redis_key],
                args=[metadata.token],
                client=self._redis,
            )
            if result:
                return LockResult(status=LockStatus.RELEASED, metadata=metadata)
            else:
                return LockResult(
                    status=LockStatus.EXPIRED,
                    metadata=metadata,
                    error="Lock was already released or expired",
                )
        except Exception as e:
            return LockResult(
                status=LockStatus.ERROR,
                metadata=metadata,
                error=f"Redis error during release: {e}",
            )

    def renew(self, additional_seconds: Optional[float] = None) -> LockResult:
        """Renew the Redis lock using token-verified Lua script.

        Args:
            additional_seconds: New TTL in seconds. None uses original TTL.

        Returns:
            LockResult with renewal status.
        """
        if self._redis is None:
            return LockResult(status=LockStatus.ERROR, error="Redis client not available")

        with self._lock:
            if self._metadata is None:
                return LockResult(
                    status=LockStatus.NOT_ACQUIRED,
                    error="Lock not held",
                )
            metadata = self._metadata

        ttl = additional_seconds if additional_seconds is not None else self._ttl_seconds
        ttl_ms = int(ttl * 1000)

        try:
            result = self._renew_script(
                keys=[self.redis_key],
                args=[metadata.token, ttl_ms],
                client=self._redis,
            )
            if result:
                with self._lock:
                    metadata.expires_at = time.monotonic() + ttl
                    metadata.renewal_count += 1
                    metadata.last_renewed_at = time.monotonic()
                return LockResult(status=LockStatus.RENEWED, metadata=metadata)
            else:
                return LockResult(
                    status=LockStatus.EXPIRED,
                    metadata=metadata,
                    error="Lock expired or token mismatch",
                )
        except Exception as e:
            return LockResult(
                status=LockStatus.ERROR,
                metadata=metadata,
                error=f"Redis error during renew: {e}",
            )

    def is_locked(self) -> bool:
        """Check if the lock is currently held in Redis.

        Returns:
            True if the lock exists and token matches.
        """
        if self._redis is None:
            return False

        with self._lock:
            if self._metadata is None:
                return False
            token = self._metadata.token

        try:
            value = self._redis.get(self.redis_key)
            return value == token
        except Exception:
            return False

    def get_lock_info(self) -> Optional[dict[str, Any]]:
        """Get information about the current lock state from Redis.

        Returns:
            Dict with lock info, or None if lock doesn't exist.
        """
        if self._redis is None:
            return None

        try:
            value = self._redis.get(self.redis_key)
            if value is None:
                return None

            ttl = self._redis.pttl(self.redis_key)
            return {
                "lock_name": self._lock_name,
                "token": value,
                "ttl_ms": ttl,
                "ttl_seconds": ttl / 1000.0 if ttl > 0 else 0,
            }
        except Exception:
            return None
