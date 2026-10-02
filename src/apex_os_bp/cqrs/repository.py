"""Repository for aggregate roots."""

from typing import Dict, List, Optional
from uuid import UUID

from apex_os_bp.cqrs.base import Event, WriteModel
from apex_os_bp.cqrs.event_store import InMemoryEventStore
from apex_os_bp.cqrs.exceptions import AggregateNotFoundError


class Repository:
    """Generic repository for aggregate roots."""

    def __init__(self, event_store: InMemoryEventStore, aggregate_class: type):
        self._event_store = event_store
        self._aggregate_class = aggregate_class
        self._cache: Dict[UUID, WriteModel] = {}

    async def get_by_id(self, aggregate_id: UUID) -> WriteModel:
        """Get an aggregate by ID, rebuilding from events."""
        if aggregate_id in self._cache:
            return self._cache[aggregate_id]

        events = await self._event_store.get_events(aggregate_id)
        if not events:
            raise AggregateNotFoundError(f"Aggregate {aggregate_id} not found")

        aggregate = self._aggregate_class(aggregate_id)
        for event in events:
            aggregate.apply(event)

        self._cache[aggregate_id] = aggregate
        return aggregate

    async def save(self, aggregate: WriteModel) -> None:
        """Save an aggregate's uncommitted events."""
        uncommitted = aggregate.uncommitted_events()
        if not uncommitted:
            return

        await self._event_store.append(
            aggregate.id, uncommitted, expected_version=aggregate.version - len(uncommitted)
        )
        aggregate.mark_committed()
        self._cache[aggregate.id] = aggregate

    async def exists(self, aggregate_id: UUID) -> bool:
        """Check if an aggregate exists."""
        try:
            await self.get_by_id(aggregate_id)
            return True
        except AggregateNotFoundError:
            return False
