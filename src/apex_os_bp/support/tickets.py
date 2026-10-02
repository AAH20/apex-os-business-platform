"""Ticket management module for customer support."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class TicketStatus(str, Enum):
    """Lifecycle states for a support ticket."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_ON_CUSTOMER = "waiting_on_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class TicketPriority(str, Enum):
    """Priority levels for triage."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Ticket:
    """Represents a customer support ticket."""

    subject: str
    description: str
    customer_id: str
    priority: TicketPriority = TicketPriority.MEDIUM
    status: TicketStatus = TicketStatus.OPEN
    assignee_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    internal_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize ticket to dictionary."""
        return {
            "id": self.id,
            "subject": self.subject,
            "description": self.description,
            "customer_id": self.customer_id,
            "priority": self.priority.value,
            "status": self.status.value,
            "assignee_id": self.assignee_id,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "internal_notes": self.internal_notes,
        }


class TicketManager:
    """Manages the full lifecycle of support tickets."""

    VALID_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
        TicketStatus.OPEN: {
            TicketStatus.IN_PROGRESS,
            TicketStatus.WAITING_ON_CUSTOMER,
            TicketStatus.ESCALATED,
            TicketStatus.RESOLVED,
        },
        TicketStatus.IN_PROGRESS: {
            TicketStatus.WAITING_ON_CUSTOMER,
            TicketStatus.ESCALATED,
            TicketStatus.RESOLVED,
        },
        TicketStatus.WAITING_ON_CUSTOMER: {
            TicketStatus.IN_PROGRESS,
            TicketStatus.ESCALATED,
            TicketStatus.RESOLVED,
        },
        TicketStatus.ESCALATED: {
            TicketStatus.IN_PROGRESS,
            TicketStatus.RESOLVED,
        },
        TicketStatus.RESOLVED: {
            TicketStatus.CLOSED,
            TicketStatus.IN_PROGRESS,
        },
        TicketStatus.CLOSED: set(),
    }

    def __init__(self) -> None:
        self._tickets: dict[str, Ticket] = {}

    def create_ticket(
        self,
        subject: str,
        description: str,
        customer_id: str,
        priority: TicketPriority = TicketPriority.MEDIUM,
        tags: Optional[list[str]] = None,
    ) -> Ticket:
        """Create a new support ticket."""
        ticket = Ticket(
            subject=subject,
            description=description,
            customer_id=customer_id,
            priority=priority,
            tags=tags or [],
        )
        self._tickets[ticket.id] = ticket
        return ticket

    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Retrieve a ticket by ID."""
        return self._tickets.get(ticket_id)

    def update_ticket(
        self,
        ticket_id: str,
        *,
        subject: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[TicketPriority] = None,
        assignee_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Optional[Ticket]:
        """Update ticket fields."""
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return None
        if subject is not None:
            ticket.subject = subject
        if description is not None:
            ticket.description = description
        if priority is not None:
            ticket.priority = priority
        if assignee_id is not None:
            ticket.assignee_id = assignee_id
        if tags is not None:
            ticket.tags = tags
        ticket.updated_at = datetime.now(timezone.utc)
        return ticket

    def transition_status(
        self, ticket_id: str, new_status: TicketStatus
    ) -> Optional[Ticket]:
        """Transition a ticket to a new status if valid."""
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return None
        if new_status not in self.VALID_TRANSITIONS.get(ticket.status, set()):
            raise ValueError(
                f"Invalid transition from {ticket.status.value} to {new_status.value}"
            )
        ticket.status = new_status
        ticket.updated_at = datetime.now(timezone.utc)
        if new_status == TicketStatus.RESOLVED:
            ticket.resolved_at = datetime.now(timezone.utc)
        if new_status == TicketStatus.CLOSED:
            ticket.closed_at = datetime.now(timezone.utc)
        return ticket

    def add_internal_note(self, ticket_id: str, note: str) -> Optional[Ticket]:
        """Add an internal note to a ticket."""
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return None
        ticket.internal_notes.append(note)
        ticket.updated_at = datetime.now(timezone.utc)
        return ticket

    def assign_ticket(self, ticket_id: str, assignee_id: str) -> Optional[Ticket]:
        """Assign a ticket to an agent."""
        return self.update_ticket(ticket_id, assignee_id=assignee_id)

    def list_tickets(
        self,
        *,
        status: Optional[TicketStatus] = None,
        priority: Optional[TicketPriority] = None,
        customer_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> list[Ticket]:
        """List tickets with optional filters."""
        results = list(self._tickets.values())
        if status is not None:
            results = [t for t in results if t.status == status]
        if priority is not None:
            results = [t for t in results if t.priority == priority]
        if customer_id is not None:
            results = [t for t in results if t.customer_id == customer_id]
        if assignee_id is not None:
            results = [t for t in results if t.assignee_id == assignee_id]
        if tag is not None:
            results = [t for t in results if tag in t.tags]
        return results

    def delete_ticket(self, ticket_id: str) -> bool:
        """Delete a ticket by ID."""
        if ticket_id in self._tickets:
            del self._tickets[ticket_id]
            return True
        return False

    def get_ticket_count(self) -> int:
        """Return total number of tickets."""
        return len(self._tickets)

    def get_open_tickets(self) -> list[Ticket]:
        """Return all non-resolved, non-closed tickets."""
        return [
            t
            for t in self._tickets.values()
            if t.status
            not in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
        ]

    def get_escalated_tickets(self) -> list[Ticket]:
        """Return all escalated tickets."""
        return [
            t for t in self._tickets.values() if t.status == TicketStatus.ESCALATED
        ]
