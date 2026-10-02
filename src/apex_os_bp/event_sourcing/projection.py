"""Projection builder: build read models from event streams."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypeVar

from .event_store import EventStore, StoredEvent
from .snapshot import SnapshotManager

T = TypeVar("T")


@dataclass
class ProjectionState(Generic[T]):
    """State of a projection."""

    name: str
    state: T
    last_processed_seq: int = 0
    event_count: int = 0


class Projection(Generic[T]):
    """A read-model projection built from events.

    Maintains state by applying events through a handler function.
    Supports checkpointing for incremental updates.
    """

    def __init__(
        self,
        name: str,
        initial_state: T,
        handler: Callable[[T, StoredEvent], T],
    ) -> None:
        self._name = name
        self._state = initial_state
        self._handler = handler
        self._last_seq = 0
        self._event_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> T:
        return self._state

    @property
    def last_processed_seq(self) -> int:
        return self._last_seq

    @property
    def event_count(self) -> int:
        return self._event_count

    def handle(self, event: StoredEvent) -> None:
        """Process a single event."""
        self._state = self._handler(self._state, event)
        self._last_seq = max(self._last_seq, event.version)
        self._event_count += 1

    def handle_many(self, events: list[StoredEvent]) -> None:
        """Process multiple events."""
        for event in events:
            self.handle(event)

    def get_state(self) -> ProjectionState[T]:
        """Get the current projection state."""
        return ProjectionState(
            name=self._name,
            state=self._state,
            last_processed_seq=self._last_seq,
            event_count=self._event_count,
        )

    def reset(self) -> None:
        """Reset the projection (does not reset initial_state reference)."""
        self._last_seq = 0
        self._event_count = 0


class ProjectionBuilder:
    """Builder for constructing and managing projections.

    Provides a fluent API for defining projections with handlers
    for specific event types.
    """

    def __init__(self, store: EventStore, snapshot_manager: SnapshotManager | None = None) -> None:
        self._store = store
        self._snapshot_manager = snapshot_manager
        self._projections: dict[str, Projection] = {}

    def register(
        self,
        name: str,
        initial_state: Any,
        handlers: dict[str, Callable[[Any, StoredEvent], Any]],
    ) -> "ProjectionBuilder":
        """Register a projection with per-event-type handlers.

        Args:
            name: Projection name.
            initial_state: Initial state value.
            handlers: Mapping of event_type -> handler function.

        Returns:
            Self for chaining.
        """

        def dispatcher(state: Any, event: StoredEvent) -> Any:
            handler = handlers.get(event.event_type)
            if handler is not None:
                return handler(state, event)
            return state

        self._projections[name] = Projection(name, initial_state, dispatcher)
        return self

    def build(self, name: str) -> Projection:
        """Get a registered projection by name."""
        if name not in self._projections:
            raise KeyError(f"Projection {name!r} not found")
        return self._projections[name]

    def rebuild(self, name: str) -> Projection:
        """Rebuild a projection from all events."""
        projection = self._projections[name]
        projection.reset()
        events = self._store.get_all()
        projection.handle_many(events)
        return projection

    def rebuild_all(self) -> dict[str, Projection]:
        """Rebuild all projections from all events."""
        events = self._store.get_all()
        for projection in self._projections.values():
            projection.reset()
            projection.handle_many(events)
        return dict(self._projections)

    def update_from_events(self, name: str, after_seq: int = 0) -> Projection:
        """Incrementally update a projection with new events."""
        projection = self._projections[name]
        events = self._store.get_all(after_seq=projection.last_processed_seq)
        projection.handle_many(events)
        return projection

    def update_all_from_events(self, after_seq: int = 0) -> dict[str, Projection]:
        """Incrementally update all projections with new events."""
        events = self._store.get_all(after_seq=after_seq)
        for projection in self._projections.values():
            projection.handle_many(events)
        return dict(self._projections)

    def list_projections_names(self) -> list[str]:
        """List all registered projection names."""
        return list(self._projections.keys())

    def get_all_states(self) -> dict[str, ProjectionState]:
        """Get states of all projections."""
        return {name: p.get_state() for name, p in self._projections.items()}
