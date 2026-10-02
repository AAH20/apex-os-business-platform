"""DR Testing module — runs disaster recovery tests and tracks results."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class DRTestType(str, Enum):
    FAILOVER = "failover"
    FAILBACK = "failback"
    DATA_INTEGRITY = "data_integrity"
    REPLICATION_LAG = "replication_lag"
    RESTORE = "restore"
    NETWORK_ISOLATION = "network_isolation"
    CHAOS = "chaos"


@dataclass
class DRTestResult:
    """Result of a single DR test."""

    test_type: DRTestType
    plan_name: str
    success: bool
    started_at: float
    completed_at: float | None = None
    rpo_achieved: float | None = None
    rto_achieved: float | None = None
    details: str = ""
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float | None:
        if self.completed_at is not None:
            return self.completed_at - self.started_at
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_type": self.test_type.value,
            "plan_name": self.plan_name,
            "success": self.success,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "rpo_achieved": self.rpo_achieved,
            "rto_achieved": self.rto_achieved,
            "details": self.details,
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class DRTestRunner:
    """Runs DR tests and maintains a history of results."""

    def __init__(self) -> None:
        self._results: list[DRTestResult] = []
        self._test_handlers: dict[DRTestType, Callable[..., DRTestResult]] = {}

    def register_handler(
        self, test_type: DRTestType, handler: Callable[..., DRTestResult]
    ) -> None:
        self._test_handlers[test_type] = handler

    def run_test(
        self,
        test_type: DRTestType,
        plan_name: str,
        handler: Callable[..., DRTestResult] | None = None,
        **kwargs: Any,
    ) -> DRTestResult:
        """Run a DR test of the given type."""
        active_handler = handler or self._test_handlers.get(test_type)
        if active_handler is None:
            started = time.time()
            result = DRTestResult(
                test_type=test_type,
                plan_name=plan_name,
                success=False,
                started_at=started,
                completed_at=time.time(),
                error=f"No handler registered for test type: {test_type.value}",
            )
            self._results.append(result)
            return result

        result = active_handler(plan_name=plan_name, **kwargs)
        self._results.append(result)
        return result

    def run_failover_test(
        self,
        plan_name: str,
        source_region: str,
        target_region: str,
        services: list[str] | None = None,
        failover_fn: Callable[..., Any] | None = None,
    ) -> DRTestResult:
        """Run a failover test and measure RTO."""
        started = time.time()
        try:
            if failover_fn is None:
                raise RuntimeError("failover_fn is required for failover test")

            fo_result = failover_fn(
                source_region=source_region,
                target_region=target_region,
                services=services or [],
                dry_run=True,
            )

            completed = time.time()
            return DRTestResult(
                test_type=DRTestType.FAILOVER,
                plan_name=plan_name,
                success=fo_result.success,
                started_at=started,
                completed_at=completed,
                rto_achieved=completed - started,
                details=f"Failover test completed in {completed - started:.2f}s",
                metadata={"failover_result": fo_result.to_dict()},
            )
        except Exception as exc:
            return DRTestResult(
                test_type=DRTestType.FAILOVER,
                plan_name=plan_name,
                success=False,
                started_at=started,
                completed_at=time.time(),
                error=str(exc),
            )

    def run_data_integrity_test(
        self,
        plan_name: str,
        data_source: str,
        check_fn: Callable[[str], tuple[bool, str]] | None = None,
    ) -> DRTestResult:
        """Run a data integrity check against a data source."""
        started = time.time()
        try:
            if check_fn is None:
                raise RuntimeError("check_fn is required for data integrity test")

            passed, details = check_fn(data_source)
            return DRTestResult(
                test_type=DRTestType.DATA_INTEGRITY,
                plan_name=plan_name,
                success=passed,
                started_at=started,
                completed_at=time.time(),
                details=details,
            )
        except Exception as exc:
            return DRTestResult(
                test_type=DRTestType.DATA_INTEGRITY,
                plan_name=plan_name,
                success=False,
                started_at=started,
                completed_at=time.time(),
                error=str(exc),
            )

    def run_replication_lag_test(
        self,
        plan_name: str,
        source_region: str,
        target_region: str,
        data_source: str,
        max_lag_seconds: float,
        get_lag_fn: Callable[[str, str, str], float] | None = None,
    ) -> DRTestResult:
        """Run a replication lag test."""
        started = time.time()
        try:
            if get_lag_fn is None:
                raise RuntimeError("get_lag_fn is required for replication lag test")

            lag = get_lag_fn(source_region, target_region, data_source)
            passed = lag <= max_lag_seconds
            return DRTestResult(
                test_type=DRTestType.REPLICATION_LAG,
                plan_name=plan_name,
                success=passed,
                started_at=started,
                completed_at=time.time(),
                rpo_achieved=lag,
                details=f"Replication lag: {lag:.2f}s (max allowed: {max_lag_seconds}s)",
                metadata={"lag_seconds": lag, "max_lag_seconds": max_lag_seconds},
            )
        except Exception as exc:
            return DRTestResult(
                test_type=DRTestType.REPLICATION_LAG,
                plan_name=plan_name,
                success=False,
                started_at=started,
                completed_at=time.time(),
                error=str(exc),
            )

    def results_for_plan(self, plan_name: str) -> list[DRTestResult]:
        return [r for r in self._results if r.plan_name == plan_name]

    def results_for_type(self, test_type: DRTestType) -> list[DRTestResult]:
        return [r for r in self._results if r.test_type == test_type]

    def last_result(self) -> DRTestResult | None:
        return self._results[-1] if self._results else None

    def summary(self) -> dict[str, Any]:
        total = len(self._results)
        passed = sum(1 for r in self._results if r.success)
        return {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total > 0 else 0.0,
        }

    def clear_history(self) -> None:
        self._results.clear()
