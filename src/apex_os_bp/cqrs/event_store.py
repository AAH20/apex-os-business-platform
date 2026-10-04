"""Event store for persisting and retrieving events."""

from typing import Dict, List
from uuid import UUID

from apex_os_bp.cqrs.base import Event
from apex_os_bp.cqrs.exceptions import ConcurrencyError


class InMemoryEventStore:
    """In-memory event store implementation."""

    def __init__(self):
        self._events: Dict[UUID, List[Event]] = {}

    async def append(self, aggregate_id: UUID, events: List[Event], expected_version: int = 0) -> None:
        """Append events to the store."""
        if aggregate_id not in self._events:
            self._events[aggregate_id] = []

        current_version = len(self._events[aggregate_id])
        if current_version != expected_version:
            raise ConcurrencyError(
                f"Expected version {expected_version}, but got {current_version}"
            )

        self._events[aggregate_id].extend(events)

    async def get_events(self, aggregate_id: UUID) -> List[Event]:
        """Get all events for an aggregate."""
        return list(self._events.get(aggregate_id, []))

    async def get_all_events(self) -> List[Event]:
        """Get all events across all aggregates."""
        all_events = []
        for events in self._events.values():
            all_events.extend(events)
        return all_events

    async def get_events_by_type(self, event_type: str) -> List[Event]:
        """Get all events of a specific type."""
        result = []
        for events in self._events.values():
            for event in events:
                if event.event_type == event_type:
                    result.append(event)
        return result

    def clear(self) -> None:
        """Clear all events (for testing)."""
        self._events.clear()
