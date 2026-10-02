"""Event sourcing system for APEX-OS Business Platform."""

from .event_store import EventStore, StoredEvent, ConcurrencyError
from .event_replay import EventReplayer, ReplayResult
from .snapshot import Snapshot, SnapshotManager
from .projection import Projection, ProjectionBuilder, ProjectionState
from .versioning import EventVersion, VersionedEvent, VersionMigrator

__all__ = [
    "EventStore",
    "StoredEvent",
    "ConcurrencyError",
    "EventReplayer",
    "ReplayResult",
    "Snapshot",
    "SnapshotManager",
    "Projection",
    "ProjectionBuilder",
    "ProjectionState",
    "EventVersion",
    "VersionedEvent",
    "VersionMigrator",
]
