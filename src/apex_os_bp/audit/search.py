"""Audit search — query and filter audit events."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from .models import AuditEvent, AuditSeverity, AuditStatus
from .store import AuditStore


@dataclass
class SearchQuery:
    """Query parameters for audit event search."""

    actor: Optional[str] = None
    action: Optional[str] = None
    resource: Optional[str] = None
    resource_type: Optional[str] = None
    severity: Optional[AuditSeverity] = None
    status: Optional[AuditStatus] = None
    correlation_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata_key: Optional[str] = None
    metadata_value: Optional[Any] = None
    text_search: Optional[str] = None
    limit: Optional[int] = None
    offset: int = 0
    sort_by: str = "timestamp"
    sort_desc: bool = True


class AuditSearch:
    """Search and filter audit events."""

    def __init__(self, store: AuditStore) -> None:
        self._store = store

    def search(self, query: SearchQuery) -> list[AuditEvent]:
        """Execute a search query."""
        events = self._store.get_all()
        results: list[AuditEvent] = []

        for event in events:
            if self._matches(event, query):
                results.append(event)

        reverse = query.sort_desc
        if query.sort_by == "timestamp":
            results.sort(key=lambda e: e.timestamp, reverse=reverse)
        elif query.sort_by == "actor":
            results.sort(key=lambda e: e.actor, reverse=reverse)
        elif query.sort_by == "action":
            results.sort(key=lambda e: e.action, reverse=reverse)
        elif query.sort_by == "severity":
            results.sort(key=lambda e: e.severity.value, reverse=reverse)
        elif query.sort_by == "status":
            results.sort(key=lambda e: e.status.value, reverse=reverse)

        start = query.offset
        end = start + query.limit if query.limit else None
        return results[start:end]

    def _matches(self, event: AuditEvent, query: SearchQuery) -> bool:
        """Check if an event matches the query criteria."""
        if query.actor and event.actor != query.actor:
            return False
        if query.action and query.action not in event.action:
            return False
        if query.resource and query.resource not in event.resource:
            return False
        if query.resource_type and event.resource_type != query.resource_type:
            return False
        if query.severity and event.severity != query.severity:
            return False
        if query.status and event.status != query.status:
            return False
        if query.correlation_id and event.correlation_id != query.correlation_id:
            return False
        if query.start_time and event.timestamp < query.start_time:
            return False
        if query.end_time and event.timestamp > query.end_time:
            return False
        if query.metadata_key:
            if query.metadata_key not in event.metadata:
                return False
            if (
                query.metadata_value is not None
                and event.metadata[query.metadata_key] != query.metadata_value
            ):
                return False
        if query.text_search:
            text = query.text_search.lower()
            searchable = (
                f"{event.actor} {event.action} {event.resource} {event.resource_type} {str(event.metadata)}".lower()
            )
            if text not in searchable:
                return False
        return True

    def count(self, query: SearchQuery) -> int:
        """Count events matching a query."""
        return len(self.search(query))

    def get_by_actor(self, actor: str) -> list[AuditEvent]:
        """Get all events for a specific actor."""
        return self.search(SearchQuery(actor=actor))

    def get_by_action(self, action: str) -> list[AuditEvent]:
        """Get all events matching an action."""
        return self.search(SearchQuery(action=action))

    def get_by_time_range(
        self, start: datetime, end: datetime
    ) -> list[AuditEvent]:
        """Get all events within a time range."""
        return self.search(SearchQuery(start_time=start, end_time=end))

    def get_by_severity(self, severity: AuditSeverity) -> list[AuditEvent]:
        """Get all events with a specific severity."""
        return self.search(SearchQuery(severity=severity))

    def get_by_status(self, status: AuditStatus) -> list[AuditEvent]:
        """Get all events with a specific status."""
        return self.search(SearchQuery(status=status))

    def full_text_search(self, text: str) -> list[AuditEvent]:
        """Full-text search across all event fields."""
        return self.search(SearchQuery(text_search=text))
