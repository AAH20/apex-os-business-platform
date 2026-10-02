"""Integration Monitoring — metrics, health checks, and alerting."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Optional


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MetricSnapshot:
    name: str
    value: float
    metric_type: MetricType
    timestamp: float = field(default_factory=time.time)
    labels: dict[str, str] = field(default_factory=dict)
    unit: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "timestamp": self.timestamp,
            "labels": self.labels,
            "unit": self.unit,
        }


@dataclass
class HealthCheck:
    name: str
    check_fn: Callable[[], Awaitable[bool]]
    interval: float = 60.0
    timeout: float = 10.0
    enabled: bool = True
    last_status: bool = True
    last_check: float = 0.0
    consecutive_failures: int = 0
    max_failures: int = 3

    @property
    def is_healthy(self) -> bool:
        return self.consecutive_failures < self.max_failures


@dataclass
class Alert:
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    severity: AlertSeverity = AlertSeverity.INFO
    message: str = ""
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False
    resolved: bool = False
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "name": self.name,
            "severity": self.severity.value,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "context": self.context,
        }


@dataclass
class AlertRule:
    name: str
    metric_name: str
    condition: str  # ">", "<", ">=", "<=", "==", "!="
    threshold: float
    severity: AlertSeverity = AlertSeverity.WARNING
    source: str = ""
    enabled: bool = True
    cooldown: float = 300.0
    last_triggered: float = 0.0
    description: str = ""

    def evaluate(self, value: float) -> bool:
        ops = {
            ">": lambda v, t: v > t,
            "<": lambda v, t: v < t,
            ">=": lambda v, t: v >= t,
            "<=": lambda v, t: v <= t,
            "==": lambda v, t: v == t,
            "!=": lambda v, t: v != t,
        }
        fn = ops.get(self.condition)
        return fn(value, self.threshold) if fn else False

    def can_trigger(self) -> bool:
        return time.time() - self.last_triggered >= self.cooldown


class IntegrationMonitor:
    """Monitor integration health, metrics, and alerts."""

    def __init__(self, name: str = "default"):
        self.name = name
        self._metrics: dict[str, list[MetricSnapshot]] = {}
        self._max_metric_history: int = 1000
        self._health_checks: dict[str, HealthCheck] = {}
        self._alerts: list[Alert] = []
        self._alert_rules: dict[str, AlertRule] = {}
        self._max_alerts: int = 5000
        self._alert_handlers: list[Callable[[Alert], None]] = []
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
        self._timers: dict[str, list[float]] = {}

    # ── Metric Recording ──

    def record_counter(self, name: str, value: float = 1.0, labels: Optional[dict] = None) -> None:
        self._counters[name] = self._counters.get(name, 0.0) + value
        self._store_metric(MetricSnapshot(
            name=name, value=self._counters[name],
            metric_type=MetricType.COUNTER, labels=labels or {},
        ))

    def record_gauge(self, name: str, value: float, labels: Optional[dict] = None) -> None:
        self._gauges[name] = value
        self._store_metric(MetricSnapshot(
            name=name, value=value,
            metric_type=MetricType.GAUGE, labels=labels or {},
        ))

    def record_histogram(self, name: str, value: float, labels: Optional[dict] = None) -> None:
        if name not in self._histograms:
            self._histograms[name] = []
        self._histograms[name].append(value)
        if len(self._histograms[name]) > self._max_metric_history:
            self._histograms[name] = self._histograms[name][-self._max_metric_history:]
        self._store_metric(MetricSnapshot(
            name=name, value=value,
            metric_type=MetricType.HISTOGRAM, labels=labels or {},
        ))

    def record_timer(self, name: str, value: float, labels: Optional[dict] = None) -> None:
        if name not in self._timers:
            self._timers[name] = []
        self._timers[name].append(value)
        if len(self._timers[name]) > self._max_metric_history:
            self._timers[name] = self._timers[name][-self._max_metric_history:]
        self._store_metric(MetricSnapshot(
            name=name, value=value,
            metric_type=MetricType.TIMER, labels=labels or {},
        ))

    def _store_metric(self, snapshot: MetricSnapshot) -> None:
        if snapshot.name not in self._metrics:
            self._metrics[snapshot.name] = []
        self._metrics[snapshot.name].append(snapshot)
        if len(self._metrics[snapshot.name]) > self._max_metric_history:
            self._metrics[snapshot.name] = self._metrics[snapshot.name][-self._max_metric_history:]
        self._evaluate_alert_rules(snapshot)

    # ── Metric Querying ──

    def get_metric(self, name: str, last_n: int = 1) -> list[MetricSnapshot]:
        return self._metrics.get(name, [])[-last_n:]

    def get_counter(self, name: str) -> float:
        return self._counters.get(name, 0.0)

    def get_gauge(self, name: str) -> float:
        return self._gauges.get(name, 0.0)

    def get_histogram_stats(self, name: str) -> dict[str, float]:
        values = self._histograms.get(name, [])
        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": n,
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "avg": sum(sorted_vals) / n,
            "p50": sorted_vals[int(n * 0.5)],
            "p95": sorted_vals[int(n * 0.95)],
            "p99": sorted_vals[int(n * 0.99)],
        }

    def get_timer_stats(self, name: str) -> dict[str, float]:
        values = self._timers.get(name, [])
        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": n,
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "avg": sum(sorted_vals) / n,
            "p50": sorted_vals[int(n * 0.5)],
            "p95": sorted_vals[int(n * 0.95)],
            "p99": sorted_vals[int(n * 0.99)],
        }

    def get_all_metrics(self) -> dict[str, list[MetricSnapshot]]:
        return {k: list(v) for k, v in self._metrics.items()}

    # ── Health Checks ──

    def register_health_check(self, check: HealthCheck) -> None:
        self._health_checks[check.name] = check

    def unregister_health_check(self, name: str) -> None:
        self._health_checks.pop(name, None)

    async def run_health_check(self, name: str) -> bool:
        check = self._health_checks.get(name)
        if not check or not check.enabled:
            return True
        try:
            result = await asyncio.wait_for(check.check_fn(), timeout=check.timeout)
            check.last_status = result
            check.last_check = time.time()
            if result:
                check.consecutive_failures = 0
            else:
                check.consecutive_failures += 1
            return result
        except Exception:
            check.last_status = False
            check.last_check = time.time()
            check.consecutive_failures += 1
            return False

    async def run_all_health_checks(self) -> dict[str, bool]:
        results = {}
        for name in self._health_checks:
            results[name] = await self.run_health_check(name)
        return results

    def get_overall_health(self) -> HealthStatus:
        if not self._health_checks:
            return HealthStatus.UNKNOWN
        checks = list(self._health_checks.values())
        healthy_count = sum(1 for c in checks if c.is_healthy)
        if healthy_count == len(checks):
            return HealthStatus.HEALTHY
        if healthy_count == 0:
            return HealthStatus.UNHEALTHY
        return HealthStatus.DEGRADED

    def get_health_check_status(self) -> dict[str, dict]:
        return {
            name: {
                "healthy": check.is_healthy,
                "last_status": check.last_status,
                "last_check": check.last_check,
                "consecutive_failures": check.consecutive_failures,
            }
            for name, check in self._health_checks.items()
        }

    # ── Alerting ──

    def add_alert_rule(self, rule: AlertRule) -> None:
        self._alert_rules[rule.name] = rule

    def remove_alert_rule(self, name: str) -> None:
        self._alert_rules.pop(name, None)

    def _evaluate_alert_rules(self, snapshot: MetricSnapshot) -> None:
        for rule in self._alert_rules.values():
            if not rule.enabled or rule.metric_name != snapshot.name:
                continue
            if not rule.can_trigger():
                continue
            if rule.evaluate(snapshot.value):
                rule.last_triggered = time.time()
                alert = Alert(
                    name=rule.name,
                    severity=rule.severity,
                    message=f"Alert '{rule.name}': {snapshot.name} = {snapshot.value} "
                            f"({rule.condition} {rule.threshold})",
                    source=rule.source or self.name,
                    context={
                        "metric_name": snapshot.name,
                        "metric_value": snapshot.value,
                        "condition": rule.condition,
                        "threshold": rule.threshold,
                        "labels": snapshot.labels,
                    },
                )
                self._trigger_alert(alert)

    def _trigger_alert(self, alert: Alert) -> None:
        self._alerts.append(alert)
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts:]
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception:
                pass

    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        self._alert_handlers.append(handler)

    def remove_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        if handler in self._alert_handlers:
            self._alert_handlers.remove(handler)

    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        acknowledged: Optional[bool] = None,
        resolved: Optional[bool] = None,
        limit: int = 100,
    ) -> list[Alert]:
        alerts = self._alerts
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]
        return alerts[-limit:]

    def acknowledge_alert(self, alert_id: str) -> bool:
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                return True
        return False

    # ── Monitoring Loop ──

    async def start_monitoring(self, interval: float = 60.0) -> None:
        """Start the background health check loop."""
        if self._running:
            return
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))

    async def stop_monitoring(self) -> None:
        """Stop the background health check loop."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    async def _monitor_loop(self, interval: float) -> None:
        while self._running:
            try:
                await self.run_all_health_checks()
            except Exception:
                pass
            await asyncio.sleep(interval)

    # ── Reporting ──

    def get_summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "overall_health": self.get_overall_health().value,
            "health_checks": self.get_health_check_status(),
            "metric_count": len(self._metrics),
            "counter_count": len(self._counters),
            "gauge_count": len(self._gauges),
            "alert_count": len(self._alerts),
            "unacknowledged_alerts": len([a for a in self._alerts if not a.acknowledged]),
            "unresolved_alerts": len([a for a in self._alerts if not a.resolved]),
        }

    def clear(self) -> None:
        self._metrics.clear()
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._timers.clear()
        self._alerts.clear()
        self._alert_rules.clear()
        self._health_checks.clear()
