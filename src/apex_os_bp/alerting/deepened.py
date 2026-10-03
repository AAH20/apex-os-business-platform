"""Deepened alerting module: rules, routing, suppression, notification, analytics."""
from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertState(Enum):
    FIRING = "firing"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    name: str
    metric: str
    threshold: float
    severity: Severity
    window_seconds: float = 60.0
    comparison: str = "gt"  # gt, lt, eq
    enabled: bool = True

    def evaluate(self, value: float) -> bool:
        if not self.enabled:
            return False
        if self.comparison == "gt":
            return value > self.threshold
        if self.comparison == "lt":
            return value < self.threshold
        return value == self.threshold


@dataclass
class Alert:
    id: str
    rule_name: str
    severity: Severity
    state: AlertState
    message: str
    source: str
    timestamp: float
    labels: dict[str, str] = field(default_factory=dict)
    resolved_at: float | None = None
    escalation_level: int = 0
    notification_channels: list[str] = field(default_factory=list)


@dataclass
class RoutingRule:
    match_labels: dict[str, str]
    channels: list[str]
    escalation_policy: list[str] = field(default_factory=list)
    escalation_delays: list[float] = field(default_factory=list)


@dataclass
class SuppressionRule:
    match_labels: dict[str, str]
    group_by: list[str] = field(default_factory=list)
    max_alerts: int = 1
    window_seconds: float = 300.0
    cooldown_seconds: float = 600.0


@dataclass
class NotificationChannel:
    name: str
    channel_type: str  # email, slack, webhook, sms
    config: dict[str, Any] = field(default_factory=dict)
    handler: Callable[[Alert], bool] | None = None

    def send(self, alert: Alert) -> bool:
        if self.handler:
            return self.handler(alert)
        return True


class AlertAnalytics:
    def __init__(self) -> None:
        self._alerts: list[Alert] = []
        self._mttr_samples: list[float] = []

    def record(self, alert: Alert) -> None:
        self._alerts.append(alert)
        if alert.state == AlertState.RESOLVED and alert.resolved_at:
            mttr = alert.resolved_at - alert.timestamp
            self._mttr_samples.append(mttr)

    def mttr(self) -> float:
        if not self._mttr_samples:
            return 0.0
        return sum(self._mttr_samples) / len(self._mttr_samples)

    def alert_count(self, state: AlertState | None = None) -> int:
        if state is None:
            return len(self._alerts)
        return sum(1 for a in self._alerts if a.state == state)

    def alerts_by_severity(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for a in self._alerts:
            counts[a.severity.value] += 1
        return dict(counts)

    def top_sources(self, n: int = 5) -> list[tuple[str, int]]:
        counts: dict[str, int] = defaultdict(int)
        for a in self._alerts:
            counts[a.source] += 1
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]


class AlertManager:
    def __init__(self) -> None:
        self.rules: list[AlertRule] = []
        self.routing_rules: list[RoutingRule] = []
        self.suppression_rules: list[SuppressionRule] = []
        self.channels: dict[str, NotificationChannel] = {}
        self.active_alerts: dict[str, Alert] = {}
        self.analytics = AlertAnalytics()
        self._suppression_windows: dict[str, list[float]] = defaultdict(list)
        self._last_suppression: dict[str, float] = {}

    def add_rule(self, rule: AlertRule) -> None:
        self.rules.append(rule)

    def add_routing_rule(self, rule: RoutingRule) -> None:
        self.routing_rules.append(rule)

    def add_suppression_rule(self, rule: SuppressionRule) -> None:
        self.suppression_rules.append(rule)

    def add_channel(self, channel: NotificationChannel) -> None:
        self.channels[channel.name] = channel

    def _match_labels(self, alert_labels: dict[str, str], match: dict[str, str]) -> bool:
        return all(alert_labels.get(k) == v for k, v in match.items())

    def _check_suppression(self, alert: Alert) -> bool:
        for rule in self.suppression_rules:
            if not self._match_labels(alert.labels, rule.match_labels):
                continue
            key = "|".join(f"{k}={alert.labels.get(k, '')}" for k in rule.group_by)
            now = time.time()
            window = self._suppression_windows.setdefault(key, [])
            window[:] = [t for t in window if now - t < rule.window_seconds]
            if len(window) >= rule.max_alerts:
                last = self._last_suppression.get(key, 0)
                if now - last < rule.cooldown_seconds:
                    return True
                self._last_suppression[key] = now
            window.append(now)
        return False

    def _route(self, alert: Alert) -> list[str]:
        for rule in self.routing_rules:
            if self._match_labels(alert.labels, rule.match_labels):
                alert.notification_channels = rule.channels
                return rule.channels
        return []

    def _escalate(self, alert: Alert) -> None:
        for rule in self.routing_rules:
            if self._match_labels(alert.labels, rule.match_labels):
                if alert.escalation_level < len(rule.escalation_policy):
                    next_ch = rule.escalation_policy[alert.escalation_level]
                    if next_ch not in alert.notification_channels:
                        alert.notification_channels.append(next_ch)
                    alert.escalation_level += 1
                return

    def _notify(self, alert: Alert) -> None:
        for ch_name in alert.notification_channels:
            channel = self.channels.get(ch_name)
            if channel:
                channel.send(alert)

    def evaluate(self, metric_name: str, value: float, source: str = "default",
                 labels: dict[str, str] | None = None) -> list[Alert]:
        labels = labels or {}
        fired: list[Alert] = []
        for rule in self.rules:
            if rule.metric != metric_name:
                continue
            if not rule.evaluate(value):
                continue
            alert_id = str(uuid.uuid4())
            alert = Alert(
                id=alert_id,
                rule_name=rule.name,
                severity=rule.severity,
                state=AlertState.FIRING,
                message=f"{rule.name}: {metric_name}={value} (threshold {rule.comparison} {rule.threshold})",
                source=source,
                timestamp=time.time(),
                labels=labels,
            )
            if self._check_suppression(alert):
                alert.state = AlertState.SUPPRESSED
                self.analytics.record(alert)
                continue
            self._route(alert)
            self._notify(alert)
            self.active_alerts[alert_id] = alert
            self.analytics.record(alert)
            fired.append(alert)
        return fired

    def resolve(self, alert_id: str) -> Alert | None:
        alert = self.active_alerts.pop(alert_id, None)
        if alert:
            alert.state = AlertState.RESOLVED
            alert.resolved_at = time.time()
            self.analytics.record(alert)
            self._notify(alert)
        return alert

    def escalate(self, alert_id: str) -> Alert | None:
        alert = self.active_alerts.get(alert_id)
        if alert:
            self._escalate(alert)
            self._notify(alert)
        return alert

    def get_active_alerts(self, severity: Severity | None = None) -> list[Alert]:
        alerts = list(self.active_alerts.values())
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts

    def get_analytics(self) -> AlertAnalytics:
        return self.analytics
