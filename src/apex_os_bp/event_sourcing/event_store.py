"""Event store: append-only persistence of domain events."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, TypeVar

T = TypeVar("T")


@dataclass
class StoredEvent:
    """A single persisted event."""

    event_id: str
    stream_id: str
    event_type: str
    payload: dict[str, Any]
    version: int
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StoredEvent":
        return cls(**data)


class ConcurrencyError(Exception):
    """Raised when an optimistic-concurrency check fails."""


class EventStore:
    """Append-only event store backed by SQLite.

    Supports:
    - Appending events with optimistic concurrency control
    - Reading events by stream or globally
    - Filtering by event type and time range
    - Subscribing to new events
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._db_path = str(db_path)
        self._lock = threading.RLock()
        self._subscribers: list[Callable[[StoredEvent], None]] = []
        self._memory_conn: sqlite3.Connection | None = None
        if self._db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        conn = self._memory_conn or self._connect()
        with self._lock:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    stream_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_stream ON events(stream_id, version)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_type ON events(event_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)"
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        if self._memory_conn is not None:
            return self._memory_conn
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def append(
        self,
        stream_id: str,
        event_type: str,
        payload: dict[str, Any],
        expected_version: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StoredEvent:
        """Append an event to a stream.

        Args:
            stream_id: The aggregate/stream identifier.
            event_type: Type name of the event.
            payload: Event data as a dict.
            expected_version: If provided, enforce optimistic concurrency.
            metadata: Optional correlation/causation metadata.

        Returns:
            The stored event.

        Raises:
            ConcurrencyError: If expected_version doesn't match.
        """
        with self._lock:
            with self._connect() as conn:
                if expected_version is not None:
                    row = conn.execute(
                        "SELECT COALESCE(MAX(version), 0) FROM events WHERE stream_id = ?",
                        (stream_id,),
                    ).fetchone()
                    current = row[0] if row else 0
                    if current != expected_version:
                        raise ConcurrencyError(
                            f"Stream {stream_id!r} expected version {expected_version}, "
                            f"but current version is {current}"
                        )

                next_version = (
                    conn.execute(
                        "SELECT COALESCE(MAX(version), 0) + 1 FROM events WHERE stream_id = ?",
                        (stream_id,),
                    ).fetchone()[0]
                )

                event = StoredEvent(
                    event_id=str(uuid.uuid4()),
                    stream_id=stream_id,
                    event_type=event_type,
                    payload=payload,
                    version=next_version,
                    timestamp=time.time(),
                    metadata=metadata or {},
                )

                conn.execute(
                    "INSERT INTO events (event_id, stream_id, event_type, payload, version, timestamp, metadata) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        event.event_id,
                        event.stream_id,
                        event.event_type,
                        json.dumps(event.payload),
                        event.version,
                        event.timestamp,
                        json.dumps(event.metadata),
                    ),
                )

        self._notify(event)
        return event

    def get_stream(self, stream_id: str, after_version: int = 0) -> list[StoredEvent]:
        """Get all events for a stream, optionally after a version."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE stream_id = ? AND version > ? ORDER BY version",
                (stream_id, after_version),
            ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def get_all(
        self,
        after_seq: int = 0,
        event_type: str | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
        limit: int | None = None,
    ) -> list[StoredEvent]:
        """Get events globally with optional filters."""
        query = "SELECT * FROM events WHERE seq > ?"
        params: list[Any] = [after_seq]

        if event_type is not None:
            query += " AND event_type = ?"
            params.append(event_type)
        if start_time is not None:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time is not None:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY seq"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_event(r) for r in rows]

    def get_current_version(self, stream_id: str) -> int:
        """Get the current version of a stream."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) FROM events WHERE stream_id = ?",
                (stream_id,),
            ).fetchone()
        return row[0] if row else 0

    def subscribe(self, callback: Callable[[StoredEvent], None]) -> None:
        """Subscribe to new events."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[StoredEvent], None]) -> None:
        """Unsubscribe from new events."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify(self, event: StoredEvent) -> None:
        for cb in list(self._subscribers):
            cb(event)

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> StoredEvent:
        return StoredEvent(
            event_id=row["event_id"],
            stream_id=row["stream_id"],
            event_type=row["event_type"],
            payload=json.loads(row["payload"]),
            version=row["version"],
            timestamp=row["timestamp"],
            metadata=json.loads(row["metadata"]),
        )
