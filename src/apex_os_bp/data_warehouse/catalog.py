"""Data catalog module for data warehouse.

Provides data catalog entries, tagging, search, and metadata management
for discovering and understanding data assets.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class AssetType(Enum):
    """Types of data assets."""

    TABLE = "table"
    VIEW = "view"
    REPORT = "report"
    DASHBOARD = "dashboard"
    PIPELINE = "pipeline"
    MODEL = "model"
    DATASET = "dataset"
    SCHEMA = "schema"
    COLUMN = "column"


class AssetStatus(Enum):
    """Status of a data asset."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DRAFT = "draft"
    ARCHIVED = "archived"
    PENDING = "pending"


@dataclass
class CatalogTag:
    """Represents a tag for catalog entries."""

    name: str
    value: str = ""
    category: str = ""

    def to_dict(self) -> Dict[str, str]:
        """Convert tag to dictionary."""
        return {"name": self.name, "value": self.value, "category": self.category}


@dataclass
class CatalogEntry:
    """Represents a data catalog entry."""

    id: str
    name: str
    asset_type: AssetType
    description: str = ""
    owner: str = ""
    status: AssetStatus = AssetStatus.ACTIVE
    tags: List[CatalogTag] = field(default_factory=list)
    columns: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "1.0.0"
    parent_id: Optional[str] = None
    child_ids: List[str] = field(default_factory=list)
    lineage: List[str] = field(default_factory=list)
    quality_score: Optional[float] = None
    usage_count: int = 0
    rating: float = 0.0
    rating_count: int = 0

    def add_tag(self, tag: CatalogTag) -> None:
        """Add a tag to the entry."""
        self.tags.append(tag)

    def remove_tag(self, tag_name: str) -> bool:
        """Remove a tag by name."""
        for i, tag in enumerate(self.tags):
            if tag.name == tag_name:
                self.tags.pop(i)
                return True
        return False

    def update_metadata(self, key: str, value: Any) -> None:
        """Update metadata."""
        self.metadata[key] = value
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def add_column(self, column: Dict[str, Any]) -> None:
        """Add a column definition."""
        self.columns.append(column)

    def record_usage(self) -> None:
        """Record a usage event."""
        self.usage_count += 1

    def add_rating(self, rating: float) -> None:
        """Add a rating to the entry."""
        if not 0.0 <= rating <= 5.0:
            raise ValueError("Rating must be between 0.0 and 5.0")
        total = self.rating * self.rating_count + rating
        self.rating_count += 1
        self.rating = total / self.rating_count

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "asset_type": self.asset_type.value,
            "description": self.description,
            "owner": self.owner,
            "status": self.status.value,
            "tags": [t.to_dict() for t in self.tags],
            "columns": self.columns,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "parent_id": self.parent_id,
            "child_ids": self.child_ids,
            "lineage": self.lineage,
            "quality_score": self.quality_score,
            "usage_count": self.usage_count,
            "rating": self.rating,
            "rating_count": self.rating_count,
        }


@dataclass
class SearchResult:
    """Represents a search result."""

    entry: CatalogEntry
    score: float
    matched_fields: List[str] = field(default_factory=list)
    highlights: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "entry": self.entry.to_dict(),
            "score": self.score,
            "matched_fields": self.matched_fields,
            "highlights": self.highlights,
        }


class DataCatalog:
    """Main data catalog manager."""

    def __init__(self):
        self._entries: Dict[str, CatalogEntry] = {}
        self._indexes: Dict[str, Set[str]] = {
            "name": set(),
            "tag": set(),
            "owner": set(),
            "type": set(),
            "status": set(),
        }
        self._search_history: List[Dict[str, Any]] = []

    def add_entry(self, entry: CatalogEntry) -> None:
        """Add an entry to the catalog."""
        self._entries[entry.id] = entry
        self._update_indexes(entry)

    def remove_entry(self, entry_id: str) -> bool:
        """Remove an entry from the catalog."""
        if entry_id in self._entries:
            entry = self._entries[entry_id]
            self._remove_from_indexes(entry)
            del self._entries[entry_id]
            return True
        return False

    def get_entry(self, entry_id: str) -> Optional[CatalogEntry]:
        """Get an entry by ID."""
        return self._entries.get(entry_id)

    def get_by_name(self, name: str) -> List[CatalogEntry]:
        """Get entries by name."""
        return [e for e in self._entries.values() if e.name == name]

    def list_entries(
        self,
        asset_type: Optional[AssetType] = None,
        status: Optional[AssetStatus] = None,
        owner: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[CatalogEntry]:
        """List entries with optional filters."""
        results = list(self._entries.values())
        if asset_type:
            results = [e for e in results if e.asset_type == asset_type]
        if status:
            results = [e for e in results if e.status == status]
        if owner:
            results = [e for e in results if e.owner == owner]
        if tags:
            results = [e for e in results if any(t.name in tags for t in e.tags)]
        return results

    def search(self, query: str, limit: int = 20) -> List[SearchResult]:
        """Search the catalog by query string."""
        query_lower = query.lower()
        results: List[SearchResult] = []

        for entry in self._entries.values():
            score = 0.0
            matched_fields: List[str] = []

            # Name match (highest weight)
            if query_lower in entry.name.lower():
                score += 10.0
                matched_fields.append("name")

            # Description match
            if query_lower in entry.description.lower():
                score += 5.0
                matched_fields.append("description")

            # Tag match
            for tag in entry.tags:
                if query_lower in tag.name.lower() or query_lower in tag.value.lower():
                    score += 3.0
                    matched_fields.append("tags")
                    break

            # Owner match
            if query_lower in entry.owner.lower():
                score += 2.0
                matched_fields.append("owner")

            # Column match
            for col in entry.columns:
                col_name = col.get("name", "")
                if query_lower in col_name.lower():
                    score += 4.0
                    matched_fields.append("columns")
                    break

            # Metadata match
            for key, value in entry.metadata.items():
                if query_lower in str(key).lower() or query_lower in str(value).lower():
                    score += 1.0
                    matched_fields.append("metadata")
                    break

            if score > 0:
                results.append(SearchResult(
                    entry=entry,
                    score=score,
                    matched_fields=list(set(matched_fields)),
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        self._search_history.append({
            "query": query,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results_count": len(results),
        })
        return results[:limit]

    def advanced_search(
        self,
        query: str = "",
        asset_types: Optional[List[AssetType]] = None,
        statuses: Optional[List[AssetStatus]] = None,
        owners: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        min_quality: Optional[float] = None,
        limit: int = 20,
    ) -> List[SearchResult]:
        """Advanced search with multiple filters."""
        results = self.search(query, limit=1000) if query else [
            SearchResult(entry=e, score=1.0) for e in self._entries.values()
        ]

        filtered: List[SearchResult] = []
        for result in results:
            entry = result.entry
            if asset_types and entry.asset_type not in asset_types:
                continue
            if statuses and entry.status not in statuses:
                continue
            if owners and entry.owner not in owners:
                continue
            if tags and not any(t.name in tags for t in entry.tags):
                continue
            if min_quality is not None and (entry.quality_score is None or entry.quality_score < min_quality):
                continue
            filtered.append(result)

        return filtered[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get catalog statistics."""
        entries = list(self._entries.values())
        return {
            "total_entries": len(entries),
            "by_type": self._count_by_type(entries),
            "by_status": self._count_by_status(entries),
            "by_owner": self._count_by_owner(entries),
            "total_tags": len(self._get_all_tags(entries)),
            "avg_quality_score": self._avg_quality(entries),
            "avg_rating": self._avg_rating(entries),
            "total_usage": sum(e.usage_count for e in entries),
            "search_queries_count": len(self._search_history),
        }

    def get_popular_entries(self, limit: int = 10) -> List[CatalogEntry]:
        """Get most popular entries by usage."""
        entries = list(self._entries.values())
        entries.sort(key=lambda e: e.usage_count, reverse=True)
        return entries[:limit]

    def get_recently_updated(self, limit: int = 10) -> List[CatalogEntry]:
        """Get recently updated entries."""
        entries = list(self._entries.values())
        entries.sort(key=lambda e: e.updated_at, reverse=True)
        return entries[:limit]

    def get_deprecated_entries(self) -> List[CatalogEntry]:
        """Get all deprecated entries."""
        return [e for e in self._entries.values() if e.status == AssetStatus.DEPRECATED]

    def suggest_related(self, entry_id: str, limit: int = 5) -> List[CatalogEntry]:
        """Suggest related entries based on tags and lineage."""
        entry = self._entries.get(entry_id)
        if not entry:
            return []

        tag_names = {t.name for t in entry.tags}
        related: List[tuple[float, CatalogEntry]] = []

        for other in self._entries.values():
            if other.id == entry_id:
                continue
            score = 0.0
            other_tags = {t.name for t in other.tags}
            common_tags = tag_names & other_tags
            score += len(common_tags) * 2.0
            if other.asset_type == entry.asset_type:
                score += 1.0
            if other.owner == entry.owner:
                score += 1.0
            if entry_id in other.lineage or other.id in entry.lineage:
                score += 5.0
            if score > 0:
                related.append((score, other))

        related.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in related[:limit]]

    def _update_indexes(self, entry: CatalogEntry) -> None:
        """Update indexes for an entry."""
        self._indexes["name"].add(entry.id)
        self._indexes["owner"].add(entry.id)
        self._indexes["type"].add(entry.id)
        self._indexes["status"].add(entry.id)
        for tag in entry.tags:
            self._indexes["tag"].add(entry.id)

    def _remove_from_indexes(self, entry: CatalogEntry) -> None:
        """Remove entry from indexes."""
        for idx in self._indexes.values():
            idx.discard(entry.id)

    def _count_by_type(self, entries: List[CatalogEntry]) -> Dict[str, int]:
        """Count entries by type."""
        counts: Dict[str, int] = {}
        for e in entries:
            key = e.asset_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _count_by_status(self, entries: List[CatalogEntry]) -> Dict[str, int]:
        """Count entries by status."""
        counts: Dict[str, int] = {}
        for e in entries:
            key = e.status.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _count_by_owner(self, entries: List[CatalogEntry]) -> Dict[str, int]:
        """Count entries by owner."""
        counts: Dict[str, int] = {}
        for e in entries:
            key = e.owner or "unassigned"
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _get_all_tags(self, entries: List[CatalogEntry]) -> Set[str]:
        """Get all unique tag names."""
        tags: Set[str] = set()
        for e in entries:
            for t in e.tags:
                tags.add(t.name)
        return tags

    def _avg_quality(self, entries: List[CatalogEntry]) -> Optional[float]:
        """Calculate average quality score."""
        scores = [e.quality_score for e in entries if e.quality_score is not None]
        return sum(scores) / len(scores) if scores else None

    def _avg_rating(self, entries: List[CatalogEntry]) -> Optional[float]:
        """Calculate average rating."""
        ratings = [e.rating for e in entries if e.rating_count > 0]
        return sum(ratings) / len(ratings) if ratings else None
