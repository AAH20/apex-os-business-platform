"""Redis-backed rate limiter for APEX-OS Business Platform.

Implements a distributed rate limiter using Redis with support for
sliding window, fixed window, and token bucket algorithms. Falls back
to in-memory tracking when Redis is unavailable.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RateLimitAlgorithm(str, Enum):
    """Rate limiting algorithms."""

    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    remaining: int
    reset_time: float
    retry_after: Optional[float] = None
    limit: int = 0
    current: int = 0

    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP response headers."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_time)),
        }
        if self.retry_after is not None:
            headers["Retry-After"] = str(int(self.retry_after))
        return headers


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW
    max_requests: int = 100
    window_seconds: float = 60.0
    key_prefix: str = "ratelimit"
    # Token bucket specific
    bucket_capacity: int = 100
    refill_rate: float = 1.0  # tokens per second
    # Burst
    burst_size: int = 0


class InMemoryBackend:
    """In-memory storage backend (fallback when Redis is unavailable)."""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            value, expiry = entry
            if expiry and time.time() > expiry:
                del self._data[key]
                return None
            return value

    def set(self, key: str, value: str, ttl_seconds: Optional[float] = None) -> None:
        with self._lock:
            expiry = time.time() + ttl_seconds if ttl_seconds else None
            self._data[key] = (value, expiry)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def incr(self, key: str, amount: int = 1) -> int:
        with self._lock:
            current = self._data.get(key)
            if current is None:
                self._data[key] = (str(amount), None)
                return amount
            value, expiry = current
            new_value = int(value) + amount
            self._data[key] = (str(new_value), expiry)
            return new_value

    def expire(self, key: str, ttl_seconds: float) -> None:
        with self._lock:
            entry = self._data.get(key)
            if entry:
                value, _ = entry
                self._data[key] = (value, time.time() + ttl_seconds)

    def lpush(self, key: str, value: str) -> None:
        with self._lock:
            if key not in self._data or not isinstance(self._data[key], list):
                self._data[key] = []
            self._data[key].insert(0, value)

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        with self._lock:
            lst = self._data.get(key, [])
            if end == -1:
                return lst[start:]
            return lst[start : end + 1]

    def ltrim(self, key: str, start: int, end: int) -> None:
        with self._lock:
            lst = self._data.get(key, [])
            self._data[key] = lst[start : end + 1]

    def llen(self, key: str) -> int:
        with self._lock:
            return len(self._data.get(key, []))

    def keys(self, pattern: str) -> List[str]:
        with self._lock:
            import fnmatch

            return [k for k in self._data if fnmatch.fnmatch(k, pattern)]

    def ttl(self, key: str) -> float:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return -2
            _, expiry = entry
            if expiry is None:
                return -1
            remaining = expiry - time.time()
            return max(0, remaining)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class RedisBackend:
    """Redis storage backend using redis-py."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, password: Optional[str] = None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self._client: Any = None
        self._available = False
        self._connect()

    def _connect(self) -> None:
        """Attempt to connect to Redis."""
        try:
            import redis

            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=True,
            )
            self._client.ping()
            self._available = True
            logger.info("Connected to Redis at %s:%d", self.host, self.port)
        except Exception:
            self._available = False
            logger.warning("Redis unavailable, using in-memory fallback")

    @property
    def available(self) -> bool:
        """Check if Redis is available."""
        return self._available

    def get(self, key: str) -> Optional[str]:
        if not self._available:
            return None
        try:
            return self._client.get(key)
        except Exception:
            self._available = False
            return None

    def set(self, key: str, value: str, ttl_seconds: Optional[float] = None) -> None:
        if not self._available:
            return
        try:
            if ttl_seconds:
                self._client.setex(key, int(ttl_seconds), value)
            else:
                self._client.set(key, value)
        except Exception:
            self._available = False

    def delete(self, key: str) -> None:
        if not self._available:
            return
        try:
            self._client.delete(key)
        except Exception:
            self._available = False

    def incr(self, key: str, amount: int = 1) -> int:
        if not self._available:
            return 0
        try:
            return self._client.incrby(key, amount)
        except Exception:
            self._available = False
            return 0

    def expire(self, key: str, ttl_seconds: float) -> None:
        if not self._available:
            return
        try:
            self._client.expire(key, int(ttl_seconds))
        except Exception:
            self._available = False

    def lpush(self, key: str, value: str) -> None:
        if not self._available:
            return
        try:
            self._client.lpush(key, value)
        except Exception:
            self._available = False

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        if not self._available:
            return []
        try:
            return self._client.lrange(key, start, end)
        except Exception:
            self._available = False
            return []

    def ltrim(self, key: str, start: int, end: int) -> None:
        if not self._available:
            return
        try:
            self._client.ltrim(key, start, end)
        except Exception:
            self._available = False

    def llen(self, key: str) -> int:
        if not self._available:
            return 0
        try:
            return self._client.llen(key)
        except Exception:
            self._available = False
            return 0

    def keys(self, pattern: str) -> List[str]:
        if not self._available:
            return []
        try:
            return list(self._client.keys(pattern))
        except Exception:
            self._available = False
            return []

    def ttl(self, key: str) -> float:
        if not self._available:
            return -2
        try:
            return self._client.ttl(key)
        except Exception:
            self._available = False
            return -2

    def clear(self) -> None:
        if not self._available:
            return
        try:
            self._client.flushdb()
        except Exception:
            self._available = False


class RedisRateLimiter:
    """Distributed rate limiter with Redis backend and in-memory fallback."""

    def __init__(
        self,
        config: Optional[RateLimitConfig] = None,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
    ):
        self.config = config or RateLimitConfig()
        self._redis: Optional[RedisBackend] = None
        self._memory = InMemoryBackend()
        self._lock = threading.Lock()

        # Try Redis first
        try:
            self._redis = RedisBackend(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
            )
        except Exception:
            logger.warning("Failed to initialize Redis backend, using in-memory only")

    @property
    def backend(self) -> str:
        """Get current backend name."""
        if self._redis and self._redis.available:
            return "redis"
        return "memory"

    def _make_key(self, identifier: str) -> str:
        """Build a Redis key for an identifier."""
        return f"{self.config.key_prefix}:{identifier}"

    def check(self, identifier: str) -> RateLimitResult:
        """Check if a request is allowed under the rate limit."""
        if self.config.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            return self._check_fixed_window(identifier)
        elif self.config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            return self._check_sliding_window(identifier)
        elif self.config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            return self._check_token_bucket(identifier)
        else:
            raise ValueError(f"Unknown algorithm: {self.config.algorithm}")

    def _check_fixed_window(self, identifier: str) -> RateLimitResult:
        """Fixed window rate limiting."""
        now = time.time()
        window_start = int(now / self.config.window_seconds) * self.config.window_seconds
        key = f"{self._make_key(identifier)}:fixed:{window_start}"

        if self._redis and self._redis.available:
            count = self._redis.incr(key)
            if count == 1:
                self._redis.expire(key, self.config.window_seconds + 1)
        else:
            count = self._memory.incr(key)

        allowed = count <= self.config.max_requests
        remaining = max(0, self.config.max_requests - count)
        reset_time = window_start + self.config.window_seconds
        retry_after = reset_time - now if not allowed else None

        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=reset_time,
            retry_after=retry_after,
            limit=self.config.max_requests,
            current=count,
        )

    def _check_sliding_window(self, identifier: str) -> RateLimitResult:
        """Sliding window rate limiting using a sorted set / list."""
        now = time.time()
        window_start = now - self.config.window_seconds
        key = f"{self._make_key(identifier)}:sliding"

        if self._redis and self._redis.available:
            # Remove old entries
            self._redis.ltrim(key, 0, -1)  # Keep all, we filter by time
            entries = self._redis.lrange(key, 0, -1)
            valid = [e for e in entries if float(e) > window_start]

            if len(valid) >= self.config.max_requests:
                oldest = float(valid[0])
                retry_after = oldest + self.config.window_seconds - now
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=oldest + self.config.window_seconds,
                    retry_after=max(0, retry_after),
                    limit=self.config.max_requests,
                    current=len(valid),
                )

            # Add current request
            self._redis.lpush(key, str(now))
            self._redis.expire(key, int(self.config.window_seconds) + 1)

            remaining = self.config.max_requests - len(valid) - 1
            return RateLimitResult(
                allowed=True,
                remaining=max(0, remaining),
                reset_time=now + self.config.window_seconds,
                limit=self.config.max_requests,
                current=len(valid) + 1,
            )
        else:
            # In-memory sliding window
            entries_raw = self._memory.lrange(key, 0, -1)
            valid = [e for e in entries_raw if float(e) > window_start]

            if len(valid) >= self.config.max_requests:
                oldest = float(valid[0])
                retry_after = oldest + self.config.window_seconds - now
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=oldest + self.config.window_seconds,
                    retry_after=max(0, retry_after),
                    limit=self.config.max_requests,
                    current=len(valid),
                )

            self._memory.lpush(key, str(now))
            remaining = self.config.max_requests - len(valid) - 1
            return RateLimitResult(
                allowed=True,
                remaining=max(0, remaining),
                reset_time=now + self.config.window_seconds,
                limit=self.config.max_requests,
                current=len(valid) + 1,
            )

    def _check_token_bucket(self, identifier: str) -> RateLimitResult:
        """Token bucket rate limiting."""
        now = time.time()
        key = f"{self._make_key(identifier)}:bucket"
        capacity = self.config.bucket_capacity
        refill_rate = self.config.refill_rate

        if self._redis and self._redis.available:
            raw = self._redis.get(key)
            if raw:
                tokens_str, last_refill_str = raw.split(":")
                tokens = float(tokens_str)
                last_refill = float(last_refill_str)
            else:
                tokens = float(capacity)
                last_refill = now

            elapsed = now - last_refill
            tokens = min(capacity, tokens + elapsed * refill_rate)

            if tokens >= 1:
                tokens -= 1
                self._redis.set(key, f"{tokens}:{now}", self.config.window_seconds * 2)
                remaining = int(tokens)
                return RateLimitResult(
                    allowed=True,
                    remaining=remaining,
                    reset_time=now + (1.0 / refill_rate) if tokens < 1 else now,
                    limit=capacity,
                    current=int(capacity - tokens),
                )
            else:
                retry_after = (1.0 - tokens) / refill_rate
                self._redis.set(key, f"{tokens}:{now}", self.config.window_seconds * 2)
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=now + retry_after,
                    retry_after=retry_after,
                    limit=capacity,
                    current=capacity,
                )
        else:
            raw = self._memory.get(key)
            if raw:
                tokens_str, last_refill_str = raw.split(":")
                tokens = float(tokens_str)
                last_refill = float(last_refill_str)
            else:
                tokens = float(capacity)
                last_refill = now

            elapsed = now - last_refill
            tokens = min(capacity, tokens + elapsed * refill_rate)

            if tokens >= 1:
                tokens -= 1
                self._memory.set(key, f"{tokens}:{now}", self.config.window_seconds * 2)
                remaining = int(tokens)
                return RateLimitResult(
                    allowed=True,
                    remaining=remaining,
                    reset_time=now + (1.0 / refill_rate) if tokens < 1 else now,
                    limit=capacity,
                    current=int(capacity - tokens),
                )
            else:
                retry_after = (1.0 - tokens) / refill_rate
                self._memory.set(key, f"{tokens}:{now}", self.config.window_seconds * 2)
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=now + retry_after,
                    retry_after=retry_after,
                    limit=capacity,
                    current=capacity,
                )

    def reset(self, identifier: str) -> None:
        """Reset rate limit for an identifier."""
        pattern = f"{self._make_key(identifier)}:*"
        if self._redis and self._redis.available:
            keys = self._redis.keys(pattern)
            for key in keys:
                self._redis.delete(key)
        else:
            keys = self._memory.keys(pattern)
            for key in keys:
                self._memory.delete(key)

    def get_current_usage(self, identifier: str) -> Dict[str, Any]:
        """Get current rate limit usage for an identifier (without consuming a request)."""
        now = time.time()
        key = self._make_key(identifier)

        if self.config.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            window_start = int(now / self.config.window_seconds) * self.config.window_seconds
            fixed_key = f"{key}:fixed:{window_start}"
            if self._redis and self._redis.available:
                raw = self._redis.get(fixed_key)
                current = int(raw) if raw else 0
            else:
                raw = self._memory.get(fixed_key)
                current = int(raw) if raw else 0
            return {
                "identifier": identifier,
                "limit": self.config.max_requests,
                "current": current,
                "remaining": max(0, self.config.max_requests - current),
                "reset_time": window_start + self.config.window_seconds,
                "backend": self.backend,
            }
        else:
            # For sliding window and token bucket, just call check
            result = self.check(identifier)
            return {
                "identifier": identifier,
                "limit": result.limit,
                "current": result.current,
                "remaining": result.remaining,
                "reset_time": result.reset_time,
                "backend": self.backend,
            }
