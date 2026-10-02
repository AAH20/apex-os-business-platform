"""Lock monitoring and metrics collection.

Provides real-time monitoring of distributed lock health, contention,
acquisition statistics, and alerting capabilities.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from .base import BaseDistributedLock, LockResult, LockStatus

logger = logging.getLogger(__name__)


class LockHealth(Enum):
    """Health status of a lock."""

    HEALTHY = "healthy"
    CONTENTED = "contended"
    EXPIRED = "expired"
    DEADLOCKED = "deadlocked"
    ERROR = "error"


@dataclass
class LockMetrics:
    """Metrics for a single lock."""

    lock_name: str
    acquisitions_total: int = 0
    acquisitions_success: int = 0
    acquisitions_failed: int = 0
    releases_total: int = 0
    renewals_total: int = 0
    renewals_failed: int = 0
    total_wait_time_seconds: float = 0.0
    total_hold_time_seconds: float = 0.0
    max_wait_time_seconds: float = 0.0
    max_hold_time_seconds: float = 0.0
    current_holders: int = 0
    peak_holders: int = 0
    errors: int = 0
    created_at: float = field(default_factory=time.monotonic)
    last_updated: float = field(default_factory=time.monotonic)

    @property
    def success_rate(self) -> float:
        if self.acquisitions_total == 0:
            return 0.0
        return self.acquisitions_success / self.acquisitions_total

    @property
    def average_wait_time(self) -> float:
        if self.acquisitions_total == 0:
            return 0.0
        return self.total_wait_time_seconds / self.acquisitions_total

    @property
    def average_hold_time(self) -> float:
        if self.releases_total == 0:
            return 0.0
        return self.total_hold_time_seconds / self.releases_total

    @property
    def contention_ratio(self) -> float:
        """Ratio of failed acquisitions to total attempts."""
        if self.acquisitions_total == 0:
            return 0.0
        return self.acquisitions_failed / self.acquisitions_total

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "lock_name": self.lock_name,
            "acquisitions_total": self.acquisitions_total,
            "acquisitions_success": self.acquisitions_success,
            "acquisitions_failed": self.acquisitions_failed,
            "releases_total": self.releases_total,
            "renewals_total": self.renewals_total,
            "renewals_failed": self.renewals_failed,
            "total_wait_time_seconds": self.total_wait_time_seconds,
            "total_hold_time_seconds": self.total_hold_time_seconds,
            "max_wait_time_seconds": self.max_wait_time_seconds,
            "max_hold_time_seconds": self.max_hold_time_seconds,
            "current_holders": self.current_holders,
            "peak_holders": self.peak_holders,
            "errors": self.errors,
            "success_rate": self.success_rate,
            "average_wait_time": self.average_wait_time,
            "average_hold_time": self.average_hold_time,
            "contention_ratio": self.contention_ratio,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }


@dataclass
class HealthCheckResult:
    """Result of a lock health check."""

    lock_name: str
    health: LockHealth
    message: str
    metrics: Optional[LockMetrics] = None
    timestamp: float = field(default_factory=time.monotonic)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lock_name": self.lock_name,
            "health": self.health.value,
            "message": self.message,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "timestamp": self.timestamp,
        }


class LockMonitor:
    """Monitors distributed locks and collects metrics.

    Tracks acquisition statistics, hold times, contention, and
    provides health checks and alerting.

    Example:
        >>> monitor = LockMonitor()
        >>> lock = RedisDistributedLock("my_resource", ttl_seconds=30)
        >>> result = lock.acquire()
        >>> monitor.record_acquisition(lock, result)
        >>> # ... work ...
        >>> monitor.record_release(lock)
        >>> health = monitor.check_health("my_resource")
    """

    def __init__(
        self,
        alert_threshold_contention: float = 0.5,
        alert_threshold_wait_time: float = 5.0,
        alert_threshold_hold_time: float = 60.0,
        on_alert: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        """Initialize lock monitor.

        Args:
            alert_threshold_contention: Contention ratio that triggers alert.
            alert_threshold_wait_time: Wait time (seconds) that triggers alert.
            alert_threshold_hold_time: Hold time (seconds) that triggers alert.
            on_alert: Callback(lock_name, message) when threshold exceeded.
        """
        self._metrics: dict[str, LockMetrics] = {}
        self._alert_threshold_contention = alert_threshold_contention
        self._alert_threshold_wait_time = alert_threshold_wait_time
        self._alert_threshold_hold_time = alert_threshold_hold_time
        self._on_alert = on_alert
        self._lock = threading.Lock()
        self._hold_start_times: dict[str, float] = {}

    @property
    def metrics(self) -> dict[str, LockMetrics]:
        with self._lock:
            return dict(self._metrics)

    def record_acquisition(
        self,
        lock: BaseDistributedLock,
        result: LockResult,
    ) -> None:
        """Record a lock acquisition attempt.

        Args:
            lock: The lock that was attempted.
            result: The result of the acquisition.
        """
        name = lock.lock_name
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = LockMetrics(lock_name=name)

            m = self._metrics[name]
            m.acquisitions_total += 1
            m.last_updated = time.monotonic()

            if result.success:
                m.acquisitions_success += 1
                m.current_holders += 1
                m.peak_holders = max(m.peak_holders, m.current_holders)
                self._hold_start_times[name] = time.monotonic()
            else:
                m.acquisitions_failed += 1
                if result.error:
                    m.errors += 1

            m.total_wait_time_seconds += result.wait_time
            m.max_wait_time_seconds = max(m.max_wait_time_seconds, result.wait_time)

            # Check thresholds
            self._check_thresholds(name, m)

    def record_release(
        self,
        lock: BaseDistributedLock,
        result: Optional[LockResult] = None,
    ) -> None:
        """Record a lock release.

        Args:
            lock: The lock that was released.
            result: Optional release result.
        """
        name = lock.lock_name
        with self._lock:
            if name not in self._metrics:
                return

            m = self._metrics[name]
            m.releases_total += 1
            m.current_holders = max(0, m.current_holders - 1)
            m.last_updated = time.monotonic()

            # Calculate hold time
            start_time = self._hold_start_times.pop(name, None)
            if start_time is not None:
                hold_time = time.monotonic() - start_time
                m.total_hold_time_seconds += hold_time
                m.max_hold_time_seconds = max(m.max_hold_time_seconds, hold_time)

    def record_renewal(
        self,
        lock: BaseDistributedLock,
        result: LockResult,
    ) -> None:
        """Record a lock renewal.

        Args:
            lock: The lock that was renewed.
            result: The renewal result.
        """
        name = lock.lock_name
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = LockMetrics(lock_name=name)

            m = self._metrics[name]
            m.renewals_total += 1
            m.last_updated = time.monotonic()

            if result.status != LockStatus.RENEWED:
                m.renewals_failed += 1

    def record_error(self, lock_name: str, error: str) -> None:
        """Record an error for a lock.

        Args:
            lock_name: Name of the lock.
            error: Error message.
        """
        with self._lock:
            if lock_name not in self._metrics:
                self._metrics[lock_name] = LockMetrics(lock_name=lock_name)
            self._metrics[lock_name].errors += 1
            self._metrics[lock_name].last_updated = time.monotonic()

    def get_metrics(self, lock_name: str) -> Optional[LockMetrics]:
        """Get metrics for a specific lock.

        Args:
            lock_name: Name of the lock.

        Returns:
            LockMetrics or None if not tracked.
        """
        with self._lock:
            return self._metrics.get(lock_name)

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        """Get all metrics as dictionaries.

        Returns:
            Dict mapping lock names to metric dicts.
        """
        with self._lock:
            return {name: m.to_dict() for name, m in self._metrics.items()}

    def check_health(self, lock_name: str) -> HealthCheckResult:
        """Check the health of a lock.

        Args:
            lock_name: Name of the lock to check.

        Returns:
            HealthCheckResult with health status.
        """
        with self._lock:
            m = self._metrics.get(lock_name)

        if m is None:
            return HealthCheckResult(
                lock_name=lock_name,
                health=LockHealth.ERROR,
                message="No metrics available for this lock",
            )

        # Determine health status
        if m.errors > 0 and m.acquisitions_failed == m.acquisitions_total:
            health = LockHealth.ERROR
            message = f"Lock has {m.errors} errors and all acquisitions failed"
        elif m.contention_ratio > 0.8:
            health = LockHealth.DEADLOCKED
            message = f"High contention ratio: {m.contention_ratio:.2%}"
        elif m.contention_ratio > self._alert_threshold_contention:
            health = LockHealth.CONTENTED
            message = f"Elevated contention: {m.contention_ratio:.2%}"
        elif m.acquisitions_failed > 0 and m.acquisitions_success == 0:
            health = LockHealth.EXPIRED
            message = "All acquisitions have failed"
        else:
            health = LockHealth.HEALTHY
            message = f"Lock is healthy (success rate: {m.success_rate:.2%})"

        return HealthCheckResult(
            lock_name=lock_name,
            health=health,
            message=message,
            metrics=m,
        )

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all lock metrics.

        Returns:
            Summary dict with aggregate statistics.
        """
        with self._lock:
            all_metrics = list(self._metrics.values())

        if not all_metrics:
            return {
                "total_locks": 0,
                "total_acquisitions": 0,
                "overall_success_rate": 0.0,
                "locks_by_health": {},
            }

        total_acquisitions = sum(m.acquisitions_total for m in all_metrics)
        total_success = sum(m.acquisitions_success for m in all_metrics)
        overall_rate = total_success / total_acquisitions if total_acquisitions > 0 else 0.0

        locks_by_health: dict[str, int] = defaultdict(int)
        for m in all_metrics:
            result = self.check_health(m.lock_name)
            locks_by_health[result.health.value] += 1

        return {
            "total_locks": len(all_metrics),
            "total_acquisitions": total_acquisitions,
            "total_success": total_success,
            "total_failed": sum(m.acquisitions_failed for m in all_metrics),
            "overall_success_rate": overall_rate,
            "total_renewals": sum(m.renewals_total for m in all_metrics),
            "total_errors": sum(m.errors for m in all_metrics),
            "locks_by_health": dict(locks_by_health),
            "most_contended_lock": max(
                all_metrics, key=lambda m: m.contention_ratio
            ).lock_name,
            "highest_wait_time_lock": max(
                all_metrics, key=lambda m: m.max_wait_time_seconds
            ).lock_name,
        }

    def reset(self, lock_name: Optional[str] = None) -> None:
        """Reset metrics for a specific lock or all locks.

        Args:
            lock_name: Lock to reset, or None to reset all.
        """
        with self._lock:
            if lock_name:
                self._metrics.pop(lock_name, None)
                self._hold_start_times.pop(lock_name, None)
            else:
                self._metrics.clear()
                self._hold_start_times.clear()

    def _check_thresholds(self, lock_name: str, metrics: LockMetrics) -> None:
        """Check if any alert thresholds are exceeded."""
        if self._on_alert is None:
            return

        if metrics.contention_ratio > self._alert_threshold_contention:
            self._on_alert(
                lock_name,
                f"Contention ratio {metrics.contention_ratio:.2%} exceeds "
                f"threshold {self._alert_threshold_contention:.2%}",
            )

        if metrics.max_wait_time_seconds > self._alert_threshold_wait_time:
            self._on_alert(
                lock_name,
                f"Max wait time {metrics.max_wait_time_seconds:.1f}s exceeds "
                f"threshold {self._alert_threshold_wait_time:.1f}s",
            )

        if metrics.max_hold_time_seconds > self._alert_threshold_hold_time:
            self._on_alert(
                lock_name,
                f"Max hold time {metrics.max_hold_time_seconds:.1f}s exceeds "
                f"threshold {self._alert_threshold_hold_time:.1f}s",
            )
