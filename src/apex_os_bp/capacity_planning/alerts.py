"""Capacity alerts module."""

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class CapacityAlert:
    """A capacity alert."""

    severity: AlertSeverity
    resource: str
    message: str
    metric: str
    threshold: float
    current_value: float

    def to_dict(self) -> dict:
        """Convert alert to dictionary."""
        return {
            "severity": self.severity.value,
            "resource": self.resource,
            "message": self.message,
            "metric": self.metric,
            "threshold": self.threshold,
            "current_value": self.current_value,
        }


def check_capacity_alerts(
    metrics: Dict[str, float],
    thresholds: Dict[str, Dict[str, float]],
) -> List[CapacityAlert]:
    """Check capacity metrics against thresholds and generate alerts.

    Args:
        metrics: Dictionary of metric names to current values.
        thresholds: Dictionary of metric names to threshold configs.
            Each config should have 'warning' and 'critical' keys.

    Returns:
        List of CapacityAlert objects.
    """
    alerts = []

    for metric_name, current_value in metrics.items():
        if metric_name not in thresholds:
            continue

        config = thresholds[metric_name]
        warning_threshold = config.get("warning", float("inf"))
        critical_threshold = config.get("critical", float("inf"))

        if current_value >= critical_threshold:
            alerts.append(
                CapacityAlert(
                    severity=AlertSeverity.CRITICAL,
                    resource=metric_name,
                    message=f"CRITICAL: {metric_name} at {current_value:.2f} exceeds critical threshold {critical_threshold:.2f}",
                    metric=metric_name,
                    threshold=critical_threshold,
                    current_value=current_value,
                )
            )
        elif current_value >= warning_threshold:
            alerts.append(
                CapacityAlert(
                    severity=AlertSeverity.WARNING,
                    resource=metric_name,
                    message=f"WARNING: {metric_name} at {current_value:.2f} exceeds warning threshold {warning_threshold:.2f}",
                    metric=metric_name,
                    threshold=warning_threshold,
                    current_value=current_value,
                )
            )

    return alerts


def format_alert(alert: CapacityAlert) -> str:
    """Format an alert as a human-readable string.

    Args:
        alert: The capacity alert to format.

    Returns:
        Formatted alert string.
    """
    return f"[{alert.severity.value.upper()}] {alert.resource}: {alert.message}"