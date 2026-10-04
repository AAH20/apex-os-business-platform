"""Per-user rate limiting for APEX-OS Business Platform.

Implements a sliding-window rate limiter that tracks request timestamps
per user and enforces configurable request limits within time windows.
"""

import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


class RateLimitExceeded(Exception):
    """Raised when a user exceeds their rate limit."""

    def __init__(self, message: str, retry_after: float):
        """Initialize the exception.

        Args:
            message: Human-readable error message.
            retry_after: Seconds until the user may retry.
        """
        super().__init__(message)
        self.retry_after = retry_after


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting behavior."""
    max_requests: int = 100
    window_seconds: float = 60.0
    burst_size: int = 10


class RateLimiter:
    """Thread-safe sliding-window rate limiter with per-user tracking."""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize the rate limiter.

        Args:
            config: Rate limit configuration (uses defaults if None).
        """
        self._config = config or RateLimitConfig()
        self._user_requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def _clean_old(self, user_id: str, now: float) -> None:
        """Remove timestamps outside the current window for a user."""
        if user_id in self._user_requests:
            cutoff = now - self._config.window_seconds
            self._user_requests[user_id] = [
                t for t in self._user_requests[user_id] if t > cutoff
            ]

    def allow_request(self, user_id: str) -> Tuple[bool, float]:
        """Check if a request from the given user should be allowed.

        Args:
            user_id: The user identifier to check.

        Returns:
            Tuple of (allowed, retry_after_seconds). If allowed is True,
            retry_after is 0.0. If False, retry_after indicates how long
            the user must wait before retrying.
        """
        now = time.time()
        with self._lock:
            self._clean_old(user_id, now)
            requests = self._user_requests.setdefault(user_id, [])

            if len(requests) >= self._config.max_requests:
                retry_after = requests[0] + self._config.window_seconds - now
                return False, max(0.0, retry_after)

            requests.append(now)
            return True, 0.0

    def check_rate_limit(self, user_id: str) -> None:
        """Check rate limit and raise an exception if exceeded.

        Args:
            user_id: The user identifier to check.

        Raises:
            RateLimitExceeded: If the user has exceeded their rate limit.
        """
        allowed, retry_after = self.allow_request(user_id)
        if not allowed:
            raise RateLimitExceeded(
                f"Rate limit exceeded for user '{user_id}'", retry_after
            )

    def get_remaining(self, user_id: str) -> int:
        """Get the number of remaining requests for a user in the current window.

        Args:
            user_id: The user identifier.

        Returns:
            Number of remaining allowed requests.
        """
        now = time.time()
        with self._lock:
            self._clean_old(user_id, now)
            return self._config.max_requests - len(self._user_requests.get(user_id, []))

    def get_reset_time(self, user_id: str) -> float:
        """Get the timestamp when the rate limit window resets for a user.

        Args:
            user_id: The user identifier.

        Returns:
            Unix timestamp when the oldest request in the window expires.
        """
        now = time.time()
        with self._lock:
            if user_id not in self._user_requests or not self._user_requests[user_id]:
                return now
            return self._user_requests[user_id][0] + self._config.window_seconds

    def reset(self, user_id: str) -> None:
        """Reset the rate limit for a specific user.

        Args:
            user_id: The user identifier to reset.
        """
        with self._lock:
            self._user_requests.pop(user_id, None)

    def reset_all(self) -> None:
        """Reset rate limits for all users."""
        with self._lock:
            self._user_requests.clear()
