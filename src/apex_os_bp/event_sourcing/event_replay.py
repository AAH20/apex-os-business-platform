"""Event replay: rebuild state by replaying events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypeVar

from .event_store import EventStore, StoredEvent

T = TypeVar("T")


@dataclass
class ReplayResult(Generic[T]):
    """Result of a replay operation."""

    state: T
    events_replayed: int
    last_version: int
    duration_ms: float


class EventReplayer:
    """Replays events to rebuild state.

    Supports:
    - Full replay from the beginning
    - Replay from a snapshot
    - Replay with a custom reducer
    - Replay with filtering
    """

    def __init__(self, store: EventStore) -> None:
        self._store = store

    def replay_stream(
        self,
        stream_id: str,
        reducer: Callable[[T, StoredEvent], T],
        initial_state: T,
        after_version: int = 0,
    ) -> ReplayResult[T]:
        """Replay all events for a stream through a reducer.

        Args:
            stream_id: The stream to replay.
            reducer: Function (state, event) -> new_state.
            initial_state: Starting state.
            after_version: Only replay events after this version.

        Returns:
            ReplayResult with final state and metadata.
        """
        import time as _time

        start = _time.perf_counter()
        events = self._store.get_stream(stream_id, after_version=after_version)
        state = initial_state
        for event in events:
            state = reducer(state, event)
        duration = (_time.perf_counter() - start) * 1000

        last_version = events[-1].version if events else after_version
        return ReplayResult(
            state=state,
            events_replayed=len(events),
            last_version=last_version,
            duration_ms=duration,
        )

    def replay_all(
        self,
        reducer: Callable[[T, StoredEvent], T],
        initial_state: T,
        event_type: str | None = None,
        after_seq: int = 0,
    ) -> ReplayResult[T]:
        """Replay all events globally through a reducer.

        Args:
            reducer: Function (state, event) -> new_state.
            initial_state: Starting state.
            event_type: Optional filter by event type.
            after_seq: Only replay events after this sequence number.

        Returns:
            ReplayResult with final state and metadata.
        """
        import time as _time

        start = _time.perf_counter()
        events = self._store.get_all(after_seq=after_seq, event_type=event_type)
        state = initial_state
        for event in events:
            state = reducer(state, event)
        duration = (_time.perf_counter() - start) * 1000

        last_version = events[-1].version if events else 0
        return ReplayResult(
            state=state,
            events_replayed=len(events),
            last_version=last_version,
            duration_ms=duration,
        )

    def replay_filtered(
        self,
        stream_ids: list[str],
        reducer: Callable[[T, StoredEvent], T],
        initial_state: T,
        predicate: Callable[[StoredEvent], bool] | None = None,
    ) -> ReplayResult[T]:
        """Replay events from selected streams with an optional predicate.

        Args:
            stream_ids: Streams to include.
            reducer: Function (state, event) -> new_state.
            initial_state: Starting state.
            predicate: Optional filter function.

        Returns:
            ReplayResult with final state and metadata.
        """
        import time as _time

        start = _time.perf_counter()
        state = initial_state
        count = 0
        last_version = 0

        for sid in stream_ids:
            events = self._store.get_stream(sid)
            for event in events:
                if predicate is None or predicate(event):
                    state = reducer(state, event)
                    count += 1
                    last_version = max(last_version, event.version)

        duration = (_time.perf_counter() - start) * 1000
        return ReplayResult(
            state=state,
            events_replayed=count,
            last_version=last_version,
            duration_ms=duration,
        )
