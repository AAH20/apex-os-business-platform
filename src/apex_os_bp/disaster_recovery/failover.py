"""Failover automation module — orchestrates region/service failover."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class FailoverState(str, Enum):
    IDLE = "idle"
    PREPARING = "preparing"
    FAILOVER_IN_PROGRESS = "failover_in_progress"
    FAILOVER_COMPLETE = "failover_complete"
    FAILBACK_IN_PROGRESS = "failback_in_progress"
    FAILBACK_COMPLETE = "failback_complete"
    FAILED = "failed"


@dataclass
class FailoverResult:
    """Result of a failover or failback operation."""

    success: bool
    source_region: str
    target_region: str
    state: FailoverState
    started_at: float
    completed_at: float | None = None
    services_affected: list[str] = field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float | None:
        if self.completed_at is not None:
            return self.completed_at - self.started_at
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "source_region": self.source_region,
            "target_region": self.target_region,
            "state": self.state.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "services_affected": list(self.services_affected),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class FailoverManager:
    """Manages automated failover between regions."""

    def __init__(self) -> None:
        self._state = FailoverState.IDLE
        self._history: list[FailoverResult] = []
        self._pre_failover_hooks: list[Callable[[str, str], None]] = []
        self._post_failover_hooks: list[Callable[[FailoverResult], None]] = []
        self._health_checks: dict[str, Callable[[], bool]] = {}

    @property
    def state(self) -> FailoverState:
        return self._state

    @property
    def history(self) -> list[FailoverResult]:
        return list(self._history)

    def register_pre_failover_hook(self, hook: Callable[[str, str], None]) -> None:
        self._pre_failover_hooks.append(hook)

    def register_post_failover_hook(self, hook: Callable[[FailoverResult], None]) -> None:
        self._post_failover_hooks.append(hook)

    def register_health_check(self, service: str, check: Callable[[], bool]) -> None:
        self._health_checks[service] = check

    def is_healthy(self, service: str) -> bool:
        check = self._health_checks.get(service)
        if check is None:
            return True  # No check registered — assume healthy
        return check()

    def failover(
        self,
        source_region: str,
        target_region: str,
        services: list[str] | None = None,
        dry_run: bool = False,
    ) -> FailoverResult:
        """Execute a failover from source to target region."""
        started = time.time()
        self._state = FailoverState.PREPARING

        try:
            # Run pre-failover hooks
            for hook in self._pre_failover_hooks:
                hook(source_region, target_region)

            if dry_run:
                result = FailoverResult(
                    success=True,
                    source_region=source_region,
                    target_region=target_region,
                    state=FailoverState.FAILOVER_COMPLETE,
                    started_at=started,
                    completed_at=time.time(),
                    services_affected=services or [],
                    metadata={"dry_run": True},
                )
                self._history.append(result)
                self._state = FailoverState.FAILOVER_COMPLETE
                return result

            self._state = FailoverState.FAILOVER_IN_PROGRESS

            # Check health of services in target region
            unhealthy = [s for s in (services or []) if not self.is_healthy(s)]
            if unhealthy:
                raise RuntimeError(
                    f"Services unhealthy in target region: {', '.join(unhealthy)}"
                )

            self._state = FailoverState.FAILOVER_COMPLETE
            result = FailoverResult(
                success=True,
                source_region=source_region,
                target_region=target_region,
                state=FailoverState.FAILOVER_COMPLETE,
                started_at=started,
                completed_at=time.time(),
                services_affected=services or [],
            )
        except Exception as exc:
            self._state = FailoverState.FAILED
            result = FailoverResult(
                success=False,
                source_region=source_region,
                target_region=target_region,
                state=FailoverState.FAILED,
                started_at=started,
                completed_at=time.time(),
                services_affected=services or [],
                error=str(exc),
            )

        self._history.append(result)

        # Run post-failover hooks
        for hook in self._post_failover_hooks:
            hook(result)

        return result

    def failback(
        self,
        source_region: str,
        target_region: str,
        services: list[str] | None = None,
        dry_run: bool = False,
    ) -> FailoverResult:
        """Execute a failback (reverse failover) to restore original topology."""
        started = time.time()
        self._state = FailoverState.FAILBACK_IN_PROGRESS

        try:
            if dry_run:
                result = FailoverResult(
                    success=True,
                    source_region=source_region,
                    target_region=target_region,
                    state=FailoverState.FAILBACK_COMPLETE,
                    started_at=started,
                    completed_at=time.time(),
                    services_affected=services or [],
                    metadata={"dry_run": True, "direction": "failback"},
                )
                self._history.append(result)
                self._state = FailoverState.FAILBACK_COMPLETE
                return result

            self._state = FailoverState.FAILBACK_COMPLETE
            result = FailoverResult(
                success=True,
                source_region=source_region,
                target_region=target_region,
                state=FailoverState.FAILBACK_COMPLETE,
                started_at=started,
                completed_at=time.time(),
                services_affected=services or [],
                metadata={"direction": "failback"},
            )
        except Exception as exc:
            self._state = FailoverState.FAILED
            result = FailoverResult(
                success=False,
                source_region=source_region,
                target_region=target_region,
                state=FailoverState.FAILED,
                started_at=started,
                completed_at=time.time(),
                services_affected=services or [],
                error=str(exc),
                metadata={"direction": "failback"},
            )

        self._history.append(result)
        return result

    def last_result(self) -> FailoverResult | None:
        return self._history[-1] if self._history else None

    def reset(self) -> None:
        self._state = FailoverState.IDLE
        self._history.clear()
