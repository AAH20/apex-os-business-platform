"""Report builder — construct reports from data sources."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ReportType(str, Enum):
    """Supported report types."""

    SUMMARY = "summary"
    DETAIL = "detail"
    ANALYTICS = "analytics"
    AUDIT = "audit"
    CUSTOM = "custom"


class ReportStatus(str, Enum):
    """Report lifecycle status."""

    DRAFT = "draft"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class ReportColumn:
    """Column definition for a report."""

    name: str
    label: str
    data_type: str = "string"
    width: int | None = None
    format: str | None = None
    visible: bool = True


@dataclass
class ReportFilter:
    """Filter applied to report data."""

    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, in, contains
    value: Any


@dataclass
class ReportDefinition:
    """Complete report definition."""

    name: str
    report_type: ReportType
    columns: list[ReportColumn]
    data_source: str
    filters: list[ReportFilter] = field(default_factory=list)
    group_by: list[str] = field(default_factory=list)
    order_by: list[str] = field(default_factory=list)
    limit: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: ReportStatus = ReportStatus.DRAFT


@dataclass
class ReportResult:
    """Result of building a report."""

    definition: ReportDefinition
    rows: list[dict[str, Any]]
    total_count: int
    generated_at: datetime = field(default_factory=datetime.utcnow)
    execution_time_ms: float = 0.0
    status: ReportStatus = ReportStatus.READY
    error: str | None = None


class ReportBuilder:
    """Builds reports from definitions and data sources."""

    def __init__(self) -> None:
        self._data_sources: dict[str, Any] = {}
        self._build_history: list[ReportResult] = []

    def register_data_source(self, name: str, source: Any) -> None:
        """Register a named data source."""
        self._data_sources[name] = source

    def create_definition(
        self,
        name: str,
        report_type: ReportType,
        columns: list[ReportColumn],
        data_source: str,
        filters: list[ReportFilter] | None = None,
        group_by: list[str] | None = None,
        order_by: list[str] | None = None,
        limit: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ReportDefinition:
        """Create a new report definition."""
        return ReportDefinition(
            name=name,
            report_type=report_type,
            columns=columns,
            data_source=data_source,
            filters=filters or [],
            group_by=group_by or [],
            order_by=order_by or [],
            limit=limit,
            metadata=metadata or {},
        )

    def build(self, definition: ReportDefinition) -> ReportResult:
        """Build a report from its definition."""
        import time

        start = time.perf_counter()
        try:
            if definition.data_source not in self._data_sources:
                raise ValueError(
                    f"Unknown data source: {definition.data_source}"
                )

            source = self._data_sources[definition.data_source]
            rows = self._fetch_data(source, definition)
            rows = self._apply_filters(rows, definition.filters)
            rows = self._apply_grouping(rows, definition.group_by)
            rows = self._apply_ordering(rows, definition.order_by)
            total = len(rows)
            if definition.limit is not None:
                rows = rows[: definition.limit]

            elapsed = (time.perf_counter() - start) * 1000
            result = ReportResult(
                definition=definition,
                rows=rows,
                total_count=total,
                execution_time_ms=elapsed,
                status=ReportStatus.READY,
            )
            definition.status = ReportStatus.READY
            self._build_history.append(result)
            return result

        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            definition.status = ReportStatus.FAILED
            result = ReportResult(
                definition=definition,
                rows=[],
                total_count=0,
                execution_time_ms=elapsed,
                status=ReportStatus.FAILED,
                error=str(exc),
            )
            self._build_history.append(result)
            return result

    def _fetch_data(
        self, source: Any, definition: ReportDefinition
    ) -> list[dict[str, Any]]:
        """Fetch raw data from the source."""
        if hasattr(source, "query"):
            return source.query(definition)
        if hasattr(source, "get_all"):
            return source.get_all()
        if isinstance(source, list):
            return source
        if isinstance(source, dict):
            return [source]
        raise TypeError(f"Unsupported data source type: {type(source)}")

    def _apply_filters(
        self, rows: list[dict[str, Any]], filters: list[ReportFilter]
    ) -> list[dict[str, Any]]:
        """Apply filters to rows."""
        for f in filters:
            rows = [r for r in rows if self._match_filter(r, f)]
        return rows

    def _match_filter(self, row: dict[str, Any], f: ReportFilter) -> bool:
        """Check if a row matches a filter."""
        val = row.get(f.field)
        if val is None:
            return False
        op = f.operator
        if op == "eq":
            return val == f.value
        if op == "ne":
            return val != f.value
        if op == "gt":
            return val > f.value
        if op == "lt":
            return val < f.value
        if op == "gte":
            return val >= f.value
        if op == "lte":
            return val <= f.value
        if op == "in":
            return val in f.value
        if op == "contains":
            return f.value in str(val)
        return True

    def _apply_grouping(
        self, rows: list[dict[str, Any]], group_by: list[str]
    ) -> list[dict[str, Any]]:
        """Group rows by specified fields."""
        if not group_by:
            return rows
        groups: dict[tuple, list[dict[str, Any]]] = {}
        for row in rows:
            key = tuple(row.get(g) for g in group_by)
            groups.setdefault(key, []).append(row)
        result = []
        for key, group_rows in groups.items():
            merged = {g: v for g, v in zip(group_by, key)}
            merged["_count"] = len(group_rows)
            merged["_items"] = group_rows
            result.append(merged)
        return result

    def _apply_ordering(
        self, rows: list[dict[str, Any]], order_by: list[str]
    ) -> list[dict[str, Any]]:
        """Sort rows by specified fields."""
        if not order_by:
            return rows
        result = list(rows)
        for field in reversed(order_by):
            reverse = field.startswith("-")
            clean = field.lstrip("-")
            result.sort(
                key=lambda r: (r.get(clean) is None, r.get(clean)),
                reverse=reverse,
            )
        return result

    def get_history(self) -> list[ReportResult]:
        """Get build history."""
        return list(self._build_history)

    def get_history_by_status(
        self, status: ReportStatus
    ) -> list[ReportResult]:
        """Get build history filtered by status."""
        return [r for r in self._build_history if r.status == status]
