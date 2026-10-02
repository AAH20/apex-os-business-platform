"""DR Monitoring module — monitors DR health and raises alerts."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class DRHealthStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class DRAlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class DRAlert:
    """A DR monitoring alert."""

    alert_id: str
    severity: DRAlertSeverity
    source: str
    message: str
    timestamp: float
    acknowledged: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.value,
            "source": self.source,
            "message": self.message,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
            "metadata": dict(self.metadata),
        }


@dataclass
class DRHealthReport:
    """Aggregated health report for DR infrastructure."""

    status: DRHealthStatus
    timestamp: float
    replication_summary: dict[str, Any] = field(default_factory=dict)
    failover_ready: bool = True
    untested_plans: list[str] = field(default_factory=list)
    active_alerts: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "replication_summary": dict(self.replication_summary),
            "failover_ready": self.failover_ready,
            "untested_plans": list(self.untested_plans),
            "active_alerts": self.active_alerts,
            "details": dict(self.details),
        }


class DRMonitor:
    """Monitors DR infrastructure health and raises alerts."""

    def __init__(self) -> None:
        self._alerts: list[DRAlert] = []
        self._alert_handlers: list[Callable[[DRAlert], None]] = []
        self._alert_counter = 0

    def register_alert_handler(self, handler: Callable[[DRAlert], None]) -> None:
        self._alert_handlers.append(handler)

    def _next_alert_id(self) -> str:
        self._alert_counter += 1
        return f"DR-{self._alert_counter:06d}"

    def raise_alert(
        self,
        severity: DRAlertSeverity,
        source: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> DRAlert:
        alert = DRAlert(
            alert_id=self._next_alert_id(),
            severity=severity,
            source=source,
            message=message,
            timestamp=time.time(),
            metadata=metadata or {},
        )
        self._alerts.append(alert)
        for handler in self._alert_handlers:
            handler(alert)
        return alert

    def acknowledge_alert(self, alert_id: str) -> bool:
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def active_alerts(
        self, severity: DRAlertSeverity | None = None
    ) -> list[DRAlert]:
        alerts = [a for a in self._alerts if not a.acknowledged]
        if severity is not None:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts

    def alerts_for_source(self, source: str) -> list[DRAlert]:
        return [a for a in self._alerts if a.source == source]

    def clear_alerts(self) -> None:
        self._alerts.clear()

    def check_replication_health(
        self,
        replication_manager: Any,
        lag_threshold: float = 300.0,
    ) -> DRHealthStatus:
        """Check replication health and raise alerts for unhealthy links."""
        summary = replication_manager.summary()
        unhealthy_count = (
            summary.get("lagging", 0)
            + summary.get("degraded", 0)
            + summary.get("broken", 0)
        )

        if summary.get("broken", 0) > 0:
            self.raise_alert(
                severity=DRAlertSeverity.CRITICAL,
                source="replication",
                message=f"{summary['broken']} replication link(s) broken",
                metadata=summary,
            )
            return DRHealthStatus.CRITICAL

        if summary.get("degraded", 0) > 0:
            self.raise_alert(
                severity=DRAlertSeverity.WARNING,
                source="replication",
                message=f"{summary['degraded']} replication link(s) degraded",
                metadata=summary,
            )
            return DRHealthStatus.WARNING

        if summary.get("lagging", 0) > 0:
            self.raise_alert(
                severity=DRAlertSeverity.WARNING,
                source="replication",
                message=f"{summary['lagging']} replication link(s) lagging",
                metadata=summary,
            )
            return DRHealthStatus.WARNING

        return DRHealthStatus.HEALTHY

    def check_failover_readiness(
        self,
        failover_manager: Any,
        replication_manager: Any,
    ) -> bool:
        """Check if the system is ready for failover."""
        # Failover is ready if no replication links are broken
        summary = replication_manager.summary()
        if summary.get("broken", 0) > 0:
            self.raise_alert(
                severity=DRAlertSeverity.CRITICAL,
                source="failover_readiness",
                message="Failover not ready: broken replication links detected",
                metadata=summary,
            )
            return False
        return True

    def check_plan_freshness(
        self,
        untested_plans: list[str],
        max_age_days: int = 30,
    ) -> DRHealthStatus:
        """Check if DR plans have been tested recently."""
        if not untested_plans:
            return DRHealthStatus.HEALTHY

        self.raise_alert(
            severity=DRAlertSeverity.WARNING,
            source="plan_freshness",
            message=f"{len(untested_plans)} DR plan(s) not tested in {max_age_days} days",
            metadata={"untested_plans": untested_plans, "max_age_days": max_age_days},
        )
        return DRHealthStatus.WARNING

    def generate_health_report(
        self,
        replication_manager: Any,
        failover_manager: Any,
        untested_plans: list[str] | None = None,
    ) -> DRHealthReport:
        """Generate a comprehensive DR health report."""
        repl_status = self.check_replication_health(replication_manager)
        failover_ready = self.check_failover_readiness(failover_manager, replication_manager)
        plan_status = self.check_plan_freshness(untested_plans or [])

        # Determine overall status
        statuses = [repl_status, plan_status]
        if DRHealthStatus.CRITICAL in statuses:
            overall = DRHealthStatus.CRITICAL
        elif DRHealthStatus.WARNING in statuses:
            overall = DRHealthStatus.WARNING
        else:
            overall = DRHealthStatus.HEALTHY

        if not failover_ready:
            overall = DRHealthStatus.CRITICAL

        return DRHealthReport(
            status=overall,
            timestamp=time.time(),
            replication_summary=replication_manager.summary(),
            failover_ready=failover_ready,
            untested_plans=untested_plans or [],
            active_alerts=len(self.active_alerts()),
            details={
                "replication_status": repl_status.value,
                "plan_status": plan_status.value,
            },
        )
