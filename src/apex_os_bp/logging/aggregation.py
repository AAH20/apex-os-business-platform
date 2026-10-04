"""Log aggregation — collect, merge, and batch log entries from multiple sources."""

from __future__ import annotations

import heapq
import threading
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from .structured import LogEntry, LogLevel


class LogAggregator:
    """Aggregates log entries from multiple sources with buffering and batching."""

    def __init__(self, max_buffer_size: int = 10000, flush_interval: float = 5.0):
        self.max_buffer_size = max_buffer_size
        self.flush_interval = flush_interval
        self._buffer: List[LogEntry] = []
        self._lock = threading.Lock()
        self._flush_callbacks: List[Callable[[List[LogEntry]], None]] = []
        self._sources: Dict[str, int] = defaultdict(int)
        self._total_aggregated = 0

    def add_entry(self, entry: LogEntry, source: str = "default") -> None:
        """Add a single log entry to the aggregation buffer."""
        with self._lock:
            self._buffer.append(entry)
            self._sources[source] += 1
            self._total_aggregated += 1
            if len(self._buffer) >= self.max_buffer_size:
                self._flush_unlocked()

    def add_entries(self, entries: Iterable[LogEntry], source: str = "default") -> int:
        """Add multiple entries; returns count added."""
        count = 0
        for entry in entries:
            self.add_entry(entry, source=source)
            count += 1
        return count

    def merge(self, other: "LogAggregator") -> "LogAggregator":
        """Merge another aggregator's buffer into this one."""
        with self._lock:
            with other._lock:
                for entry in other._buffer:
                    self._buffer.append(entry)
                for src, cnt in other._sources.items():
                    self._sources[src] += cnt
                self._total_aggregated += other._total_aggregated
                other._buffer.clear()
                other._sources.clear()
                other._total_aggregated = 0
        return self

    def flush(self) -> List[LogEntry]:
        """Flush the buffer, returning all entries and clearing it."""
        with self._lock:
            return self._flush_unlocked()

    def _flush_unlocked(self) -> List[LogEntry]:
        """Flush without acquiring the lock (caller must hold lock)."""
        if not self._buffer:
            return []
        entries = self._buffer.copy()
        self._buffer.clear()
        for callback in self._flush_callbacks:
            try:
                callback(entries)
            except Exception:
                pass
        return entries

    def on_flush(self, callback: Callable[[List[LogEntry]], None]) -> None:
        """Register a callback invoked on flush with the batch of entries."""
        self._flush_callbacks.append(callback)

    def get_buffer_size(self) -> int:
        """Current number of entries in the buffer."""
        return len(self._buffer)

    def get_source_counts(self) -> Dict[str, int]:
        """Return counts of entries per source."""
        return dict(self._sources)

    def get_total_aggregated(self) -> int:
        """Total number of entries ever aggregated."""
        return self._total_aggregated

    def get_entries(
        self,
        level: Optional[LogLevel] = None,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[LogEntry]:
        """Get filtered entries from the buffer without flushing."""
        with self._lock:
            entries = self._buffer.copy()
        return filter_entries(entries, level=level, source=source, since=since, until=until)

    def merge_sorted(
        self, sources: Iterable[Iterable[LogEntry]]
    ) -> List[LogEntry]:
        """Merge multiple sorted entry streams into one sorted list."""
        iterators = [iter(s) for s in sources]
        return list(heapq.merge(*iterators, key=lambda e: e.timestamp))

    def clear(self) -> None:
        """Clear the buffer and reset counters."""
        with self._lock:
            self._buffer.clear()
            self._sources.clear()
            self._total_aggregated = 0


def filter_entries(
    entries: Iterable[LogEntry],
    level: Optional[LogLevel] = None,
    source: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> List[LogEntry]:
    """Filter entries by level, source, and time range."""
    result = []
    for entry in entries:
        if level is not None and entry.level.value < level.value:
            continue
        if source is not None and entry.source != source:
            continue
        if since is not None and entry.timestamp < since:
            continue
        if until is not None and entry.timestamp > until:
            continue
        result.append(entry)
    return result


class AggregationStats:
    """Statistics about aggregated logs."""

    def __init__(self):
        self.total_entries: int = 0
        self.entries_by_level: Dict[str, int] = defaultdict(int)
        self.entries_by_source: Dict[str, int] = defaultdict(int)
        self.entries_by_minute: Dict[str, int] = defaultdict(int)
        self.error_rate: float = 0.0
        self.time_range: Optional[Tuple[datetime, datetime]] = None

    def compute(self, entries: Iterable[LogEntry]) -> "AggregationStats":
        """Compute statistics from an iterable of entries."""
        entries_list = list(entries)
        self.total_entries = len(entries_list)

        if not entries_list:
            return self

        timestamps = []
        error_count = 0
        for entry in entries_list:
            self.entries_by_level[entry.level.name] += 1
            self.entries_by_source[entry.source] += 1
            minute_key = entry.timestamp.strftime("%Y-%m-%dT%H:%M")
            self.entries_by_minute[minute_key] += 1
            timestamps.append(entry.timestamp)
            if entry.level.value >= LogLevel.ERROR.value:
                error_count += 1

        self.error_rate = error_count / self.total_entries if self.total_entries else 0.0
        self.time_range = (min(timestamps), max(timestamps))
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "total_entries": self.total_entries,
            "entries_by_level": dict(self.entries_by_level),
            "entries_by_source": dict(self.entries_by_source),
            "entries_by_minute": dict(self.entries_by_minute),
            "error_rate": self.error_rate,
            "time_range": (
                [self.time_range[0].isoformat(), self.time_range[1].isoformat()]
                if self.time_range
                else None
            ),
        }
