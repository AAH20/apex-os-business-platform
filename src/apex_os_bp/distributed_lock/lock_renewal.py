"""Lock renewal manager for distributed locks.

Provides automatic background renewal of distributed locks to prevent
expiration during long-running critical sections.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .base import BaseDistributedLock, LockResult, LockStatus

logger = logging.getLogger(__name__)


@dataclass
class RenewalConfig:
    """Configuration for lock renewal."""

    # Interval between renewal attempts (seconds)
    renewal_interval: float = 10.0
    # Fraction of TTL to use as renewal interval if not explicitly set
    renewal_interval_factor: float = 0.3
    # Maximum number of consecutive renewal failures before giving up
    max_consecutive_failures: int = 3
    # Whether to stop renewal on first failure
    stop_on_failure: bool = False
    # Callback invoked on renewal failure
    on_failure: Optional[Callable[[str, Exception], None]] = None
    # Callback invoked on each successful renewal
    on_renewal: Optional[Callable[[str, LockResult], None]] = None


@dataclass
class RenewalStats:
    """Statistics for a renewal session."""

    lock_name: str
    renewals_attempted: int = 0
    renewals_succeeded: int = 0
    renewals_failed: int = 0
    consecutive_failures: int = 0
    started_at: float = field(default_factory=time.monotonic)
    stopped_at: Optional[float] = None
    last_renewal_at: Optional[float] = None
    last_error: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        end = self.stopped_at or time.monotonic()
        return end - self.started_at

    @property
    def success_rate(self) -> float:
        if self.renewals_attempted == 0:
            return 0.0
        return self.renewals_succeeded / self.renewals_attempted


class LockRenewalManager:
    """Manages automatic renewal of distributed locks.

    Runs a background thread that periodically renews registered locks
    to prevent them from expiring during long-running operations.

    Example:
        >>> manager = LockRenewalManager()
        >>> lock = RedisDistributedLock("my_resource", ttl_seconds=30)
        >>> lock.acquire()
        >>> manager.register(lock)
        >>> # ... long-running work ...
        >>> manager.unregister(lock)
        >>> lock.release()
    """

    def __init__(self, config: Optional[RenewalConfig] = None) -> None:
        self._config = config or RenewalConfig()
        self._renewal_threads: dict[str, threading.Thread] = {}
        self._stop_events: dict[str, threading.Event] = {}
        self._stats: dict[str, RenewalStats] = {}
        self._lock = threading.Lock()

    @property
    def config(self) -> RenewalConfig:
        return self._config

    def register(
        self,
        lock: BaseDistributedLock,
        renewal_interval: Optional[float] = None,
    ) -> None:
        """Register a lock for automatic renewal.

        Args:
            lock: The distributed lock to renew.
            renewal_interval: Override renewal interval for this lock.
        """
        lock_name = lock.lock_name

        with self._lock:
            if lock_name in self._renewal_threads:
                logger.warning("Lock '%s' already registered for renewal", lock_name)
                return

            interval = renewal_interval or self._get_renewal_interval(lock)
            stop_event = threading.Event()

            self._stats[lock_name] = RenewalStats(lock_name=lock_name)
            self._stop_events[lock_name] = stop_event

            thread = threading.Thread(
                target=self._renewal_loop,
                args=(lock, lock_name, interval, stop_event),
                name=f"lock-renewal-{lock_name}",
                daemon=True,
            )
            self._renewal_threads[lock_name] = thread
            thread.start()

            logger.info(
                "Registered lock '%s' for renewal (interval=%.1fs)",
                lock_name,
                interval,
            )

    def unregister(self, lock_or_name: Any) -> None:
        """Unregister a lock from automatic renewal.

        Args:
            lock_or_name: The lock instance or lock name to unregister.
        """
        lock_name = (
            lock_or_name.lock_name
            if hasattr(lock_or_name, "lock_name")
            else str(lock_or_name)
        )

        with self._lock:
            if lock_name not in self._renewal_threads:
                return

            self._stop_events[lock_name].set()
            thread = self._renewal_threads.pop(lock_name)
            self._stop_events.pop(lock_name, None)

            if thread.is_alive() and thread is not threading.current_thread():
                thread.join(timeout=5.0)

            if lock_name in self._stats:
                self._stats[lock_name].stopped_at = time.monotonic()

            logger.info("Unregistered lock '%s' from renewal", lock_name)

    def get_stats(self, lock_or_name: Any) -> Optional[RenewalStats]:
        """Get renewal statistics for a lock.

        Args:
            lock_or_name: The lock instance or lock name.

        Returns:
            RenewalStats or None if not registered.
        """
        lock_name = (
            lock_or_name.lock_name
            if hasattr(lock_or_name, "lock_name")
            else str(lock_or_name)
        )
        return self._stats.get(lock_name)

    def get_all_stats(self) -> dict[str, RenewalStats]:
        """Get renewal statistics for all registered locks."""
        return dict(self._stats)

    def is_registered(self, lock_or_name: Any) -> bool:
        """Check if a lock is registered for renewal."""
        lock_name = (
            lock_or_name.lock_name
            if hasattr(lock_or_name, "lock_name")
            else str(lock_or_name)
        )
        return lock_name in self._renewal_threads

    def shutdown(self, timeout: float = 10.0) -> None:
        """Stop all renewal threads and clean up.

        Args:
            timeout: Maximum time to wait for threads to stop.
        """
        with self._lock:
            lock_names = list(self._renewal_threads.keys())

        for name in lock_names:
            self.unregister(name)

        logger.info("LockRenewalManager shutdown complete")

    def _get_renewal_interval(self, lock: BaseDistributedLock) -> float:
        """Calculate renewal interval for a lock."""
        if self._config.renewal_interval > 0:
            return self._config.renewal_interval
        return lock.ttl_seconds * self._config.renewal_interval_factor

    def _renewal_loop(
        self,
        lock: BaseDistributedLock,
        lock_name: str,
        interval: float,
        stop_event: threading.Event,
    ) -> None:
        """Background loop that renews a lock until stopped."""
        while not stop_event.is_set():
            # Sleep in small increments to respond quickly to stop
            if stop_event.wait(timeout=interval):
                break

            if stop_event.is_set():
                break

            stats = self._stats.get(lock_name)
            if stats is None:
                break

            stats.renewals_attempted += 1

            try:
                result = lock.renew()

                if result.status == LockStatus.RENEWED:
                    stats.renewals_succeeded += 1
                    stats.consecutive_failures = 0
                    stats.last_renewal_at = time.monotonic()

                    if self._config.on_renewal:
                        try:
                            self._config.on_renewal(lock_name, result)
                        except Exception as e:
                            logger.exception("Error in renewal callback: %s", e)
                else:
                    stats.renewals_failed += 1
                    stats.consecutive_failures += 1
                    stats.last_error = result.error

                    logger.warning(
                        "Lock '%s' renewal failed: %s",
                        lock_name,
                        result.error,
                    )

                    if self._config.on_failure:
                        try:
                            self._config.on_failure(
                                lock_name,
                                Exception(result.error or "Renewal failed"),
                            )
                        except Exception as e:
                            logger.exception("Error in failure callback: %s", e)

                    if (
                        self._config.stop_on_failure
                        or stats.consecutive_failures >= self._config.max_consecutive_failures
                    ):
                        logger.error(
                            "Lock '%s' renewal stopped after %d consecutive failures",
                            lock_name,
                            stats.consecutive_failures,
                        )
                        break

            except Exception as e:
                stats.renewals_failed += 1
                stats.consecutive_failures += 1
                stats.last_error = str(e)

                logger.exception("Lock '%s' renewal error: %s", lock_name, e)

                if self._config.on_failure:
                    try:
                        self._config.on_failure(lock_name, e)
                    except Exception as cb_e:
                        logger.exception("Error in failure callback: %s", cb_e)

                if (
                    self._config.stop_on_failure
                    or stats.consecutive_failures >= self._config.max_consecutive_failures
                ):
                    logger.error(
                        "Lock '%s' renewal stopped after %d consecutive failures",
                        lock_name,
                        stats.consecutive_failures,
                    )
                    break

        # Mark stats as stopped
        stats = self._stats.get(lock_name)
        if stats and stats.stopped_at is None:
            stats.stopped_at = time.monotonic()

    def __enter__(self) -> LockRenewalManager:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.shutdown()
