"""Log search — full-text and field-based search over log entries."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Pattern, Set, Tuple

from .structured import LogEntry, LogLevel


class SearchQuery:
    """Represents a structured search query."""

    def __init__(self):
        self.text: Optional[str] = None
        self.level: Optional[LogLevel] = None
        self.source: Optional[str] = None
        self.since: Optional[datetime] = None
        self.until: Optional[datetime] = None
        self.context_filters: Dict[str, Any] = {}
        self.trace_id: Optional[str] = None
        self.regex_pattern: Optional[str] = None
        self.case_sensitive: bool = False
        self.limit: Optional[int] = None
        self.offset: int = 0

    def with_text(self, text: str, case_sensitive: bool = False) -> "SearchQuery":
        self.text = text
        self.case_sensitive = case_sensitive
        return self

    def with_level(self, level: LogLevel) -> "SearchQuery":
        self.level = level
        return self

    def with_source(self, source: str) -> "SearchQuery":
        self.source = source
        return self

    def with_time_range(
        self, since: Optional[datetime] = None, until: Optional[datetime] = None
    ) -> "SearchQuery":
        self.since = since
        self.until = until
        return self

    def with_context(self, **kwargs: Any) -> "SearchQuery":
        self.context_filters.update(kwargs)
        return self

    def with_trace_id(self, trace_id: str) -> "SearchQuery":
        self.trace_id = trace_id
        return self

    def with_regex(self, pattern: str) -> "SearchQuery":
        self.regex_pattern = pattern
        return self

    def with_pagination(self, limit: int = 100, offset: int = 0) -> "SearchQuery":
        self.limit = limit
        self.offset = offset
        return self


class SearchResult:
    """Result of a log search."""

    def __init__(self, entries: List[LogEntry], total: int, query: SearchQuery):
        self.entries = entries
        self.total = total
        self.query = query

    @property
    def count(self) -> int:
        return len(self.entries)

    def __len__(self) -> int:
        return self.count

    def __iter__(self):
        return iter(self.entries)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "count": self.count,
            "entries": [e.to_dict() for e in self.entries],
        }


class LogSearch:
    """Search engine for log entries."""

    def __init__(self, entries: Optional[Iterable[LogEntry]] = None):
        self._entries: List[LogEntry] = []
        self._index: Dict[str, Set[int]] = defaultdict(set)
        self._level_index: Dict[str, Set[int]] = defaultdict(set)
        self._source_index: Dict[str, Set[int]] = defaultdict(set)
        self._trace_index: Dict[str, Set[int]] = defaultdict(set)
        self._context_index: Dict[str, Dict[Any, Set[int]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self._dirty = False
        if entries:
            self.add_entries(entries)

    def add_entry(self, entry: LogEntry) -> None:
        """Add a single entry to the search index."""
        idx = len(self._entries)
        self._entries.append(entry)
        self._index_entry(entry, idx)

    def add_entries(self, entries: Iterable[LogEntry]) -> int:
        """Add multiple entries; returns count added."""
        count = 0
        for entry in entries:
            self.add_entry(entry)
            count += 1
        return count

    def _index_entry(self, entry: LogEntry, idx: int) -> None:
        """Index a single entry for fast lookup."""
        # Index words from message
        words = re.findall(r"\w+", entry.message.lower())
        for word in words:
            self._index[word].add(idx)

        # Index level
        self._level_index[entry.level.name].add(idx)

        # Index source
        if entry.source:
            self._source_index[entry.source].add(idx)

        # Index trace_id
        if entry.trace_id:
            self._trace_index[entry.trace_id].add(idx)

        # Index context fields
        for key, value in entry.context.items():
            self._context_index[key][value].add(idx)

    def rebuild_index(self) -> None:
        """Rebuild all indexes from scratch."""
        self._index.clear()
        self._level_index.clear()
        self._source_index.clear()
        self._trace_index.clear()
        self._context_index.clear()
        for idx, entry in enumerate(self._entries):
            self._index_entry(entry, idx)
        self._dirty = False

    def search(self, query: SearchQuery) -> SearchResult:
        """Execute a search query and return results."""
        candidates: Optional[Set[int]] = None

        # Use indexes for exact-match filters
        if query.level is not None:
            level_matches = self._level_index.get(query.level.name, set())
            candidates = level_matches if candidates is None else candidates & level_matches

        if query.source is not None:
            source_matches = self._source_index.get(query.source, set())
            candidates = source_matches if candidates is None else candidates & source_matches

        if query.trace_id is not None:
            trace_matches = self._trace_index.get(query.trace_id, set())
            candidates = trace_matches if candidates is None else candidates & trace_matches

        for key, value in query.context_filters.items():
            ctx_matches = self._context_index.get(key, {}).get(value, set())
            candidates = ctx_matches if candidates is None else candidates & ctx_matches

        # If no indexed filters matched, scan all entries
        if candidates is None:
            candidates = set(range(len(self._entries)))

        # Apply text/regex/time filters
        matched: List[Tuple[int, LogEntry]] = []
        flags = 0 if query.case_sensitive else re.IGNORECASE
        compiled_regex: Optional[Pattern] = None
        if query.regex_pattern:
            try:
                compiled_regex = re.compile(query.regex_pattern, flags)
            except re.error:
                pass

        for idx in candidates:
            entry = self._entries[idx]

            if query.since is not None and entry.timestamp < query.since:
                continue
            if query.until is not None and entry.timestamp > query.until:
                continue

            if query.text is not None:
                text = entry.message
                search_text = query.text if query.case_sensitive else query.text.lower()
                haystack = text if query.case_sensitive else text.lower()
                if search_text not in haystack:
                    continue

            if compiled_regex is not None:
                if not compiled_regex.search(entry.message):
                    continue

            matched.append((idx, entry))

        # Sort by timestamp descending (most recent first)
        matched.sort(key=lambda x: x[1].timestamp, reverse=True)

        total = len(matched)

        # Apply pagination
        start = query.offset
        end = start + query.limit if query.limit is not None else total
        page = matched[start:end]

        return SearchResult([e for _, e in page], total, query)

    def find_by_text(
        self, text: str, limit: int = 100, case_sensitive: bool = False
    ) -> List[LogEntry]:
        """Quick text search."""
        query = SearchQuery().with_text(text, case_sensitive=case_sensitive).with_pagination(limit=limit)
        return self.search(query).entries

    def find_by_level(self, level: LogLevel, limit: int = 100) -> List[LogEntry]:
        """Quick level filter."""
        query = SearchQuery().with_level(level).with_pagination(limit=limit)
        return self.search(query).entries

    def find_by_trace(self, trace_id: str) -> List[LogEntry]:
        """Find all entries for a trace ID."""
        query = SearchQuery().with_trace_id(trace_id)
        return self.search(query).entries

    def find_by_time_range(
        self, since: datetime, until: datetime, limit: int = 1000
    ) -> List[LogEntry]:
        """Find entries within a time range."""
        query = SearchQuery().with_time_range(since, until).with_pagination(limit=limit)
        return self.search(query).entries

    def find_errors(self, limit: int = 100) -> List[LogEntry]:
        """Find all error-level entries."""
        query = SearchQuery().with_level(LogLevel.ERROR).with_pagination(limit=limit)
        return self.search(query).entries

    def count(self) -> int:
        """Total entries in the search index."""
        return len(self._entries)

    def clear(self) -> None:
        """Remove all entries and clear indexes."""
        self._entries.clear()
        self._index.clear()
        self._level_index.clear()
        self._source_index.clear()
        self._trace_index.clear()
        self._context_index.clear()
