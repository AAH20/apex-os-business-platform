"""Model monitoring component for APEX-OS ML Platform."""

from __future__ import annotations

import math
import statistics
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class Metric:
    """A single metric data point."""

    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "labels": self.labels,
        }


@dataclass
class Alert:
    """An alert triggered by a monitoring rule."""

    alert_id: str
    metric_name: str
    severity: str  # "info", "warning", "critical"
    message: str
    threshold: float
    observed_value: float
    timestamp: float
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "metric_name": self.metric_name,
            "severity": self.severity,
            "message": self.message,
            "threshold": self.threshold,
            "observed_value": self.observed_value,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
        }


@dataclass
class MonitoringRule:
    """A rule for triggering alerts."""

    metric_name: str
    threshold: float
    comparison: str  # "gt", "lt", "gte", "lte"
    severity: str = "warning"
    description: str = ""

    def check(self, value: float) -> bool:
        """Check if a value violates this rule."""
        if self.comparison == "gt":
            return value > self.threshold
        if self.comparison == "lt":
            return value < self.threshold
        if self.comparison == "gte":
            return value >= self.threshold
        if self.comparison == "lte":
            return value <= self.threshold
        return False


class ModelMonitor:
    """Monitors model performance, data drift, and system health."""

    def __init__(self, max_history: int = 10000):
        self._metrics: Dict[str, List[Metric]] = {}
        self._alerts: List[Alert] = []
        self._rules: List[MonitoringRule] = []
        self._max_history = max_history
        self._lock = threading.Lock()
        self._alert_counter = 0

    def record_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a metric data point."""
        metric = Metric(
            name=name,
            value=value,
            timestamp=time.time(),
            labels=labels or {},
        )
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
            self._metrics[name].append(metric)
            # Trim history
            if len(self._metrics[name]) > self._max_history:
                self._metrics[name] = self._metrics[name][-self._max_history :]

            # Check rules
            self._check_rules(metric)

    def record_prediction(
        self,
        model_id: str,
        prediction: float,
        actual: Optional[float] = None,
        latency_ms: Optional[float] = None,
    ) -> None:
        """Record a prediction event."""
        labels = {"model_id": model_id}
        self.record_metric("prediction_value", prediction, labels)

        if actual is not None:
            error = abs(prediction - actual)
            self.record_metric("prediction_error", error, labels)
            self.record_metric("prediction_accuracy", 1.0 if error < 0.1 else 0.0, labels)

        if latency_ms is not None:
            self.record_metric("prediction_latency_ms", latency_ms, labels)

    def add_rule(self, rule: MonitoringRule) -> None:
        """Add a monitoring rule."""
        with self._lock:
            self._rules.append(rule)

    def remove_rule(self, metric_name: str) -> None:
        """Remove all rules for a metric."""
        with self._lock:
            self._rules = [r for r in self._rules if r.metric_name != metric_name]

    def get_metrics(
        self,
        name: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> List[Metric]:
        """Get metrics filtered by time range."""
        with self._lock:
            if name not in self._metrics:
                return []
            metrics = self._metrics[name]
            if start_time is not None:
                metrics = [m for m in metrics if m.timestamp >= start_time]
            if end_time is not None:
                metrics = [m for m in metrics if m.timestamp <= end_time]
            return list(metrics)

    def get_metric_stats(self, name: str) -> Dict[str, float]:
        """Get statistics for a metric."""
        with self._lock:
            if name not in self._metrics or not self._metrics[name]:
                return {}
            values = [m.value for m in self._metrics[name]]
            return {
                "count": len(values),
                "mean": statistics.mean(values),
                "std": statistics.stdev(values) if len(values) > 1 else 0.0,
                "min": min(values),
                "max": max(values),
                "p50": statistics.median(values),
                "p95": self._percentile(values, 95),
                "p99": self._percentile(values, 99),
            }

    def get_alerts(
        self,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
    ) -> List[Alert]:
        """Get alerts with optional filtering."""
        with self._lock:
            alerts = self._alerts
            if severity is not None:
                alerts = [a for a in alerts if a.severity == severity]
            if acknowledged is not None:
                alerts = [a for a in alerts if a.acknowledged == acknowledged]
            return list(alerts)

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert by ID."""
        with self._lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    return True
        return False

    def detect_drift(
        self,
        metric_name: str,
        reference_window: Tuple[float, float],
        current_window: Tuple[float, float],
        threshold_std: float = 2.0,
    ) -> Dict[str, Any]:
        """Detect data drift by comparing metric distributions.

        Args:
            metric_name: Name of the metric to check.
            reference_window: (start, end) timestamps for reference period.
            current_window: (start, end) timestamps for current period.
            threshold_std: Number of standard deviations for drift detection.

        Returns:
            Drift detection result with statistics.
        """
        ref_metrics = self.get_metrics(metric_name, reference_window[0], reference_window[1])
        cur_metrics = self.get_metrics(metric_name, current_window[0], current_window[1])

        if not ref_metrics or not cur_metrics:
            return {
                "drift_detected": False,
                "reason": "insufficient_data",
                "reference_mean": None,
                "current_mean": None,
            }

        ref_values = [m.value for m in ref_metrics]
        cur_values = [m.value for m in cur_metrics]

        ref_mean = statistics.mean(ref_values)
        ref_std = statistics.stdev(ref_values) if len(ref_values) > 1 else 0.0
        cur_mean = statistics.mean(cur_values)

        if ref_std == 0:
            drift_detected = abs(cur_mean - ref_mean) > 0.01
            z_score = float("inf") if drift_detected else 0.0
        else:
            z_score = (cur_mean - ref_mean) / ref_std
            drift_detected = abs(z_score) > threshold_std

        return {
            "drift_detected": drift_detected,
            "z_score": z_score,
            "reference_mean": ref_mean,
            "reference_std": ref_std,
            "current_mean": cur_mean,
            "threshold_std": threshold_std,
        }

    def get_model_health(self, model_id: str) -> Dict[str, Any]:
        """Get health summary for a model."""
        labels = {"model_id": model_id}
        prediction_stats = self.get_metric_stats("prediction_value")
        error_stats = self.get_metric_stats("prediction_error")
        latency_stats = self.get_metric_stats("prediction_latency_ms")

        # Filter by model_id
        with self._lock:
            model_metrics = {}
            for name in ["prediction_value", "prediction_error", "prediction_latency_ms"]:
                if name in self._metrics:
                    model_metrics[name] = [
                        m for m in self._metrics[name] if m.labels.get("model_id") == model_id
                    ]

        health = {
            "model_id": model_id,
            "total_predictions": len(model_metrics.get("prediction_value", [])),
            "average_error": (
                statistics.mean([m.value for m in model_metrics["prediction_error"]])
                if "prediction_error" in model_metrics and model_metrics["prediction_error"]
                else None
            ),
            "average_latency_ms": (
                statistics.mean([m.value for m in model_metrics["prediction_latency_ms"]])
                if "prediction_latency_ms" in model_metrics and model_metrics["prediction_latency_ms"]
                else None
            ),
            "status": "healthy",
        }

        if health["average_error"] is not None and health["average_error"] > 0.5:
            health["status"] = "degraded"
        if health["average_latency_ms"] is not None and health["average_latency_ms"] > 1000:
            health["status"] = "critical"

        return health

    def clear(self) -> None:
        """Clear all metrics and alerts."""
        with self._lock:
            self._metrics.clear()
            self._alerts.clear()
            self._rules.clear()

    def _check_rules(self, metric: Metric) -> None:
        """Check a metric against all rules."""
        for rule in self._rules:
            if rule.metric_name == metric.name and rule.check(metric.value):
                self._alert_counter += 1
                alert = Alert(
                    alert_id=f"alert_{self._alert_counter}",
                    metric_name=metric.name,
                    severity=rule.severity,
                    message=rule.description or f"Metric {metric.name} violated threshold",
                    threshold=rule.threshold,
                    observed_value=metric.value,
                    timestamp=metric.timestamp,
                )
                self._alerts.append(alert)

    def _percentile(self, values: List[float], p: float) -> float:
        """Compute the p-th percentile."""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        k = (len(sorted_vals) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_vals[int(k)]
        return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)
