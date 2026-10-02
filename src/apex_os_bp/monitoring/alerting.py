"""Alerting system for APEX-OS.

Provides alert rules, threshold evaluation, severity levels,
and notification channels for alerting on system conditions.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

    @property
    def priority(self) -> int:
        """Numeric priority for comparison."""
        levels = {
            AlertSeverity.INFO: 1,
            AlertSeverity.WARNING: 2,
            AlertSeverity.CRITICAL: 3,
        }
        return levels[self]

    def __ge__(self, other: "AlertSeverity") -> bool:
        return self.priority >= other.priority

    def __gt__(self, other: "AlertSeverity") -> bool:
        return self.priority > other.priority


@dataclass
class AlertRule:
    """An alert rule with a condition and threshold."""

    name: str
    description: str
    severity: AlertSeverity
    metric_name: str
    threshold: float
    comparison: str  # "gt", "lt", "gte", "lte", "eq"
    duration: float = 0.0  # seconds the condition must hold
    labels: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    cooldown: float = 300.0  # seconds between repeated alerts

    def evaluate(self, value: float) -> bool:
        """Evaluate the rule against a metric value."""
        if not self.enabled:
            return False
        ops = {
            "gt": lambda v, t: v > t,
            "lt": lambda v, t: v < t,
            "gte": lambda v, t: v >= t,
            "lte": lambda v, t: v <= t,
            "eq": lambda v, t: v == t,
        }
        op = ops.get(self.comparison)
        if op is None:
            raise ValueError(f"Unknown comparison operator: {self.comparison}")
        return op(value, self.threshold)


@dataclass
class Alert:
    """A fired alert instance."""

    rule_name: str
    severity: AlertSeverity
    message: str
    value: float
    threshold: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp,
            "labels": self.labels,
            "acknowledged": self.acknowledged,
        }


class NotificationChannel:
    """Base class for notification channels."""

    def send(self, alert: Alert) -> bool:
        """Send an alert notification. Returns True on success."""
        raise NotImplementedError


class WebhookChannel(NotificationChannel):
    """Webhook-based notification channel."""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 10.0):
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout

    def send(self, alert: Alert) -> bool:
        """Send alert via HTTP webhook."""
        try:
            data = json.dumps(alert.to_dict()).encode("utf-8")
            req = urllib.request.Request(
                self.url,
                data=data,
                headers=self.headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return 200 <= resp.status < 300
        except Exception:
            return False


class CallbackChannel(NotificationChannel):
    """Callback-based notification channel."""

    def __init__(self, callback: Callable[[Alert], None]):
        self.callback = callback

    def send(self, alert: Alert) -> bool:
        """Send alert via callback."""
        try:
            self.callback(alert)
            return True
        except Exception:
            return False


class AlertManager:
    """Manages alert rules, evaluates conditions, and dispatches notifications."""

    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._channels: List[NotificationChannel] = []
        self._alerts: List[Alert] = []
        self._last_fired: Dict[str, float] = {}
        self._condition_since: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._alert_handlers: List[Callable[[Alert], None]] = []

    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        with self._lock:
            self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> None:
        """Remove an alert rule."""
        with self._lock:
            self._rules.pop(name, None)

    def get_rule(self, name: str) -> Optional[AlertRule]:
        """Get an alert rule by name."""
        with self._lock:
            return self._rules.get(name)

    def list_rules(self) -> List[AlertRule]:
        """List all alert rules."""
        with self._lock:
            return list(self._rules.values())

    def add_channel(self, channel: NotificationChannel) -> None:
        """Add a notification channel."""
        self._channels.append(channel)

    def remove_channel(self, channel: NotificationChannel) -> None:
        """Remove a notification channel."""
        if channel in self._channels:
            self._channels.remove(channel)

    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add a handler that is called when an alert fires."""
        self._alert_handlers.append(handler)

    def evaluate(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None) -> List[Alert]:
        """Evaluate all rules against a metric value. Returns fired alerts."""
        fired: List[Alert] = []
        labels = labels or {}
        now = time.time()

        with self._lock:
            rules = list(self._rules.values())

        for rule in rules:
            if rule.metric_name != metric_name:
                continue
            if not rule.enabled:
                continue

            # Check label matching
            labels_match = all(
                rule.labels.get(k) == v for k, v in labels.items()
            ) and all(
                labels.get(k) == v for k, v in rule.labels.items()
            )
            if not labels_match:
                continue

            if rule.evaluate(value):
                # Check duration
                if rule.duration > 0:
                    key = f"{metric_name}:{json.dumps(labels, sort_keys=True)}"
                    if key not in self._condition_since:
                        self._condition_since[key] = now
                        continue
                    elif now - self._condition_since[key] < rule.duration:
                        continue
                    else:
                        del self._condition_since[key]
                else:
                    key = f"{metric_name}:{json.dumps(labels, sort_keys=True)}"
                    self._condition_since.pop(key, None)

                # Check cooldown
                last = self._last_fired.get(rule.name, 0)
                if now - last < rule.cooldown:
                    continue
                self._last_fired[rule.name] = now

                alert = Alert(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=f"Alert '{rule.name}': {rule.description} (value={value}, threshold={rule.threshold})",
                    value=value,
                    threshold=rule.threshold,
                    labels=labels,
                )
                fired.append(alert)
            else:
                # Reset condition timer if condition no longer holds
                key = f"{metric_name}:{json.dumps(labels, sort_keys=True)}"
                self._condition_since.pop(key, None)

        # Dispatch alerts
        for alert in fired:
            self._dispatch(alert)

        return fired

    def _dispatch(self, alert: Alert) -> None:
        """Dispatch an alert to all channels and handlers."""
        with self._lock:
            self._alerts.append(alert)

        for channel in self._channels:
            try:
                channel.send(alert)
            except Exception:
                pass

        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception:
                pass

    def get_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Alert]:
        """Get alerts with optional filtering."""
        with self._lock:
            alerts = list(self._alerts)

        if severity is not None:
            alerts = [a for a in alerts if a.severity == severity]
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]

        return alerts[-limit:]

    def acknowledge(self, rule_name: str) -> int:
        """Acknowledge all alerts for a rule. Returns count acknowledged."""
        with self._lock:
            count = 0
            for alert in self._alerts:
                if alert.rule_name == rule_name and not alert.acknowledged:
                    alert.acknowledged = True
                    count += 1
            return count

    def clear_alerts(self) -> None:
        """Clear all alerts."""
        with self._lock:
            self._alerts.clear()
            self._last_fired.clear()
            self._condition_since.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get alert manager statistics."""
        with self._lock:
            return {
                "rules": len(self._rules),
                "channels": len(self._channels),
                "total_alerts": len(self._alerts),
                "unacknowledged": sum(1 for a in self._alerts if not a.acknowledged),
            }
