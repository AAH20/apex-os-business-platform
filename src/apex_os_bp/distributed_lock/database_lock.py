"""Database-based distributed lock implementation.

Uses PostgreSQL advisory locks (pg_advisory_lock / pg_try_advisory_lock)
for session-level locking, and pg_advisory_xact_lock for
transaction-level locking.
"""

from __future__ import annotations

import hashlib
import threading
import time
from typing import Any, Optional

from .base import BaseDistributedLock, LockMetadata, LockResult, LockStatus


class DatabaseDistributedLock(BaseDistributedLock):
    """Distributed lock backed by PostgreSQL advisory locks.

    Uses 64-bit advisory lock keys derived from the lock name.
    Supports both session-level (manual release) and
    transaction-level (auto-release on commit/rollback) modes.

    Example:
        >>> lock = DatabaseDistributedLock(
        ...     "my_resource",
        ...     db_connection=conn,
        ...     ttl_seconds=10,
        ... )
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
        db_connection: Any = None,
        db_url: Optional[str] = None,
        transaction_level: bool = False,
        lock_namespace: int = 0,
    ) -> None:
        """Initialize database distributed lock.

        Args:
            lock_name: Unique name for the lock.
            ttl_seconds: Time-to-live in seconds (used for metadata tracking).
            owner: Owner identifier.
            metadata: Additional metadata.
            db_connection: Existing database connection (psycopg2/psycopg3).
            db_url: Database URL (used if db_connection is None).
            transaction_level: If True, use xact-level advisory locks.
            lock_namespace: Namespace ID to avoid collisions (0-65535).
        """
        super().__init__(lock_name, ttl_seconds, owner, metadata)
        self._db_connection = db_connection
        self._db_url = db_url
        self._transaction_level = transaction_level
        self._lock_namespace = lock_namespace
        self._lock_key = self._derive_lock_key(lock_name, lock_namespace)
        self._acquired = False

        if self._db_connection is None and self._db_url:
            self._db_connection = self._create_connection()

    @staticmethod
    def _derive_lock_key(lock_name: str, namespace: int) -> int:
        """Derive a 64-bit advisory lock key from the lock name.

        Uses first 8 bytes of SHA-256 hash combined with namespace.

        Args:
            lock_name: The lock name.
            namespace: Namespace ID.

        Returns:
            64-bit signed integer lock key.
        """
        hash_bytes = hashlib.sha256(lock_name.encode("utf-8")).digest()
        # Use first 8 bytes as a signed 64-bit integer
        key = int.from_bytes(hash_bytes[:8], byteorder="big", signed=True)
        # Mix in namespace to avoid collisions
        key = (key ^ (namespace << 32)) & 0x7FFFFFFFFFFFFFFF
        if key > 0x7FFFFFFFFFFFFFFF:
            key = key - 0x10000000000000000
        return key

    def _create_connection(self) -> Any:
        """Create a new database connection from URL."""
        try:
            import psycopg2  # type: ignore
        except ImportError:
            try:
                import psycopg  # type: ignore

                return psycopg.connect(self._db_url)
            except ImportError:
                raise ImportError(
                    "psycopg2 or psycopg3 is required for DatabaseDistributedLock. "
                    "Install with: pip install psycopg2-binary"
                )

        return psycopg2.connect(self._db_url)

    def _get_cursor(self) -> Any:
        """Get a cursor from the connection."""
        if self._db_connection is None:
            raise RuntimeError("No database connection available")
        return self._db_connection.cursor()

    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> LockResult:
        """Acquire the database advisory lock.

        Args:
            blocking: If True, use pg_advisory_lock (blocks).
            timeout: Maximum wait time in seconds.

        Returns:
            LockResult with acquisition status.
        """
        if self._db_connection is None:
            return LockResult(
                status=LockStatus.ERROR,
                error="No database connection available",
            )

        metadata = self._create_metadata()
        start_time = time.monotonic()

        try:
            cursor = self._get_cursor()

            if self._transaction_level:
                # Transaction-level advisory lock (auto-released on commit/rollback)
                if blocking:
                    cursor.execute(
                        "SELECT pg_advisory_xact_lock(%s)",
                        (self._lock_key,),
                    )
                else:
                    cursor.execute(
                        "SELECT pg_try_advisory_xact_lock(%s)",
                        (self._lock_key,),
                    )
                    result = cursor.fetchone()
                    if not result or not result[0]:
                        return LockResult(
                            status=LockStatus.NOT_ACQUIRED,
                            wait_time=time.monotonic() - start_time,
                        )
            else:
                # Session-level advisory lock
                if blocking:
                    if timeout is not None:
                        # Use pg_try_advisory_lock with polling for timeout support
                        deadline = start_time + timeout
                        while True:
                            cursor.execute(
                                "SELECT pg_try_advisory_lock(%s)",
                                (self._lock_key,),
                            )
                            row = cursor.fetchone()
                            if row and row[0]:
                                break
                            if time.monotonic() >= deadline:
                                return LockResult(
                                    status=LockStatus.NOT_ACQUIRED,
                                    error=f"Timeout after {timeout}s",
                                    wait_time=time.monotonic() - start_time,
                                )
                            time.sleep(0.05)
                    else:
                        cursor.execute(
                            "SELECT pg_advisory_lock(%s)",
                            (self._lock_key,),
                        )
                else:
                    cursor.execute(
                        "SELECT pg_try_advisory_lock(%s)",
                        (self._lock_key,),
                    )
                    row = cursor.fetchone()
                    if not row or not row[0]:
                        return LockResult(
                            status=LockStatus.NOT_ACQUIRED,
                            wait_time=time.monotonic() - start_time,
                        )

            with self._lock:
                self._metadata = metadata
                self._acquired = True

            return LockResult(
                status=LockStatus.ACQUIRED,
                metadata=metadata,
                wait_time=time.monotonic() - start_time,
            )

        except Exception as e:
            return LockResult(
                status=LockStatus.ERROR,
                error=f"Database error during acquire: {e}",
                wait_time=time.monotonic() - start_time,
            )

    def release(self) -> LockResult:
        """Release the database advisory lock.

        Returns:
            LockResult with release status.
        """
        if self._db_connection is None:
            return LockResult(status=LockStatus.ERROR, error="No database connection available")

        with self._lock:
            if self._metadata is None or not self._acquired:
                return LockResult(
                    status=LockStatus.NOT_ACQUIRED,
                    error="Lock not held",
                )
            metadata = self._metadata
            self._acquired = False
            self._metadata = None

        try:
            cursor = self._get_cursor()

            if self._transaction_level:
                # Transaction-level locks are auto-released on commit/rollback
                # We can also explicitly release with pg_advisory_xact_unlock
                cursor.execute(
                    "SELECT pg_advisory_xact_unlock(%s)",
                    (self._lock_key,),
                )
            else:
                cursor.execute(
                    "SELECT pg_advisory_unlock(%s)",
                    (self._lock_key,),
                )

            row = cursor.fetchone()
            released = row and row[0]

            if released:
                return LockResult(status=LockStatus.RELEASED, metadata=metadata)
            else:
                return LockResult(
                    status=LockStatus.ERROR,
                    metadata=metadata,
                    error="Lock was not held (already released or expired)",
                )

        except Exception as e:
            return LockResult(
                status=LockStatus.ERROR,
                metadata=metadata,
                error=f"Database error during release: {e}",
            )

    def renew(self, additional_seconds: Optional[float] = None) -> LockResult:
        """Renew the database lock.

        PostgreSQL advisory locks don't have built-in TTL, so renewal
        is a no-op that just updates metadata. The lock persists until
        explicitly released or the session ends.

        Args:
            additional_seconds: Ignored for advisory locks.

        Returns:
            LockResult with renewal status.
        """
        with self._lock:
            if self._metadata is None or not self._acquired:
                return LockResult(
                    status=LockStatus.NOT_ACQUIRED,
                    error="Lock not held",
                )
            self._metadata.renewal_count += 1
            self._metadata.last_renewed_at = time.monotonic()
            return LockResult(
                status=LockStatus.RENEWED,
                metadata=self._metadata,
            )

    def is_locked(self) -> bool:
        """Check if the lock is currently held.

        For session-level locks, checks pg_locks view.
        For transaction-level locks, checks pg_locks with xact scope.

        Returns:
            True if the lock is held.
        """
        if self._db_connection is None:
            return False

        with self._lock:
            if self._metadata is None or not self._acquired:
                return False

        try:
            cursor = self._get_cursor()
            lock_type = "advisory"
            cursor.execute(
                """
                SELECT COUNT(*) FROM pg_locks
                WHERE locktype = %s
                AND classid = %s
                AND objid = %s
                AND objsubid = %s
                """,
                (
                    lock_type,
                    self._lock_namespace,
                    self._lock_key & 0xFFFFFFFF,
                    2 if not self._transaction_level else 1,
                ),
            )
            row = cursor.fetchone()
            return row and row[0] > 0
        except Exception:
            return False

    def close(self) -> None:
        """Close the database connection if we created it."""
        if self._db_connection is not None and self._db_url:
            try:
                self._db_connection.close()
            except Exception:
                pass
            self._db_connection = None
