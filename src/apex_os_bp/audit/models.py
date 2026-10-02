"""Core data models for the audit system."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""

    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    ERROR = "error"
    CRITICAL = "critical"


class AuditStatus(str, Enum):
    """Status outcomes for audit events."""

    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


@dataclass
class AuditEvent:
    """Represents a single audit event."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str = "system"
    action: str = ""
    resource: str = ""
    resource_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    severity: AuditSeverity = AuditSeverity.WARNING
    status: AuditStatus = AuditStatus.SUCCESS
    correlation_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    duration_ms: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize event to dictionary."""
        d = asdict(self)
        d["severity"] = self.severity.value
        d["status"] = self.status.value
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditEvent:
        """Deserialize event from dictionary."""
        data = dict(data)
        data["severity"] = AuditSeverity(data["severity"])
        data["status"] = AuditStatus(data["status"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)
