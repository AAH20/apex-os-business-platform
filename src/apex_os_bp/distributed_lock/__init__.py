"""Distributed locking system for APEX-OS Business Platform.

Provides Redis locks, database advisory locks, lock renewal,
deadlock detection, and lock monitoring.
"""

from .base import LockResult, LockMetadata, BaseDistributedLock, LockStatus
from .redis_lock import RedisDistributedLock
from .database_lock import DatabaseDistributedLock
from .lock_renewal import LockRenewalManager, RenewalConfig, RenewalStats
from .deadlock_detector import (
    DeadlockDetector,
    WaitForGraph,
    WaitForEdge,
    LockOperation,
    DeadlockCycle,
)
from .monitoring import LockMonitor, LockMetrics, LockHealth, HealthCheckResult

__all__ = [
    "LockResult",
    "LockMetadata",
    "BaseDistributedLock",
    "LockStatus",
    "RedisDistributedLock",
    "DatabaseDistributedLock",
    "LockRenewalManager",
    "RenewalConfig",
    "RenewalStats",
    "DeadlockDetector",
    "WaitForGraph",
    "WaitForEdge",
    "LockOperation",
    "DeadlockCycle",
    "LockMonitor",
    "LockMetrics",
    "LockHealth",
    "HealthCheckResult",
]
