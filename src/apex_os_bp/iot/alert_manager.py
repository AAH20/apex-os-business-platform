"""Alert management module for the IoT platform.

Manages alert creation, lifecycle, acknowledgment, resolution,
and notification routing for IoT device alerts.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


class AlertSeverity(str, Enum):
    """Severity levels for alerts."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Lifecycle states for an alert."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    EXPIRED = "expired"


@dataclass
class Alert:
    """Represents an IoT alert.

    Attributes:
        alert_id: Unique alert identifier.
        device_id: Device that triggered the alert.
        alert_type: Type of alert (e.g., 'threshold_exceeded').
        severity: Alert severity level.
        status: Current alert status.
        message: Human-readable alert message.
        value: The value that triggered the alert.
        threshold: The threshold that was crossed.
        created_at: When the alert was created.
        acknowledged_at: When the alert was acknowledged.
        resolved_at: When the alert was resolved.
        acknowledged_by: Who acknowledged the alert.
        resolved_by: Who resolved the alert.
        resolution_note: Note added on resolution.
        metadata: Additional context.
        notification_channels: Channels to notify.
    """

    alert_id: str
    device_id: str
    alert_type: str
    severity: AlertSeverity
    message: str
    status: AlertStatus = AlertStatus.ACTIVE
    value: float | None = None
    threshold: float | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    acknowledged_by: str | None = None
    resolved_by: str | None = None
    resolution_note: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    notification_channels: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize alert to a dictionary."""
        return {
            "alert_id": self.alert_id,
            "device_id": self.device_id,
            "alert_type": self.alert_type,
            "severity": self.severity.value,
            "status": self.status.value,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_by": self.resolved_by,
            "resolution_note": self.resolution_note,
            "metadata": dict(self.metadata),
            "notification_channels": list(self.notification_channels),
        }

    @property
    def is_active(self) -> bool:
        """Whether the alert is still active."""
        return self.status == AlertStatus.ACTIVE

    @property
    def age_seconds(self) -> float:
        """Age of the alert in seconds."""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()


@dataclass
class AlertRule:
    """Defines a rule for automatically creating alerts.

    Attributes:
        rule_id: Unique rule identifier.
        name: Human-readable rule name.
        device_id: Device to monitor (or '*' for all devices).
        sensor_type: Sensor type to monitor.
        condition: Comparison operator ('gt', 'lt', 'gte', 'lte', 'eq', 'neq').
        threshold: Threshold value.
        severity: Severity to assign.
        message_template: Alert message template.
        enabled: Whether the rule is active.
        cooldown_seconds: Minimum seconds between alerts from this rule.
        last_triggered: When the rule last fired.
    """

    rule_id: str
    name: str
    device_id: str
    sensor_type: str
    condition: str
    threshold: float
    severity: AlertSeverity
    message_template: str = ""
    enabled: bool = True
    cooldown_seconds: float = 60.0
    last_triggered: datetime | None = None

    def evaluate(self, value: float) -> bool:
        """Evaluate the rule against a value.

        Args:
            value: The sensor reading value.

        Returns:
            True if the rule condition is met.
        """
        ops = {
            "gt": lambda v, t: v > t,
            "lt": lambda v, t: v < t,
            "gte": lambda v, t: v >= t,
            "lte": lambda v, t: v <= t,
            "eq": lambda v, t: v == t,
            "neq": lambda v, t: v != t,
        }
        op = ops.get(self.condition)
        if op is None:
            raise ValueError(f"Unknown condition '{self.condition}'")
        return op(value, self.threshold)

    def can_trigger(self) -> bool:
        """Check if the rule can trigger (not in cooldown)."""
        if not self.enabled:
            return False
        if self.last_triggered is None:
            return True
        elapsed = (datetime.now(timezone.utc) - self.last_triggered).total_seconds()
        return elapsed >= self.cooldown_seconds

    def mark_triggered(self) -> None:
        """Mark the rule as having triggered now."""
        self.last_triggered = datetime.now(timezone.utc)


class AlertManager:
    """Manages the lifecycle of IoT alerts.

    Provides alert creation, acknowledgment, resolution, rule-based
    alerting, and notification routing.
    """

    _SEVERITY_ORDER: dict[AlertSeverity, int] = {
        AlertSeverity.CRITICAL: 0,
        AlertSeverity.HIGH: 1,
        AlertSeverity.MEDIUM: 2,
        AlertSeverity.LOW: 3,
        AlertSeverity.INFO: 4,
    }

    def __init__(self) -> None:
        """Initialize the alert manager."""
        self._alerts: dict[str, Alert] = {}
        self._rules: dict[str, AlertRule] = {}
        self._alert_history: list[str] = []
        self._device_alerts: dict[str, list[str]] = {}
        self._notification_handlers: dict[str, Callable[[Alert], None]] = {}

    def create_alert(
        self,
        device_id: str,
        alert_type: str,
        severity: AlertSeverity | str,
        message: str,
        value: float | None = None,
        threshold: float | None = None,
        metadata: dict[str, Any] | None = None,
        notification_channels: list[str] | None = None,
        alert_id: str | None = None,
    ) -> Alert:
        """Create a new alert.

        Args:
            device_id: Device that triggered the alert.
            alert_type: Type of alert.
            severity: Severity level.
            message: Alert message.
            value: Triggering value.
            threshold: Threshold that was crossed.
            metadata: Additional context.
            notification_channels: Channels to notify.
            alert_id: Optional explicit ID.

        Returns:
            The created Alert.
        """
        if isinstance(severity, str):
            severity = AlertSeverity(severity)

        aid = alert_id or str(uuid.uuid4())
        alert = Alert(
            alert_id=aid,
            device_id=device_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            value=value,
            threshold=threshold,
            metadata=metadata or {},
            notification_channels=notification_channels or [],
        )
        self._alerts[aid] = alert
        self._alert_history.append(aid)

        if device_id not in self._device_alerts:
            self._device_alerts[device_id] = []
        self._device_alerts[device_id].append(aid)

        # Send notifications
        self._notify(alert)

        return alert

    def get_alert(self, alert_id: str) -> Alert:
        """Retrieve an alert by ID.

        Args:
            alert_id: The alert identifier.

        Returns:
            The Alert instance.

        Raises:
            KeyError: If the alert does not exist.
        """
        if alert_id not in self._alerts:
            raise KeyError(f"Alert '{alert_id}' not found")
        return self._alerts[alert_id]

    def acknowledge(
        self,
        alert_id: str,
        acknowledged_by: str = "system",
    ) -> Alert:
        """Acknowledge an alert.

        Args:
            alert_id: The alert to acknowledge.
            acknowledged_by: Who is acknowledging.

        Returns:
            The updated Alert.

        Raises:
            ValueError: If the alert is not active.
        """
        alert = self.get_alert(alert_id)
        if alert.status != AlertStatus.ACTIVE:
            raise ValueError(
                f"Cannot acknowledge alert in status '{alert.status.value}'"
            )
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = acknowledged_by
        return alert

    def resolve(
        self,
        alert_id: str,
        resolved_by: str = "system",
        resolution_note: str = "",
    ) -> Alert:
        """Resolve an alert.

        Args:
            alert_id: The alert to resolve.
            resolved_by: Who is resolving.
            resolution_note: Optional resolution note.

        Returns:
            The updated Alert.
        """
        alert = self.get_alert(alert_id)
        if alert.status in (AlertStatus.RESOLVED, AlertStatus.EXPIRED):
            raise ValueError(
                f"Cannot resolve alert in status '{alert.status.value}'"
            )
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolved_by = resolved_by
        alert.resolution_note = resolution_note
        return alert

    def suppress(self, alert_id: str) -> Alert:
        """Suppress an alert (hide from active views).

        Args:
            alert_id: The alert to suppress.

        Returns:
            The updated Alert.
        """
        alert = self.get_alert(alert_id)
        alert.status = AlertStatus.SUPPRESSED
        return alert

    def expire(self, alert_id: str) -> Alert:
        """Mark an alert as expired.

        Args:
            alert_id: The alert to expire.

        Returns:
            The updated Alert.
        """
        alert = self.get_alert(alert_id)
        alert.status = AlertStatus.EXPIRED
        return alert

    def list_alerts(
        self,
        status: AlertStatus | str | None = None,
        severity: AlertSeverity | str | None = None,
        device_id: str | None = None,
        alert_type: str | None = None,
        active_only: bool = False,
    ) -> list[Alert]:
        """List alerts with optional filtering.

        Args:
            status: Filter by status.
            severity: Filter by severity.
            device_id: Filter by device.
            alert_type: Filter by alert type.
            active_only: If True, only return active alerts.

        Returns:
            List of matching alerts.
        """
        results = list(self._alerts.values())

        if active_only:
            results = [a for a in results if a.status == AlertStatus.ACTIVE]
        if status is not None:
            if isinstance(status, str):
                status = AlertStatus(status)
            results = [a for a in results if a.status == status]
        if severity is not None:
            if isinstance(severity, str):
                severity = AlertSeverity(severity)
            results = [a for a in results if a.severity == severity]
        if device_id is not None:
            results = [a for a in results if a.device_id == device_id]
        if alert_type is not None:
            results = [a for a in results if a.alert_type == alert_type]

        # Sort by severity then creation time
        results.sort(key=lambda a: (self._SEVERITY_ORDER[a.severity], a.created_at), reverse=False)
        return results

    def get_active_alerts(self) -> list[Alert]:
        """Get all active alerts sorted by severity."""
        return self.list_alerts(active_only=True)

    def get_critical_alerts(self) -> list[Alert]:
        """Get all active critical alerts."""
        return self.list_alerts(severity=AlertSeverity.CRITICAL, active_only=True)

    def get_alert_count(
        self,
        status: AlertStatus | str | None = None,
        severity: AlertSeverity | str | None = None,
    ) -> int:
        """Get the count of alerts matching filters.

        Args:
            status: Optional status filter.
            severity: Optional severity filter.

        Returns:
            Alert count.
        """
        return len(self.list_alerts(status=status, severity=severity))

    def add_rule(
        self,
        name: str,
        device_id: str,
        sensor_type: str,
        condition: str,
        threshold: float,
        severity: AlertSeverity | str,
        message_template: str = "",
        cooldown_seconds: float = 60.0,
        rule_id: str | None = None,
    ) -> AlertRule:
        """Add an alert rule.

        Args:
            name: Rule name.
            device_id: Device to monitor ('*' for all).
            sensor_type: Sensor type to monitor.
            condition: Comparison operator.
            threshold: Threshold value.
            severity: Severity to assign.
            message_template: Message template.
            cooldown_seconds: Cooldown period.
            rule_id: Optional explicit ID.

        Returns:
            The created AlertRule.
        """
        if isinstance(severity, str):
            severity = AlertSeverity(severity)

        rid = rule_id or str(uuid.uuid4())
        rule = AlertRule(
            rule_id=rid,
            name=name,
            device_id=device_id,
            sensor_type=sensor_type,
            condition=condition,
            threshold=threshold,
            severity=severity,
            message_template=message_template or f"{name}: {{value}} {condition} {threshold}",
            cooldown_seconds=cooldown_seconds,
        )
        self._rules[rid] = rule
        return rule

    def remove_rule(self, rule_id: str) -> None:
        """Remove an alert rule.

        Args:
            rule_id: The rule to remove.

        Raises:
            KeyError: If the rule does not exist.
        """
        if rule_id not in self._rules:
            raise KeyError(f"Rule '{rule_id}' not found")
        del self._rules[rule_id]

    def evaluate_rules(
        self,
        device_id: str,
        sensor_type: str,
        value: float,
    ) -> list[Alert]:
        """Evaluate all applicable rules against a reading.

        Args:
            device_id: Device that produced the reading.
            sensor_type: Sensor type.
            value: Reading value.

        Returns:
            List of alerts created by triggered rules.
        """
        triggered: list[Alert] = []
        for rule in self._rules.values():
            if not rule.can_trigger():
                continue
            if rule.device_id not in (device_id, "*"):
                continue
            if rule.sensor_type != sensor_type:
                continue
            if rule.evaluate(value):
                rule.mark_triggered()
                msg = rule.message_template.format(
                    value=value,
                    threshold=rule.threshold,
                    device_id=device_id,
                    sensor_type=sensor_type,
                )
                alert = self.create_alert(
                    device_id=device_id,
                    alert_type=rule.name,
                    severity=rule.severity,
                    message=msg,
                    value=value,
                    threshold=rule.threshold,
                    metadata={"rule_id": rule.rule_id},
                )
                triggered.append(alert)
        return triggered

    def register_notification_handler(
        self,
        channel: str,
        handler: Callable[[Alert], None],
    ) -> None:
        """Register a notification handler for a channel.

        Args:
            channel: Channel name (e.g., 'email', 'sms', 'webhook').
            handler: Callable that accepts an Alert.
        """
        self._notification_handlers[channel] = handler

    def clear(self) -> None:
        """Clear all alerts and rules."""
        self._alerts.clear()
        self._rules.clear()
        self._alert_history.clear()
        self._device_alerts.clear()
        self._notification_handlers.clear()

    def _notify(self, alert: Alert) -> None:
        """Send notifications for an alert."""
        for channel in alert.notification_channels:
            handler = self._notification_handlers.get(channel)
            if handler:
                handler(alert)
