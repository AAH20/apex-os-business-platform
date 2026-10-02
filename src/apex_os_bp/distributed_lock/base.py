"""Base classes and interfaces for distributed locks."""

from __future__ import annotations

import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class LockStatus(Enum):
    """Status of a lock operation."""

    ACQUIRED = "acquired"
    NOT_ACQUIRED = "not_acquired"
    RELEASED = "released"
    EXPIRED = "expired"
    RENEWED = "renewed"
    ERROR = "error"


@dataclass
class LockMetadata:
    """Metadata associated with a lock."""

    lock_name: str
    owner: str = field(default_factory=lambda: f"{uuid.uuid4().hex[:8]}")
    created_at: float = field(default_factory=time.monotonic)
    expires_at: Optional[float] = None
    token: str = field(default_factory=lambda: uuid.uuid4().hex)
    metadata: dict[str, Any] = field(default_factory=dict)
    renewal_count: int = 0
    last_renewed_at: Optional[float] = None

    @property
    def age_seconds(self) -> float:
        """Return the age of the lock in seconds."""
        return time.monotonic() - self.created_at

    @property
    def ttl_remaining(self) -> Optional[float]:
        """Return remaining TTL in seconds, or None if no expiry."""
        if self.expires_at is None:
            return None
        return max(0.0, self.expires_at - time.monotonic())

    @property
    def is_expired(self) -> bool:
        """Check if the lock has expired."""
        if self.expires_at is None:
            return False
        return time.monotonic() >= self.expires_at


@dataclass
class LockResult:
    """Result of a lock operation."""

    status: LockStatus
    metadata: Optional[LockMetadata] = None
    error: Optional[str] = None
    wait_time: float = 0.0

    @property
    def success(self) -> bool:
        """Check if the lock was acquired successfully."""
        return self.status == LockStatus.ACQUIRED

    def __bool__(self) -> bool:
        return self.success


class BaseDistributedLock(ABC):
    """Abstract base class for distributed locks."""

    def __init__(
        self,
        lock_name: str,
        ttl_seconds: float = 30.0,
        owner: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        self._lock_name = lock_name
        self._ttl_seconds = ttl_seconds
        self._owner = owner or f"{uuid.uuid4().hex[:8]}"
        self._extra_metadata = metadata or {}
        self._metadata: Optional[LockMetadata] = None
        self._lock = threading.Lock()

    @property
    def lock_name(self) -> str:
        return self._lock_name

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def ttl_seconds(self) -> float:
        return self._ttl_seconds

    @property
    def metadata(self) -> Optional[LockMetadata]:
        return self._metadata

    @abstractmethod
    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> LockResult:
        """Acquire the distributed lock.

        Args:
            blocking: If True, block until the lock is acquired or timeout.
            timeout: Maximum time to wait in seconds. None means wait indefinitely.

        Returns:
            LockResult indicating success or failure.
        """
        ...

    @abstractmethod
    def release(self) -> LockResult:
        """Release the distributed lock.

        Returns:
            LockResult indicating success or failure.
        """
        ...

    @abstractmethod
    def renew(self, additional_seconds: Optional[float] = None) -> LockResult:
        """Renew/extend the lock TTL.

        Args:
            additional_seconds: New TTL duration. None uses the original TTL.

        Returns:
            LockResult indicating success or failure.
        """
        ...

    @abstractmethod
    def is_locked(self) -> bool:
        """Check if the lock is currently held."""
        ...

    def _create_metadata(self) -> LockMetadata:
        """Create lock metadata for a new acquisition."""
        now = time.monotonic()
        return LockMetadata(
            lock_name=self._lock_name,
            owner=self._owner,
            created_at=now,
            expires_at=now + self._ttl_seconds,
            token=uuid.uuid4().hex,
            metadata=dict(self._extra_metadata),
        )

    def __enter__(self) -> BaseDistributedLock:
        result = self.acquire(blocking=True)
        if not result.success:
            raise RuntimeError(f"Failed to acquire lock '{self._lock_name}': {result.error}")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.release()
