"""Data governance module for data warehouse.

Provides governance policies, data lineage tracking, access control,
and sensitivity classification for data assets.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class AccessLevel(Enum):
    """Access levels for data assets."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    SECRET = "secret"


class SensitivityLevel(Enum):
    """Data sensitivity classification levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    HIGHLY_CONFIDENTIAL = "highly_confidential"
    CRITICAL = "critical"


@dataclass
class GovernancePolicy:
    """Represents a data governance policy."""

    name: str
    description: str = ""
    access_level: AccessLevel = AccessLevel.INTERNAL
    sensitivity: SensitivityLevel = SensitivityLevel.INTERNAL
    allowed_roles: List[str] = field(default_factory=list)
    denied_roles: List[str] = field(default_factory=list)
    allowed_users: List[str] = field(default_factory=list)
    denied_users: List[str] = field(default_factory=list)
    requires_approval: bool = False
    approvers: List[str] = field(default_factory=list)
    retention_days: Optional[int] = None
    encryption_required: bool = False
    audit_logging: bool = True
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_access(self, user: str, roles: List[str]) -> bool:
        """Check if a user with given roles can access data under this policy."""
        if not self.enabled:
            return False
        if user in self.denied_users:
            return False
        if any(r in self.denied_roles for r in roles):
            return False
        if self.allowed_users and user not in self.allowed_users:
            return False
        if self.allowed_roles and not any(r in self.allowed_roles for r in roles):
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert policy to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "access_level": self.access_level.value,
            "sensitivity": self.sensitivity.value,
            "allowed_roles": self.allowed_roles,
            "denied_roles": self.denied_roles,
            "allowed_users": self.allowed_users,
            "denied_users": self.denied_users,
            "requires_approval": self.requires_approval,
            "approvers": self.approvers,
            "retention_days": self.retention_days,
            "encryption_required": self.encryption_required,
            "audit_logging": self.audit_logging,
            "enabled": self.enabled,
        }


@dataclass
class DataLineage:
    """Represents data lineage information."""

    source: str
    target: str
    transformation: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    upstream: List[str] = field(default_factory=list)
    downstream: List[str] = field(default_factory=list)

    def add_upstream(self, source: str) -> None:
        """Add an upstream dependency."""
        if source not in self.upstream:
            self.upstream.append(source)

    def add_downstream(self, target: str) -> None:
        """Add a downstream dependency."""
        if target not in self.downstream:
            self.downstream.append(target)

    def to_dict(self) -> Dict[str, Any]:
        """Convert lineage to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "transformation": self.transformation,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "upstream": self.upstream,
            "downstream": self.downstream,
        }


@dataclass
class AuditEvent:
    """Represents an audit event."""

    event_id: str
    event_type: str
    user: str
    resource: str
    action: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: Dict[str, Any] = field(default_factory=dict)
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "user": self.user,
            "resource": self.resource,
            "action": self.action,
            "timestamp": self.timestamp,
            "details": self.details,
            "success": self.success,
        }


class DataGovernance:
    """Main data governance manager."""

    def __init__(self):
        self._policies: Dict[str, GovernancePolicy] = {}
        self._lineage: Dict[str, DataLineage] = {}
        self._audit_log: List[AuditEvent] = []
        self._classifications: Dict[str, SensitivityLevel] = {}
        self._role_hierarchy: Dict[str, List[str]] = {}

    def add_policy(self, policy: GovernancePolicy) -> None:
        """Add a governance policy."""
        self._policies[policy.name] = policy

    def remove_policy(self, name: str) -> bool:
        """Remove a governance policy."""
        if name in self._policies:
            del self._policies[name]
            return True
        return False

    def get_policy(self, name: str) -> Optional[GovernancePolicy]:
        """Get a policy by name."""
        return self._policies.get(name)

    def list_policies(self) -> List[GovernancePolicy]:
        """List all policies."""
        return list(self._policies.values())

    def check_access(self, resource: str, user: str, roles: List[str]) -> bool:
        """Check if a user can access a resource."""
        policy = self._policies.get(resource)
        if not policy:
            return True  # No policy means open access
        return policy.can_access(user, roles)

    def classify_data(self, resource: str, sensitivity: SensitivityLevel) -> None:
        """Classify a data resource with a sensitivity level."""
        self._classifications[resource] = sensitivity

    def get_classification(self, resource: str) -> Optional[SensitivityLevel]:
        """Get the sensitivity classification of a resource."""
        return self._classifications.get(resource)

    def add_lineage(self, lineage: DataLineage) -> None:
        """Add data lineage information."""
        key = f"{lineage.source}->{lineage.target}"
        self._lineage[key] = lineage

    def get_lineage(self, source: str, target: str) -> Optional[DataLineage]:
        """Get lineage for a source-target pair."""
        key = f"{source}->{target}"
        return self._lineage.get(key)

    def get_upstream_lineage(self, target: str) -> List[DataLineage]:
        """Get all upstream lineage for a target."""
        return [l for l in self._lineage.values() if l.target == target]

    def get_downstream_lineage(self, source: str) -> List[DataLineage]:
        """Get all downstream lineage for a source."""
        return [l for l in self._lineage.values() if l.source == source]

    def log_audit_event(self, event: AuditEvent) -> None:
        """Log an audit event."""
        self._audit_log.append(event)

    def get_audit_log(self, resource: Optional[str] = None, user: Optional[str] = None) -> List[AuditEvent]:
        """Get audit log entries, optionally filtered."""
        events = self._audit_log
        if resource:
            events = [e for e in events if e.resource == resource]
        if user:
            events = [e for e in events if e.user == user]
        return events

    def add_role_hierarchy(self, role: str, inherits_from: List[str]) -> None:
        """Define role inheritance hierarchy."""
        self._role_hierarchy[role] = inherits_from

    def get_effective_roles(self, roles: List[str]) -> Set[str]:
        """Get all effective roles including inherited ones."""
        effective = set(roles)
        for role in roles:
            if role in self._role_hierarchy:
                effective.update(self._role_hierarchy[role])
        return effective

    def enforce_retention(self) -> List[str]:
        """Enforce retention policies. Returns list of resources to purge."""
        to_purge = []
        now = datetime.now(timezone.utc)
        for name, policy in self._policies.items():
            if policy.retention_days is not None:
                # In a real system, check data age against retention_days
                to_purge.append(name)
        return to_purge

    def generate_audit_report(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Generate an audit report."""
        events = self._audit_log
        if start_date:
            events = [e for e in events if e.timestamp >= start_date]
        if end_date:
            events = [e for e in events if e.timestamp <= end_date]

        return {
            "total_events": len(events),
            "successful_events": sum(1 for e in events if e.success),
            "failed_events": sum(1 for e in events if not e.success),
            "events_by_type": self._group_by_key(events, "event_type"),
            "events_by_user": self._group_by_key(events, "user"),
            "events_by_resource": self._group_by_key(events, "resource"),
        }

    def _group_by_key(self, events: List[AuditEvent], key: str) -> Dict[str, int]:
        """Group events by a key and count."""
        result: Dict[str, int] = {}
        for event in events:
            value = getattr(event, key, "unknown")
            result[value] = result.get(value, 0) + 1
        return result

    def validate_compliance(self, resource: str) -> Dict[str, Any]:
        """Validate compliance for a resource."""
        policy = self._policies.get(resource)
        classification = self._classifications.get(resource)
        lineage = [l for l in self._lineage.values() if l.target == resource or l.source == resource]

        issues = []
        if policy and policy.encryption_required:
            # In a real system, verify encryption is active
            pass
        if classification in (SensitivityLevel.HIGHLY_CONFIDENTIAL, SensitivityLevel.CRITICAL):
            if not policy or policy.access_level not in (AccessLevel.RESTRICTED, AccessLevel.SECRET):
                issues.append(f"Resource '{resource}' has high sensitivity but insufficient access controls")

        return {
            "resource": resource,
            "compliant": len(issues) == 0,
            "issues": issues,
            "policy": policy.to_dict() if policy else None,
            "classification": classification.value if classification else None,
            "lineage_count": len(lineage),
        }
