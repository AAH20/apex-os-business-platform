"""Data retention — manages lifecycle and purging of audit events."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .models import AuditEvent, AuditSeverity
from .store import AuditStore


@dataclass
class RetentionPolicy:
    """Defines retention rules for audit events."""

    name: str
    retention_days: int
    archive_before_delete: bool = True
    archive_path: Optional[str] = None
    severity_filter: Optional[set[AuditSeverity]] = None
    resource_type_filter: Optional[set[str]] = None

    def is_expired(
        self, event: AuditEvent, now: Optional[datetime] = None
    ) -> bool:
        """Check if an event has exceeded its retention period."""
        now = now or datetime.now(timezone.utc)
        age = now - event.timestamp
        return age > timedelta(days=self.retention_days)

    def matches(self, event: AuditEvent) -> bool:
        """Check if an event matches this policy's filters."""
        if self.severity_filter and event.severity not in self.severity_filter:
            return False
        if (
            self.resource_type_filter
            and event.resource_type not in self.resource_type_filter
        ):
            return False
        return True


class DataRetentionManager:
    """Manages data retention policies and purging."""

    def __init__(self, store: AuditStore) -> None:
        self._store = store
        self._policies: dict[str, RetentionPolicy] = {}

    def add_policy(self, policy: RetentionPolicy) -> None:
        """Add a retention policy."""
        self._policies[policy.name] = policy

    def remove_policy(self, name: str) -> bool:
        """Remove a retention policy by name."""
        if name in self._policies:
            del self._policies[name]
            return True
        return False

    def get_policy(self, name: str) -> Optional[RetentionPolicy]:
        """Get a retention policy by name."""
        return self._policies.get(name)

    def list_policies(self) -> list[RetentionPolicy]:
        """List all retention policies."""
        return list(self._policies.values())

    def purge_expired(self, now: Optional[datetime] = None) -> int:
        """Remove events that have exceeded their retention period."""
        now = now or datetime.now(timezone.utc)
        all_events = self._store.get_all()
        kept: list[AuditEvent] = []
        purged = 0

        for event in all_events:
            expired = False
            for policy in self._policies.values():
                if policy.matches(event) and policy.is_expired(event, now):
                    expired = True
                    if policy.archive_before_delete and policy.archive_path:
                        self._archive_event(event, policy.archive_path)
                    break
            if expired:
                purged += 1
            else:
                kept.append(event)

        self._store.clear()
        for event in kept:
            self._store.append(event)

        return purged

    def _archive_event(self, event: AuditEvent, path: str) -> None:
        """Archive an event to a file."""
        archive_file = Path(path)
        archive_file.parent.mkdir(parents=True, exist_ok=True)
        with open(archive_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def get_retention_summary(self) -> dict[str, int]:
        """Get summary of events per policy."""
        all_events = self._store.get_all()
        summary: dict[str, int] = {}
        for name, policy in self._policies.items():
            summary[name] = sum(1 for e in all_events if policy.matches(e))
        return summary
