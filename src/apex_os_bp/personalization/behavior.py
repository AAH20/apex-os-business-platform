"""Behavior tracking for the personalization system."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BehaviorEvent:
    """Represents a single user behavior event.

    Attributes:
        user_id: The user who triggered the event.
        event_type: Type of event (e.g., 'page_view', 'click', 'purchase').
        timestamp: Unix timestamp of the event.
        properties: Additional event metadata.
        session_id: Optional session identifier.
    """

    user_id: str
    event_type: str
    timestamp: float = field(default_factory=time.time)
    properties: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize event to dictionary."""
        return {
            "user_id": self.user_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "properties": dict(self.properties),
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BehaviorEvent:
        """Deserialize event from dictionary."""
        return cls(
            user_id=data["user_id"],
            event_type=data["event_type"],
            timestamp=data.get("timestamp", time.time()),
            properties=dict(data.get("properties", {})),
            session_id=data.get("session_id"),
        )


class BehaviorTracker:
    """Tracks and aggregates user behavior events."""

    def __init__(self) -> None:
        self._events: list[BehaviorEvent] = []
        self._user_events: dict[str, list[BehaviorEvent]] = {}
        self._session_events: dict[str, list[BehaviorEvent]] = {}

    def track(
        self,
        user_id: str,
        event_type: str,
        properties: dict[str, Any] | None = None,
        session_id: str | None = None,
        timestamp: float | None = None,
    ) -> BehaviorEvent:
        """Record a new behavior event."""
        event = BehaviorEvent(
            user_id=user_id,
            event_type=event_type,
            timestamp=timestamp or time.time(),
            properties=properties or {},
            session_id=session_id,
        )
        self._events.append(event)

        if user_id not in self._user_events:
            self._user_events[user_id] = []
        self._user_events[user_id].append(event)

        if session_id is not None:
            if session_id not in self._session_events:
                self._session_events[session_id] = []
            self._session_events[session_id].append(event)

        return event

    def get_user_events(
        self, user_id: str, event_type: str | None = None
    ) -> list[BehaviorEvent]:
        """Get all events for a user, optionally filtered by type."""
        events = self._user_events.get(user_id, [])
        if event_type is not None:
            return [e for e in events if e.event_type == event_type]
        return list(events)

    def get_session_events(self, session_id: str) -> list[BehaviorEvent]:
        """Get all events for a session."""
        return list(self._session_events.get(session_id, []))

    def get_event_count(self, user_id: str | None = None) -> int:
        """Get total event count, optionally filtered by user."""
        if user_id is not None:
            return len(self._user_events.get(user_id, []))
        return len(self._events)

    def get_event_types(self, user_id: str | None = None) -> dict[str, int]:
        """Get counts per event type, optionally filtered by user."""
        events = (
            self._user_events.get(user_id, [])
            if user_id is not None
            else self._events
        )
        counts: dict[str, int] = {}
        for event in events:
            counts[event.event_type] = counts.get(event.event_type, 0) + 1
        return counts

    def get_last_event(self, user_id: str) -> BehaviorEvent | None:
        """Get the most recent event for a user."""
        events = self._user_events.get(user_id, [])
        return events[-1] if events else None

    def get_first_event(self, user_id: str) -> BehaviorEvent | None:
        """Get the earliest event for a user."""
        events = self._user_events.get(user_id, [])
        return events[0] if events else None

    def clear(self) -> None:
        """Clear all tracked events."""
        self._events.clear()
        self._user_events.clear()
        self._session_events.clear()
