"""Tenant monitoring — health checks, metrics, and alerting."""

from __future__ import annotations

import logging
import statistics
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from apex_os_bp.multitenancy.models import Alert, HealthStatus

logger = logging.getLogger(__name__)


@dataclass
class MetricSample:
    """A single metric data point."""

    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class MetricsCollector:
    """Collects and aggregates metrics for tenants."""

    max_samples_per_metric: int = 10_000
    _samples: dict[str, dict[str, list[MetricSample]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(list))
    )

    def record(
        self,
        tenant_id: str,
        metric_name: str,
        value: float,
        labels: Optional[dict[str, str]] = None,
    ) -> MetricSample:
        """Record a metric sample for a tenant."""
        sample = MetricSample(
            name=metric_name,
            value=value,
            timestamp=datetime.utcnow(),
            labels=labels or {},
        )
        samples = self._samples[tenant_id][metric_name]
        samples.append(sample)
        # Trim old samples
        if len(samples) > self.max_samples_per_metric:
            self._samples[tenant_id][metric_name] = samples[-self.max_samples_per_metric:]
        return sample

    def get_samples(
        self,
        tenant_id: str,
        metric_name: str,
        since: Optional[datetime] = None,
    ) -> list[MetricSample]:
        """Get samples for a specific metric."""
        samples = self._samples.get(tenant_id, {}).get(metric_name, [])
        if since:
            samples = [s for s in samples if s.timestamp >= since]
        return list(samples)

    def get_aggregate(
        self,
        tenant_id: str,
        metric_name: str,
        aggregation: str = "avg",
        since: Optional[datetime] = None,
    ) -> Optional[float]:
        """Get an aggregated value for a metric."""
        samples = self.get_samples(tenant_id, metric_name, since)
        if not samples:
            return None
        values = [s.value for s in samples]
        if aggregation == "avg":
            return statistics.mean(values)
        elif aggregation == "sum":
            return sum(values)
        elif aggregation == "min":
            return min(values)
        elif aggregation == "max":
            return max(values)
        elif aggregation == "count":
            return float(len(values))
        elif aggregation == "p95":
            sorted_vals = sorted(values)
            idx = int(len(sorted_vals) * 0.95)
            return sorted_vals[min(idx, len(sorted_vals) - 1)]
        elif aggregation == "p99":
            sorted_vals = sorted(values)
            idx = int(len(sorted_vals) * 0.99)
            return sorted_vals[min(idx, len(sorted_vals) - 1)]
        return None

    def get_all_metrics(self, tenant_id: str) -> dict[str, list[MetricSample]]:
        """Get all metrics for a tenant."""
        return dict(self._samples.get(tenant_id, {}))

    def clear(self, tenant_id: str) -> None:
        """Clear all metrics for a tenant."""
        self._samples.pop(tenant_id, None)


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    name: str
    status: HealthStatus
    latency_ms: float
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class TenantMonitor:
    """Monitors tenant health, collects metrics, and manages alerts."""

    def __init__(self) -> None:
        self._collector = MetricsCollector()
        self._alerts: dict[str, list[Alert]] = {}
        self._health_checks: dict[str, Callable[[str], HealthCheckResult]] = {}
        self._alert_rules: list[dict[str, Any]] = []

    def register_health_check(
        self, name: str, check_func: Callable[[str], HealthCheckResult]
    ) -> None:
        """Register a health check function."""
        self._health_checks[name] = check_func

    def register_alert_rule(
        self,
        name: str,
        metric: str,
        condition: str,  # "gt", "lt", "eq"
        threshold: float,
        severity: str = "warning",
        window_minutes: int = 5,
    ) -> None:
        """Register an alert rule."""
        self._alert_rules.append({
            "name": name,
            "metric": metric,
            "condition": condition,
            "threshold": threshold,
            "severity": severity,
            "window_minutes": window_minutes,
        })

    def run_health_checks(self, tenant_id: str) -> list[HealthCheckResult]:
        """Run all registered health checks for a tenant."""
        results = []
        for name, check_func in self._health_checks.items():
            start = time.monotonic()
            try:
                result = check_func(tenant_id)
            except Exception as exc:
                result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=(time.monotonic() - start) * 1000,
                    message=f"Health check failed: {exc}",
                )
            results.append(result)

            # Record latency metric
            self._collector.record(
                tenant_id,
                f"health_check_{name}_latency_ms",
                result.latency_ms,
            )

        return results

    def get_overall_health(self, tenant_id: str) -> HealthStatus:
        """Determine overall health status from all health checks."""
        results = self.run_health_checks(tenant_id)
        if not results:
            return HealthStatus.UNKNOWN

        statuses = [r.status for r in results]
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        return HealthStatus.UNKNOWN

    def check_alerts(self, tenant_id: str) -> list[Alert]:
        """Evaluate alert rules and create alerts for triggered conditions."""
        triggered = []
        now = datetime.utcnow()

        for rule in self._alert_rules:
            window_start = now - timedelta(minutes=rule["window_minutes"])
            value = self._collector.get_aggregate(
                tenant_id, rule["metric"], "avg", window_start
            )
            if value is None:
                continue

            condition = rule["condition"]
            threshold = rule["threshold"]
            is_triggered = False

            if condition == "gt" and value > threshold:
                is_triggered = True
            elif condition == "lt" and value < threshold:
                is_triggered = True
            elif condition == "eq" and value == threshold:
                is_triggered = True

            if is_triggered:
                # Check if there's already an unresolved alert for this rule
                existing = self._find_unresolved_alert(tenant_id, rule["name"])
                if existing:
                    continue

                alert = Alert(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    name=rule["name"],
                    severity=rule["severity"],
                    message=(
                        f"Alert '{rule['name']}': {rule['metric']} "
                        f"is {condition} {threshold} (current: {value:.2f})"
                    ),
                    triggered_at=now,
                    metadata={
                        "metric": rule["metric"],
                        "condition": condition,
                        "threshold": threshold,
                        "current_value": value,
                    },
                )
                if tenant_id not in self._alerts:
                    self._alerts[tenant_id] = []
                self._alerts[tenant_id].append(alert)
                triggered.append(alert)

                logger.warning(
                    "Alert triggered for tenant %s: %s", tenant_id, alert.message
                )

        return triggered

    def resolve_alert(self, tenant_id: str, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        alerts = self._alerts.get(tenant_id, [])
        for alert in alerts:
            if alert.id == alert_id and not alert.is_resolved:
                alert.is_resolved = True
                alert.resolved_at = datetime.utcnow()
                logger.info("Alert %s resolved for tenant %s", alert_id, tenant_id)
                return True
        return False

    def get_alerts(
        self,
        tenant_id: str,
        include_resolved: bool = False,
        severity: Optional[str] = None,
    ) -> list[Alert]:
        """Get alerts for a tenant."""
        alerts = self._alerts.get(tenant_id, [])
        if not include_resolved:
            alerts = [a for a in alerts if not a.is_resolved]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts

    def get_metrics_collector(self) -> MetricsCollector:
        """Get the metrics collector."""
        return self._collector

    def record_metric(
        self,
        tenant_id: str,
        metric_name: str,
        value: float,
        labels: Optional[dict[str, str]] = None,
    ) -> MetricSample:
        """Record a metric for a tenant."""
        return self._collector.record(tenant_id, metric_name, value, labels)

    def get_tenant_dashboard(self, tenant_id: str) -> dict[str, Any]:
        """Get a monitoring dashboard summary for a tenant."""
        health = self.get_overall_health(tenant_id)
        alerts = self.get_alerts(tenant_id)
        critical_alerts = [a for a in alerts if a.severity == "critical"]
        warning_alerts = [a for a in alerts if a.severity == "warning"]

        # Get recent metrics
        recent_metrics: dict[str, Optional[float]] = {}
        all_metrics = self._collector.get_all_metrics(tenant_id)
        for metric_name in all_metrics:
            recent_metrics[metric_name] = self._collector.get_aggregate(
                tenant_id, metric_name, "avg", datetime.utcnow() - timedelta(hours=1)
            )

        return {
            "tenant_id": tenant_id,
            "health": health.value,
            "open_alerts": len(alerts),
            "critical_alerts": len(critical_alerts),
            "warning_alerts": len(warning_alerts),
            "recent_metrics": recent_metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _find_unresolved_alert(self, tenant_id: str, name: str) -> Optional[Alert]:
        """Find an unresolved alert by name for a tenant."""
        alerts = self._alerts.get(tenant_id, [])
        for alert in alerts:
            if alert.name == name and not alert.is_resolved:
                return alert
        return None
