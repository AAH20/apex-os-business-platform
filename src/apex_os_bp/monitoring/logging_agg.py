"""Log aggregation for APEX-OS.

Provides structured log entries, buffering, filtering, batching,
and forwarding to external log aggregation systems.
"""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional


class LogLevel(Enum):
    """Log severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @property
    def priority(self) -> int:
        """Numeric priority for comparison."""
        levels = {
            LogLevel.DEBUG: 10,
            LogLevel.INFO: 20,
            LogLevel.WARNING: 30,
            LogLevel.ERROR: 40,
            LogLevel.CRITICAL: 50,
        }
        return levels[self]

    def __ge__(self, other: "LogLevel") -> bool:
        return self.priority >= other.priority

    def __gt__(self, other: "LogLevel") -> bool:
        return self.priority > other.priority

    def __le__(self, other: "LogLevel") -> bool:
        return self.priority <= other.priority

    def __lt__(self, other: "LogLevel") -> bool:
        return self.priority < other.priority


@dataclass
class LogEntry:
    """A structured log entry."""

    message: str
    level: LogLevel
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message": self.message,
            "level": self.level.value,
            "timestamp": self.timestamp,
            "source": self.source,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "attributes": self.attributes,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogEntry":
        """Create a LogEntry from a dictionary."""
        return cls(
            message=data["message"],
            level=LogLevel(data["level"]),
            timestamp=data.get("timestamp", time.time()),
            source=data.get("source", ""),
            trace_id=data.get("trace_id"),
            span_id=data.get("span_id"),
            attributes=data.get("attributes", {}),
        )


class LogAggregator:
    """Aggregates, buffers, filters, and forwards log entries."""

    def __init__(
        self,
        buffer_size: int = 1000,
        batch_size: int = 100,
        flush_interval: float = 5.0,
        min_level: LogLevel = LogLevel.INFO,
    ):
        self._buffer: Deque[LogEntry] = deque(maxlen=buffer_size)
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._min_level = min_level
        self._handlers: List[Callable[[List[LogEntry]], None]] = []
        self._filters: List[Callable[[LogEntry], bool]] = []
        self._lock = threading.Lock()
        self._flush_callbacks: List[Callable[[List[LogEntry]], None]] = []
        self._last_flush = time.time()
        self._total_aggregated = 0
        self._total_dropped = 0

    def add_handler(self, handler: Callable[[List[LogEntry]], None]) -> None:
        """Add a handler that receives batches of log entries."""
        self._handlers.append(handler)

    def remove_handler(self, handler: Callable[[List[LogEntry]], None]) -> None:
        """Remove a handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)

    def add_filter(self, filter_fn: Callable[[LogEntry], bool]) -> None:
        """Add a filter function. Return True to keep the entry."""
        self._filters.append(filter_fn)

    def remove_filter(self, filter_fn: Callable[[LogEntry], bool]) -> None:
        """Remove a filter function."""
        if filter_fn in self._filters:
            self._filters.remove(filter_fn)

    def log(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        source: str = "",
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        **attributes: Any,
    ) -> Optional[LogEntry]:
        """Submit a log entry for aggregation."""
        if level < self._min_level:
            return None

        entry = LogEntry(
            message=message,
            level=level,
            source=source,
            trace_id=trace_id,
            span_id=span_id,
            attributes=attributes,
        )

        # Apply filters
        for filter_fn in self._filters:
            if not filter_fn(entry):
                return None

        with self._lock:
            if len(self._buffer) >= self._buffer.maxlen:
                self._total_dropped += 1
            self._buffer.append(entry)
            self._total_aggregated += 1

            should_flush = (
                len(self._buffer) >= self._batch_size
                or (time.time() - self._last_flush) >= self._flush_interval
            )

        if should_flush:
            self.flush()

        return entry

    def flush(self) -> List[LogEntry]:
        """Flush buffered log entries to all handlers."""
        with self._lock:
            if not self._buffer:
                return []
            batch = list(self._buffer)
            self._buffer.clear()
            self._last_flush = time.time()

        for handler in self._handlers:
            try:
                handler(batch)
            except Exception:
                pass  # Handlers should not crash the aggregator

        for callback in self._flush_callbacks:
            try:
                callback(batch)
            except Exception:
                pass

        return batch

    def on_flush(self, callback: Callable[[List[LogEntry]], None]) -> None:
        """Register a callback for flush events."""
        self._flush_callbacks.append(callback)

    def get_recent(self, count: int = 100, level: Optional[LogLevel] = None) -> List[LogEntry]:
        """Get recent log entries, optionally filtered by level."""
        with self._lock:
            entries = list(self._buffer)
        if level is not None:
            entries = [e for e in entries if e.level >= level]
        return entries[-count:]

    def search(
        self,
        query: str,
        level: Optional[LogLevel] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> List[LogEntry]:
        """Search log entries by message content, source, level, and source filter."""
        with self._lock:
            entries = list(self._buffer)

        results = []
        for entry in entries:
            if level is not None and entry.level < level:
                continue
            if source is not None and entry.source != source:
                continue
            if query.lower() not in entry.message.lower() and query.lower() not in entry.source.lower():
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregator statistics."""
        with self._lock:
            return {
                "buffered": len(self._buffer),
                "total_aggregated": self._total_aggregated,
                "total_dropped": self._total_dropped,
                "handlers": len(self._handlers),
                "filters": len(self._filters),
                "batch_size": self._batch_size,
                "flush_interval": self._flush_interval,
                "min_level": self._min_level.value,
            }

    def clear(self) -> None:
        """Clear the buffer and reset statistics."""
        with self._lock:
            self._buffer.clear()
            self._total_aggregated = 0
            self._total_dropped = 0
            self._last_flush = time.time()
