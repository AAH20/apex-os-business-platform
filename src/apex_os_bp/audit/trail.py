"""Audit trail — maintains ordered, correlated event sequences."""
from __future__ import annotations

from typing import Optional

from .models import AuditEvent
from .store import AuditStore


class AuditTrail:
    """Manages an ordered trail of correlated audit events."""

    def __init__(self, store: AuditStore) -> None:
        self._store = store

    def get_events(self) -> list[AuditEvent]:
        """Return all events in chronological order."""
        return sorted(self._store.get_all(), key=lambda e: e.timestamp)

    def get_by_correlation(self, correlation_id: str) -> list[AuditEvent]:
        """Return all events sharing a correlation ID."""
        return sorted(
            [e for e in self._store.get_all() if e.correlation_id == correlation_id],
            key=lambda e: e.timestamp,
        )

    def get_chain(self, event_id: str) -> list[AuditEvent]:
        """Return the full chain of events related to the given event."""
        all_events = self._store.get_all()
        target = next((e for e in all_events if e.id == event_id), None)
        if target is None:
            return []
        if target.correlation_id:
            return self.get_by_correlation(target.correlation_id)
        return [target]

    def get_timeline(self, actor: Optional[str] = None) -> list[AuditEvent]:
        """Return event timeline, optionally filtered by actor."""
        events = self.get_events()
        if actor:
            events = [e for e in events if e.actor == actor]
        return events

    def summarize(self) -> dict[str, int]:
        """Return summary statistics of the trail."""
        events = self._store.get_all()
        return {
            "total_events": len(events),
            "unique_actors": len({e.actor for e in events}),
            "unique_correlations": len(
                {e.correlation_id for e in events if e.correlation_id}
            ),
            "by_severity": {
                sev.value: sum(1 for e in events if e.severity == sev)
                for sev in {e.severity for e in events}
            },
            "by_status": {
                st.value: sum(1 for e in events if e.status == st)
                for st in {e.status for e in events}
            },
        }
