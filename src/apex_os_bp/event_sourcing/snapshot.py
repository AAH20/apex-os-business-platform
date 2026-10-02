"""Snapshot management: capture and restore state at a point in time."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, TypeVar

from .event_store import EventStore

T = TypeVar("T")


@dataclass
class Snapshot(Generic[T]):
    """A point-in-time snapshot of aggregate state."""

    snapshot_id: str
    stream_id: str
    state: T
    version: int
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "stream_id": self.stream_id,
            "state": self.state,
            "version": self.version,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Snapshot":
        return cls(**data)


class SnapshotManager:
    """Manages snapshots for event-sourced aggregates.

    Snapshots are stored in a separate SQLite table and can be used
    to avoid replaying the full event history.
    """

    def __init__(self, store: EventStore, db_path: str | Path = ":memory:") -> None:
        self._store = store
        self._db_path = str(db_path)
        self._memory_conn: sqlite3.Connection | None = None
        if self._db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        conn = self._memory_conn or sqlite3.connect(self._db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                snapshot_id TEXT PRIMARY KEY,
                stream_id TEXT NOT NULL,
                state TEXT NOT NULL,
                version INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_snap_stream ON snapshots(stream_id, version DESC)"
        )
        conn.commit()
        if self._memory_conn is None:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        if self._memory_conn is not None:
            return self._memory_conn
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def save_snapshot(
        self,
        stream_id: str,
        state: Any,
        version: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Snapshot:
        """Save a snapshot for a stream.

        Args:
            stream_id: The aggregate/stream identifier.
            state: The state to snapshot (must be JSON-serializable).
            version: Stream version at snapshot time (auto-detected if None).
            metadata: Optional metadata.

        Returns:
            The saved snapshot.
        """
        if version is None:
            version = self._store.get_current_version(stream_id)

        snapshot = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            stream_id=stream_id,
            state=state,
            version=version,
            timestamp=time.time(),
            metadata=metadata or {},
        )

        conn = self._connect()
        conn.execute(
            "INSERT INTO snapshots (snapshot_id, stream_id, state, version, timestamp, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                snapshot.snapshot_id,
                snapshot.stream_id,
                json.dumps(snapshot.state),
                snapshot.version,
                snapshot.timestamp,
                json.dumps(snapshot.metadata),
            ),
        )
        conn.commit()
        if self._memory_conn is None:
            conn.close()
        return snapshot

    def get_latest(self, stream_id: str) -> Snapshot | None:
        """Get the latest snapshot for a stream."""
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM snapshots WHERE stream_id = ? ORDER BY version DESC LIMIT 1",
            (stream_id,),
        ).fetchone()
        if self._memory_conn is None:
            conn.close()

        if row is None:
            return None
        return Snapshot(
            snapshot_id=row["snapshot_id"],
            stream_id=row["stream_id"],
            state=json.loads(row["state"]),
            version=row["version"],
            timestamp=row["timestamp"],
            metadata=json.loads(row["metadata"]),
        )

    def get_at_version(self, stream_id: str, version: int) -> Snapshot | None:
        """Get the latest snapshot at or before a given version."""
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM snapshots WHERE stream_id = ? AND version <= ? "
            "ORDER BY version DESC LIMIT 1",
            (stream_id, version),
        ).fetchone()
        if self._memory_conn is None:
            conn.close()

        if row is None:
            return None
        return Snapshot(
            snapshot_id=row["snapshot_id"],
            stream_id=row["stream_id"],
            state=json.loads(row["state"]),
            version=row["version"],
            timestamp=row["timestamp"],
            metadata=json.loads(row["metadata"]),
        )

    def get_all_for_stream(self, stream_id: str) -> list[Snapshot]:
        """Get all snapshots for a stream, newest first."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM snapshots WHERE stream_id = ? ORDER BY version DESC",
            (stream_id,),
        ).fetchall()
        if self._memory_conn is None:
            conn.close()

        return [
            Snapshot(
                snapshot_id=r["snapshot_id"],
                stream_id=r["stream_id"],
                state=json.loads(r["state"]),
                version=r["version"],
                timestamp=r["timestamp"],
                metadata=json.loads(r["metadata"]),
            )
            for r in rows
        ]

    def delete_stream_snapshots(self, stream_id: str) -> int:
        """Delete all snapshots for a stream. Returns count deleted."""
        conn = self._connect()
        cursor = conn.execute(
            "DELETE FROM snapshots WHERE stream_id = ?", (stream_id,)
        )
        conn.commit()
        deleted = cursor.rowcount
        if self._memory_conn is None:
            conn.close()
        return deleted

    def should_snapshot(self, stream_id: str, threshold: int) -> bool:
        """Check if a snapshot should be taken based on event count since last snapshot."""
        current_version = self._store.get_current_version(stream_id)
        latest = self.get_latest(stream_id)
        if latest is None:
            return current_version >= threshold
        return (current_version - latest.version) >= threshold
