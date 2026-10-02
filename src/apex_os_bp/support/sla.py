"""SLA (Service Level Agreement) management module."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional


class SLAStatus(str, Enum):
    """Status of SLA compliance for a ticket."""

    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BREACHED = "breached"
    MET = "met"
    EXEMPT = "exempt"


@dataclass
class SLAPolicy:
    """Defines an SLA policy with response and resolution time targets."""

    name: str
    priority: str  # "low", "medium", "high", "urgent"
    response_time_minutes: int
    resolution_time_minutes: int
    business_hours_only: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""
    escalation_threshold_minutes: Optional[int] = None

    def to_dict(self) -> dict:
        """Serialize policy to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "priority": self.priority,
            "response_time_minutes": self.response_time_minutes,
            "resolution_time_minutes": self.resolution_time_minutes,
            "business_hours_only": self.business_hours_only,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "escalation_threshold_minutes": self.escalation_threshold_minutes,
        }


@dataclass
class SLATracking:
    """Tracks SLA compliance for a specific ticket."""

    ticket_id: str
    policy_id: str
    response_deadline: datetime
    resolution_deadline: datetime
    status: SLAStatus = SLAStatus.ON_TRACK
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    responded_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    breached_at: Optional[datetime] = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize tracking to dictionary."""
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "policy_id": self.policy_id,
            "response_deadline": self.response_deadline.isoformat(),
            "resolution_deadline": self.resolution_deadline.isoformat(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "responded_at": self.responded_at.isoformat()
            if self.responded_at
            else None,
            "resolved_at": self.resolved_at.isoformat()
            if self.resolved_at
            else None,
            "breached_at": self.breached_at.isoformat()
            if self.breached_at
            else None,
            "notes": self.notes,
        }


class SLAManager:
    """Manages SLA policies, tracking, and breach detection."""

    DEFAULT_POLICIES: dict[str, tuple[int, int]] = {
        "low": (480, 2880),  # 8h response, 48h resolution
        "medium": (240, 1440),  # 4h response, 24h resolution
        "high": (60, 480),  # 1h response, 8h resolution
        "urgent": (15, 120),  # 15min response, 2h resolution
    }

    def __init__(self) -> None:
        self._policies: dict[str, SLAPolicy] = {}
        self._tracking: dict[str, SLATracking] = {}
        self._ticket_tracking: dict[str, str] = {}

    def create_policy(
        self,
        name: str,
        priority: str,
        response_time_minutes: int,
        resolution_time_minutes: int,
        *,
        business_hours_only: bool = True,
        description: str = "",
        escalation_threshold_minutes: Optional[int] = None,
    ) -> SLAPolicy:
        """Create a new SLA policy."""
        policy = SLAPolicy(
            name=name,
            priority=priority,
            response_time_minutes=response_time_minutes,
            resolution_time_minutes=resolution_time_minutes,
            business_hours_only=business_hours_only,
            description=description,
            escalation_threshold_minutes=escalation_threshold_minutes,
        )
        self._policies[policy.id] = policy
        return policy

    def get_policy(self, policy_id: str) -> Optional[SLAPolicy]:
        """Retrieve an SLA policy by ID."""
        return self._policies.get(policy_id)

    def get_policy_by_priority(self, priority: str) -> Optional[SLAPolicy]:
        """Find a policy by priority level."""
        for policy in self._policies.values():
            if policy.priority == priority:
                return policy
        return None

    def create_default_policies(self) -> list[SLAPolicy]:
        """Create default SLA policies for all priority levels."""
        policies = []
        for priority, (resp, res) in self.DEFAULT_POLICIES.items():
            policy = self.create_policy(
                name=f"Default {priority.capitalize()} SLA",
                priority=priority,
                response_time_minutes=resp,
                resolution_time_minutes=res,
            )
            policies.append(policy)
        return policies

    def start_tracking(
        self, ticket_id: str, policy_id: str, start_time: Optional[datetime] = None
    ) -> SLATracking:
        """Start SLA tracking for a ticket."""
        policy = self._policies.get(policy_id)
        if policy is None:
            raise ValueError(f"Policy {policy_id} not found")
        start = start_time or datetime.now(timezone.utc)
        tracking = SLATracking(
            ticket_id=ticket_id,
            policy_id=policy_id,
            response_deadline=start
            + timedelta(minutes=policy.response_time_minutes),
            resolution_deadline=start
            + timedelta(minutes=policy.resolution_time_minutes),
        )
        self._tracking[tracking.id] = tracking
        self._ticket_tracking[ticket_id] = tracking.id
        return tracking

    def get_tracking(self, tracking_id: str) -> Optional[SLATracking]:
        """Retrieve SLA tracking by ID."""
        return self._tracking.get(tracking_id)

    def get_tracking_for_ticket(self, ticket_id: str) -> Optional[SLATracking]:
        """Retrieve SLA tracking for a specific ticket."""
        tracking_id = self._ticket_tracking.get(ticket_id)
        if tracking_id is None:
            return None
        return self._tracking.get(tracking_id)

    def record_response(self, ticket_id: str) -> Optional[SLATracking]:
        """Record that a response was sent for a ticket."""
        tracking = self.get_tracking_for_ticket(ticket_id)
        if tracking is None:
            return None
        tracking.responded_at = datetime.now(timezone.utc)
        if tracking.status == SLAStatus.ON_TRACK:
            tracking.status = SLAStatus.MET
        return tracking

    def record_resolution(self, ticket_id: str) -> Optional[SLATracking]:
        """Record that a ticket was resolved."""
        tracking = self.get_tracking_for_ticket(ticket_id)
        if tracking is None:
            return None
        tracking.resolved_at = datetime.now(timezone.utc)
        if tracking.status != SLAStatus.BREACHED:
            tracking.status = SLAStatus.MET
        return tracking

    def check_breaches(self) -> list[SLATracking]:
        """Check all active tracking for SLA breaches."""
        now = datetime.now(timezone.utc)
        breached = []
        for tracking in self._tracking.values():
            if tracking.status in (SLAStatus.MET, SLAStatus.BREACHED):
                continue
            if now > tracking.resolution_deadline:
                tracking.status = SLAStatus.BREACHED
                tracking.breached_at = now
                breached.append(tracking)
            elif now > tracking.response_deadline:
                tracking.status = SLAStatus.AT_RISK
        return breached

    def get_breached_tickets(self) -> list[SLATracking]:
        """Return all breached SLA tracking entries."""
        return [
            t for t in self._tracking.values() if t.status == SLAStatus.BREACHED
        ]

    def get_at_risk_tickets(self) -> list[SLATracking]:
        """Return all at-risk SLA tracking entries."""
        return [
            t for t in self._tracking.values() if t.status == SLAStatus.AT_RISK
        ]

    def get_sla_compliance_rate(self) -> float:
        """Return the percentage of tickets meeting SLA."""
        total = len(self._tracking)
        if total == 0:
            return 100.0
        met = len(
            [t for t in self._tracking.values() if t.status == SLAStatus.MET]
        )
        return (met / total) * 100.0

    def get_average_response_time(self) -> float:
        """Return average response time in minutes."""
        responded = [
            t
            for t in self._tracking.values()
            if t.responded_at is not None
        ]
        if not responded:
            return 0.0
        total = sum(
            (t.responded_at - t.created_at).total_seconds() / 60
            for t in responded
        )
        return total / len(responded)

    def get_average_resolution_time(self) -> float:
        """Return average resolution time in minutes."""
        resolved = [
            t
            for t in self._tracking.values()
            if t.resolved_at is not None
        ]
        if not resolved:
            return 0.0
        total = sum(
            (t.resolved_at - t.created_at).total_seconds() / 60
            for t in resolved
        )
        return total / len(resolved)

    def add_note(self, ticket_id: str, note: str) -> Optional[SLATracking]:
        """Add a note to SLA tracking for a ticket."""
        tracking = self.get_tracking_for_ticket(ticket_id)
        if tracking is None:
            return None
        tracking.notes.append(note)
        return tracking

    def list_policies(self) -> list[SLAPolicy]:
        """Return all SLA policies."""
        return list(self._policies.values())

    def list_tracking(self) -> list[SLATracking]:
        """Return all SLA tracking entries."""
        return list(self._tracking.values())
