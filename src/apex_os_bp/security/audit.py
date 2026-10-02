"""Audit logging for APEX-OS Business Platform."""

import json
import threading
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class AuditAction(Enum):
    """Types of auditable actions."""
    LOGIN = "login"
    LOGOUT = "logout"
    TOKEN_CREATED = "token_created"
    TOKEN_REFRESHED = "token_refreshed"
    TOKEN_REVOKED = "token_revoked"
    ACCESS_DENIED = "access_denied"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    DATA_READ = "data_read"
    DATA_WRITE = "data_write"
    DATA_DELETE = "data_delete"
    ENCRYPTION = "encryption"
    DECRYPTION = "decryption"
    RATE_LIMIT_HIT = "rate_limit_hit"
    CONFIG_CHANGE = "config_change"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Represents a single audit event record."""
    timestamp: float
    user_id: str
    action: str
    severity: str
    resource: str
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    success: bool = True


class AuditLogger:
    """Thread-safe in-memory audit logger with query capabilities."""

    def __init__(self, max_events: int = 10000):
        """Initialize the audit logger.

        Args:
            max_events: Maximum number of events to retain (oldest are evicted).
        """
        self._events: List[AuditEvent] = []
        self._max_events = max_events
        self._lock = threading.Lock()

    def log(
        self,
        user_id: str,
        action: AuditAction,
        resource: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        success: bool = True,
    ) -> AuditEvent:
        """Record an audit event.

        Args:
            user_id: ID of the user who triggered the event.
            action: The type of action performed.
            resource: The resource affected by the action.
            severity: Severity level of the event.
            details: Additional key-value details about the event.
            ip_address: Optional IP address of the requester.
            session_id: Optional session identifier.
            success: Whether the action succeeded.

        Returns:
            The created AuditEvent.
        """
        event = AuditEvent(
            timestamp=time.time(),
            user_id=user_id,
            action=action.value,
            severity=severity.value,
            resource=resource,
            details=details or {},
            ip_address=ip_address,
            session_id=session_id,
            success=success,
        )
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]
        return event

    def get_events(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        severity: Optional[str] = None,
        resource: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Query audit events with optional filters.

        Args:
            user_id: Filter by user ID.
            action: Filter by action type.
            severity: Filter by severity level.
            resource: Filter by resource name.
            limit: Maximum number of events to return (most recent first).

        Returns:
            List of matching AuditEvent objects.
        """
        with self._lock:
            events = list(self._events)

        if user_id is not None:
            events = [e for e in events if e.user_id == user_id]
        if action is not None:
            events = [e for e in events if e.action == action]
        if severity is not None:
            events = [e for e in events if e.severity == severity]
        if resource is not None:
            events = [e for e in events if e.resource == resource]

        return events[-limit:]

    def get_all_events(self) -> List[AuditEvent]:
        """Return all stored audit events."""
        with self._lock:
            return list(self._events)

    def clear(self) -> None:
        """Remove all stored audit events."""
        with self._lock:
            self._events.clear()

    def count(self) -> int:
        """Return the number of stored audit events."""
        with self._lock:
            return len(self._events)

    def to_dict(self) -> List[Dict[str, Any]]:
        """Serialize all events to a list of dictionaries."""
        return [asdict(e) for e in self.get_all_events()]

    def to_json(self) -> str:
        """Serialize all events to a JSON string."""
        return json.dumps(self.to_dict(), indent=2)
