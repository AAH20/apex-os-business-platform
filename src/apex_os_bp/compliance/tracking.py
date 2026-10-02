"""Compliance tracking module."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from .models import ComplianceItem, ComplianceStatus


class ComplianceTracker:
    """Tracks compliance items and their statuses."""

    def __init__(self) -> None:
        self._items: dict[str, ComplianceItem] = {}

    def add_item(self, item: ComplianceItem) -> ComplianceItem:
        """Add a compliance item."""
        self._items[item.id] = item
        return item

    def get_item(self, item_id: str) -> ComplianceItem | None:
        """Get a compliance item by ID."""
        return self._items.get(item_id)

    def update_status(
        self, item_id: str, status: ComplianceStatus, notes: str = ""
    ) -> ComplianceItem | None:
        """Update the status of a compliance item."""
        item = self._items.get(item_id)
        if item is None:
            return None
        item.status = status
        if notes:
            item.notes = notes
        item.last_assessed = datetime.utcnow()
        item.updated_at = datetime.utcnow()
        return item

    def add_evidence(self, item_id: str, evidence: str) -> ComplianceItem | None:
        """Add evidence to a compliance item."""
        item = self._items.get(item_id)
        if item is None:
            return None
        item.evidence.append(evidence)
        item.updated_at = datetime.utcnow()
        return item

    def remove_item(self, item_id: str) -> bool:
        """Remove a compliance item."""
        if item_id in self._items:
            del self._items[item_id]
            return True
        return False

    def list_items(
        self,
        status: ComplianceStatus | None = None,
        category: str | None = None,
        regulation: str | None = None,
        owner: str | None = None,
    ) -> list[ComplianceItem]:
        """List compliance items with optional filters."""
        items = list(self._items.values())
        if status is not None:
            items = [i for i in items if i.status == status]
        if category is not None:
            items = [i for i in items if i.category == category]
        if regulation is not None:
            items = [i for i in items if i.regulation == regulation]
        if owner is not None:
            items = [i for i in items if i.owner == owner]
        return items

    def get_overdue_items(self) -> list[ComplianceItem]:
        """Get items that are past their due date and not compliant."""
        today = date.today()
        return [
            i for i in self._items.values()
            if i.due_date is not None
            and i.due_date < today
            and i.status not in (ComplianceStatus.COMPLIANT, ComplianceStatus.EXEMPTED)
        ]

    def get_status_summary(self) -> dict[str, int]:
        """Get a summary count of items by status."""
        summary: dict[str, int] = defaultdict(int)
        for item in self._items.values():
            summary[item.status.value] += 1
        return dict(summary)

    def get_compliance_rate(self) -> float:
        """Get the compliance rate as a percentage (0-100)."""
        if not self._items:
            return 0.0
        compliant = sum(
            1 for i in self._items.values()
            if i.status == ComplianceStatus.COMPLIANT
        )
        return (compliant / len(self._items)) * 100.0

    def get_items_by_category(self) -> dict[str, list[ComplianceItem]]:
        """Group items by category."""
        grouped: dict[str, list[ComplianceItem]] = defaultdict(list)
        for item in self._items.values():
            grouped[item.category].append(item)
        return dict(grouped)

    def get_items_by_regulation(self) -> dict[str, list[ComplianceItem]]:
        """Group items by regulation."""
        grouped: dict[str, list[ComplianceItem]] = defaultdict(list)
        for item in self._items.values():
            grouped[item.regulation].append(item)
        return dict(grouped)

    def to_dict(self) -> dict[str, Any]:
        """Export all items as a dictionary."""
        return {
            "items": {k: v.to_dict() for k, v in self._items.items()},
            "summary": self.get_status_summary(),
            "compliance_rate": self.get_compliance_rate(),
        }

    def __len__(self) -> int:
        return len(self._items)
