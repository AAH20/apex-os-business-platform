"""Alerting data models."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AlertSeverity(str, Enum):
    """Severity levels for alerts."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Status of an alert."""
    FIRING = "firing"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ESCALATED = "escalated"


class AlertRoutingStrategy(str, Enum):
    """Routing strategies for alerts."""
    BROADCAST = "broadcast"
    ROUND_ROBIN = "round_robin"
    PRIORITY = "priority"
    FAILOVER = "failover"


class EscalationPolicy(str, Enum):
    """Escalation policies."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIXED = "fixed"


@dataclass
class AlertRule:
    """An alert rule that defines conditions for triggering alerts."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    condition: str = ""
    threshold: float = 0.0
    comparison: str = "gt"  # gt, lt, eq, gte, lte
    duration: int = 0  # seconds the condition must hold before firing
    enabled: bool = True
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    routing_strategy: AlertRoutingStrategy = AlertRoutingStrategy.BROADCAST
    escalation_policy: EscalationPolicy = EscalationPolicy.LINEAR
    escalation_delay: int = 300  # seconds before escalation
    max_escalation_level: int = 3
    notification_channels: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert rule to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "condition": self.condition,
            "threshold": self.threshold,
            "comparison": self.comparison,
            "duration": self.duration,
            "enabled": self.enabled,
            "labels": self.labels,
            "annotations": self.annotations,
            "routing_strategy": self.routing_strategy.value,
            "escalation_policy": self.escalation_policy.value,
            "escalation_delay": self.escalation_delay,
            "max_escalation_level": self.max_escalation_level,
            "notification_channels": self.notification_channels,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AlertRule:
        """Create alert rule from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            severity=AlertSeverity(data.get("severity", "warning")),
            condition=data.get("condition", ""),
            threshold=data.get("threshold", 0.0),
            comparison=data.get("comparison", "gt"),
            duration=data.get("duration", 0),
            enabled=data.get("enabled", True),
            labels=data.get("labels", {}),
            annotations=data.get("annotations", {}),
            routing_strategy=AlertRoutingStrategy(data.get("routing_strategy", "broadcast")),
            escalation_policy=EscalationPolicy(data.get("escalation_policy", "linear")),
            escalation_delay=data.get("escalation_delay", 300),
            max_escalation_level=data.get("max_escalation_level", 3),
            notification_channels=data.get("notification_channels", []),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


@dataclass
class Alert:
    """An alert instance."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    rule_id: str = ""
    rule_name: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    status: AlertStatus = AlertStatus.FIRING
    message: str = ""
    source: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    value: float = 0.0
    threshold: float = 0.0
    escalation_level: int = 0
    routing_targets: List[str] = field(default_factory=list)
    notification_channels: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    acknowledged_at: Optional[float] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[float] = None
    escalated_at: Optional[float] = None
    suppressed_at: Optional[float] = None
    suppression_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "status": self.status.value,
            "message": self.message,
            "source": self.source,
            "labels": self.labels,
            "annotations": self.annotations,
            "value": self.value,
            "threshold": self.threshold,
            "escalation_level": self.escalation_level,
            "routing_targets": self.routing_targets,
            "notification_channels": self.notification_channels,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "acknowledged_at": self.acknowledged_at,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at,
            "escalated_at": self.escalated_at,
            "suppressed_at": self.suppressed_at,
            "suppression_reason": self.suppression_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Alert:
        """Create alert from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            rule_id=data.get("rule_id", ""),
            rule_name=data.get("rule_name", ""),
            severity=AlertSeverity(data.get("severity", "warning")),
            status=AlertStatus(data.get("status", "firing")),
            message=data.get("message", ""),
            source=data.get("source", ""),
            labels=data.get("labels", {}),
            annotations=data.get("annotations", {}),
            value=data.get("value", 0.0),
            threshold=data.get("threshold", 0.0),
            escalation_level=data.get("escalation_level", 0),
            routing_targets=data.get("routing_targets", []),
            notification_channels=data.get("notification_channels", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            acknowledged_at=data.get("acknowledged_at"),
            acknowledged_by=data.get("acknowledged_by"),
            resolved_at=data.get("resolved_at"),
            escalated_at=data.get("escalated_at"),
            suppressed_at=data.get("suppressed_at"),
            suppression_reason=data.get("suppression_reason"),
        )


@dataclass
class AlertRoutingTarget:
    """A target for alert routing."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    channel: str = ""
    address: str = ""
    priority: int = 0
    enabled: bool = True
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert routing target to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "channel": self.channel,
            "address": self.address,
            "priority": self.priority,
            "enabled": self.enabled,
            "labels": self.labels,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AlertRoutingTarget:
        """Create routing target from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            channel=data.get("channel", ""),
            address=data.get("address", ""),
            priority=data.get("priority", 0),
            enabled=data.get("enabled", True),
            labels=data.get("labels", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class EscalationRule:
    """An escalation rule defining how alerts escalate."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    alert_rule_id: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    escalation_levels: List[Dict[str, Any]] = field(default_factory=list)
    current_level: int = 0
    max_level: int = 3
    escalation_delay: int = 300
    escalation_policy: EscalationPolicy = EscalationPolicy.LINEAR
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert escalation rule to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "alert_rule_id": self.alert_rule_id,
            "severity": self.severity.value if self.severity else None,
            "escalation_levels": self.escalation_levels,
            "current_level": self.current_level,
            "max_level": self.max_level,
            "escalation_delay": self.escalation_delay,
            "escalation_policy": self.escalation_policy.value,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EscalationRule:
        """Create escalation rule from dictionary."""
        severity = data.get("severity")
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            alert_rule_id=data.get("alert_rule_id"),
            severity=AlertSeverity(severity) if severity else None,
            escalation_levels=data.get("escalation_levels", []),
            current_level=data.get("current_level", 0),
            max_level=data.get("max_level", 3),
            escalation_delay=data.get("escalation_delay", 300),
            escalation_policy=EscalationPolicy(data.get("escalation_policy", "linear")),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


@dataclass
class SuppressionRule:
    """A suppression rule for silencing alerts."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    alert_rule_id: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    labels: Dict[str, str] = field(default_factory=dict)
    source: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: int = 0  # seconds; 0 means indefinite
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert suppression rule to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "alert_rule_id": self.alert_rule_id,
            "severity": self.severity.value if self.severity else None,
            "labels": self.labels,
            "source": self.source,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SuppressionRule:
        """Create suppression rule from dictionary."""
        severity = data.get("severity")
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            alert_rule_id=data.get("alert_rule_id"),
            severity=AlertSeverity(severity) if severity else None,
            labels=data.get("labels", {}),
            source=data.get("source"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            duration=data.get("duration", 0),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


@dataclass
class AlertHistoryEntry:
    """An entry in the alert history."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    alert_id: str = ""
    rule_id: str = ""
    rule_name: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    status: AlertStatus = AlertStatus.FIRING
    message: str = ""
    source: str = ""
    value: float = 0.0
    threshold: float = 0.0
    escalation_level: int = 0
    action: str = ""  # created, acknowledged, resolved, escalated, suppressed
    actor: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert history entry to dictionary."""
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "status": self.status.value,
            "message": self.message,
            "source": self.source,
            "value": self.value,
            "threshold": self.threshold,
            "escalation_level": self.escalation_level,
            "action": self.action,
            "actor": self.actor,
            "details": self.details,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AlertHistoryEntry:
        """Create history entry from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            alert_id=data.get("alert_id", ""),
            rule_id=data.get("rule_id", ""),
            rule_name=data.get("rule_name", ""),
            severity=AlertSeverity(data.get("severity", "warning")),
            status=AlertStatus(data.get("status", "firing")),
            message=data.get("message", ""),
            source=data.get("source", ""),
            value=data.get("value", 0.0),
            threshold=data.get("threshold", 0.0),
            escalation_level=data.get("escalation_level", 0),
            action=data.get("action", ""),
            actor=data.get("actor", ""),
            details=data.get("details", {}),
            timestamp=data.get("timestamp", time.time()),
        )
