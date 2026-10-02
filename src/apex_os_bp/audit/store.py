"""Storage backends for audit events."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from .models import AuditEvent


class AuditStore(ABC):
    """Abstract base class for audit event storage."""

    @abstractmethod
    def append(self, event: AuditEvent) -> None:
        """Store an audit event."""
        ...

    @abstractmethod
    def get_all(self) -> list[AuditEvent]:
        """Retrieve all stored events."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Remove all stored events."""
        ...


class InMemoryAuditStore(AuditStore):
    """In-memory storage backend."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self._events.append(event)

    def get_all(self) -> list[AuditEvent]:
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()

    def __len__(self) -> int:
        return len(self._events)


class FileAuditStore(AuditStore):
    """File-based storage backend (JSON Lines)."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def append(self, event: AuditEvent) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def get_all(self) -> list[AuditEvent]:
        if not self._path.exists():
            return []
        events: list[AuditEvent] = []
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(AuditEvent.from_dict(json.loads(line)))
        return events

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()
