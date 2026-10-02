"""Memory Management Module.

Provides short-term (working) memory and long-term memory
with persistence, retrieval, and context management.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class MemoryType(str, Enum):
    """Type of memory entry."""

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


@dataclass
class MemoryEntry:
    """A single memory entry."""

    content: str
    memory_type: MemoryType
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    importance: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    access_count: int = 0
    last_accessed: float = 0.0

    def touch(self) -> None:
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = time.time()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        d = asdict(self)
        d["memory_type"] = self.memory_type.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryEntry:
        """Deserialize from dictionary."""
        data = dict(data)
        data["memory_type"] = MemoryType(data["memory_type"])
        return cls(**data)


class MemoryManager:
    """Manages agent memory with short-term and long-term storage.

    Supports adding, searching, retrieving, and forgetting memories.
    Includes importance-based eviction for short-term memory.
    """

    def __init__(
        self,
        short_term_capacity: int = 100,
        long_term_capacity: int = 1000,
        persist_path: str | None = None,
    ) -> None:
        self._short_term: list[MemoryEntry] = []
        self._long_term: list[MemoryEntry] = []
        self._short_term_capacity = short_term_capacity
        self._long_term_capacity = long_term_capacity
        self._persist_path = Path(persist_path) if persist_path else None

        if self._persist_path and self._persist_path.exists():
            self._load()

    def add(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> MemoryEntry:
        """Add a new memory entry."""
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            importance=max(0.0, min(1.0, importance)),
            metadata=metadata or {},
            tags=tags or [],
        )

        if memory_type == MemoryType.SHORT_TERM:
            self._short_term.append(entry)
            self._evict_short_term()
        else:
            self._long_term.append(entry)
            self._evict_long_term()

        return entry

    def search(
        self,
        query: str,
        memory_type: MemoryType | None = None,
        limit: int = 10,
        min_importance: float = 0.0,
    ) -> list[MemoryEntry]:
        """Search memories by content similarity (substring match)."""
        query_lower = query.lower()
        pool = self._get_pool(memory_type)

        scored: list[tuple[float, MemoryEntry]] = []
        for entry in pool:
            if entry.importance < min_importance:
                continue
            score = self._compute_score(entry, query_lower)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [entry for _, entry in scored[:limit]]
        for entry in results:
            entry.touch()
        return results

    def get_recent(
        self,
        memory_type: MemoryType | None = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Get most recent memories."""
        pool = self._get_pool(memory_type)
        sorted_pool = sorted(pool, key=lambda e: e.timestamp, reverse=True)
        return sorted_pool[:limit]

    def get_by_id(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID."""
        for entry in self._short_term + self._long_term:
            if entry.entry_id == entry_id:
                entry.touch()
                return entry
        return None

    def forget(self, entry_id: str) -> bool:
        """Remove a memory entry by ID."""
        for pool in (self._short_term, self._long_term):
            for i, entry in enumerate(pool):
                if entry.entry_id == entry_id:
                    pool.pop(i)
                    return True
        return False

    def clear(self, memory_type: MemoryType | None = None) -> None:
        """Clear memories, optionally filtered by type."""
        if memory_type is None:
            self._short_term.clear()
            self._long_term.clear()
        elif memory_type == MemoryType.SHORT_TERM:
            self._short_term.clear()
        else:
            self._long_term.clear()

    def promote(self, entry_id: str) -> bool:
        """Promote a short-term memory to long-term."""
        for i, entry in enumerate(self._short_term):
            if entry.entry_id == entry_id:
                promoted = self._short_term.pop(i)
                promoted.memory_type = MemoryType.LONG_TERM
                self._long_term.append(promoted)
                self._evict_long_term()
                return True
        return False

    def get_context_window(self, max_entries: int = 20) -> str:
        """Get a formatted context window of recent memories."""
        recent = self.get_recent(limit=max_entries)
        lines = []
        for entry in recent:
            prefix = "[ST]" if entry.memory_type == MemoryType.SHORT_TERM else "[LT]"
            lines.append(f"{prefix} {entry.content}")
        return "\n".join(lines)

    def persist(self) -> None:
        """Persist memories to disk."""
        if not self._persist_path:
            return
        data = {
            "short_term": [e.to_dict() for e in self._short_term],
            "long_term": [e.to_dict() for e in self._long_term],
        }
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._persist_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        return {
            "short_term_count": len(self._short_term),
            "long_term_count": len(self._long_term),
            "total_count": len(self._short_term) + len(self._long_term),
            "short_term_capacity": self._short_term_capacity,
            "long_term_capacity": self._long_term_capacity,
        }

    def _get_pool(self, memory_type: MemoryType | None) -> list[MemoryEntry]:
        if memory_type == MemoryType.SHORT_TERM:
            return self._short_term
        if memory_type == MemoryType.LONG_TERM:
            return self._long_term
        return self._short_term + self._long_term

    def _compute_score(self, entry: MemoryEntry, query: str) -> float:
        """Compute relevance score for a memory entry."""
        content_lower = entry.content.lower()
        if query in content_lower:
            base = 1.0
        else:
            words = query.split()
            matches = sum(1 for w in words if w in content_lower)
            base = matches / len(words) if words else 0.0

        recency = 1.0 / (1.0 + (time.time() - entry.timestamp) / 3600)
        return base * 0.6 + entry.importance * 0.2 + recency * 0.2

    def _evict_short_term(self) -> None:
        """Evict least important short-term memories when over capacity."""
        while len(self._short_term) > self._short_term_capacity:
            self._short_term.sort(key=lambda e: e.importance)
            self._short_term.pop(0)

    def _evict_long_term(self) -> None:
        """Evict least important long-term memories when over capacity."""
        while len(self._long_term) > self._long_term_capacity:
            self._long_term.sort(key=lambda e: e.importance)
            self._long_term.pop(0)

    def _load(self) -> None:
        """Load memories from disk."""
        try:
            with open(self._persist_path, "r") as f:
                data = json.load(f)
            self._short_term = [
                MemoryEntry.from_dict(d) for d in data.get("short_term", [])
            ]
            self._long_term = [
                MemoryEntry.from_dict(d) for d in data.get("long_term", [])
            ]
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
