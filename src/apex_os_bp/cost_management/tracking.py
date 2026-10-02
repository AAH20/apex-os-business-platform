"""Cost tracking engine."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from apex_os_bp.cost_management.models import (
    CostCategory,
    CostEntry,
    CostStatus,
)


class CostTracker:
    """Tracks and manages cost entries."""

    def __init__(self):
        self._entries: Dict[str, CostEntry] = {}

    def add_entry(self, entry: CostEntry) -> CostEntry:
        """Add a cost entry."""
        self._entries[entry.id] = entry
        return entry

    def create_entry(
        self,
        category: CostCategory,
        amount: float,
        currency: str,
        description: str,
        department_id: Optional[str] = None,
        project_id: Optional[str] = None,
        vendor_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> CostEntry:
        """Create and add a new cost entry."""
        entry = CostEntry.create(
            category=category,
            amount=amount,
            currency=currency,
            description=description,
            department_id=department_id,
            project_id=project_id,
            vendor_id=vendor_id,
            tags=tags,
            metadata=metadata,
        )
        return self.add_entry(entry)

    def get_entry(self, entry_id: str) -> Optional[CostEntry]:
        """Get a cost entry by ID."""
        return self._entries.get(entry_id)

    def get_all_entries(self) -> List[CostEntry]:
        """Get all cost entries."""
        return list(self._entries.values())

    def get_entries_by_category(self, category: CostCategory) -> List[CostEntry]:
        """Get entries filtered by category."""
        return [e for e in self._entries.values() if e.category == category]

    def get_entries_by_department(self, department_id: str) -> List[CostEntry]:
        """Get entries filtered by department."""
        return [e for e in self._entries.values() if e.department_id == department_id]

    def get_entries_by_project(self, project_id: str) -> List[CostEntry]:
        """Get entries filtered by project."""
        return [e for e in self._entries.values() if e.project_id == project_id]

    def get_entries_by_status(self, status: CostStatus) -> List[CostEntry]:
        """Get entries filtered by status."""
        return [e for e in self._entries.values() if e.status == status]

    def get_entries_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[CostEntry]:
        """Get entries within a date range."""
        return [
            e for e in self._entries.values()
            if start_date <= e.incurred_date <= end_date
        ]

    def get_entries_by_vendor(self, vendor_id: str) -> List[CostEntry]:
        """Get entries filtered by vendor."""
        return [e for e in self._entries.values() if e.vendor_id == vendor_id]

    def get_entries_by_tags(self, tags: List[str]) -> List[CostEntry]:
        """Get entries matching any of the given tags."""
        return [
            e for e in self._entries.values()
            if any(tag in e.tags for tag in tags)
        ]

    def approve_entry(self, entry_id: str) -> CostEntry:
        """Approve a cost entry."""
        entry = self._entries.get(entry_id)
        if not entry:
            raise ValueError(f"Cost entry not found: {entry_id}")
        entry.approve()
        return entry

    def reject_entry(self, entry_id: str) -> CostEntry:
        """Reject a cost entry."""
        entry = self._entries.get(entry_id)
        if not entry:
            raise ValueError(f"Cost entry not found: {entry_id}")
        entry.reject()
        return entry

    def mark_paid(self, entry_id: str) -> CostEntry:
        """Mark a cost entry as paid."""
        entry = self._entries.get(entry_id)
        if not entry:
            raise ValueError(f"Cost entry not found: {entry_id}")
        entry.mark_paid()
        return entry

    def cancel_entry(self, entry_id: str) -> CostEntry:
        """Cancel a cost entry."""
        entry = self._entries.get(entry_id)
        if not entry:
            raise ValueError(f"Cost entry not found: {entry_id}")
        entry.cancel()
        return entry

    def delete_entry(self, entry_id: str) -> bool:
        """Delete a cost entry."""
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False

    def get_total_cost(
        self,
        category: Optional[CostCategory] = None,
        department_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[CostStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> float:
        """Get total cost with optional filters."""
        entries = self._entries.values()
        if category:
            entries = [e for e in entries if e.category == category]
        if department_id:
            entries = [e for e in entries if e.department_id == department_id]
        if project_id:
            entries = [e for e in entries if e.project_id == project_id]
        if status:
            entries = [e for e in entries if e.status == status]
        if start_date:
            entries = [e for e in entries if e.incurred_date >= start_date]
        if end_date:
            entries = [e for e in entries if e.incurred_date <= end_date]
        return sum(e.amount for e in entries)

    def get_cost_by_category(self) -> Dict[CostCategory, float]:
        """Get total cost grouped by category."""
        result: Dict[CostCategory, float] = {}
        for entry in self._entries.values():
            result[entry.category] = result.get(entry.category, 0.0) + entry.amount
        return result

    def get_cost_by_department(self) -> Dict[str, float]:
        """Get total cost grouped by department."""
        result: Dict[str, float] = {}
        for entry in self._entries.values():
            dept = entry.department_id or "unassigned"
            result[dept] = result.get(dept, 0.0) + entry.amount
        return result

    def get_cost_by_project(self) -> Dict[str, float]:
        """Get total cost grouped by project."""
        result: Dict[str, float] = {}
        for entry in self._entries.values():
            proj = entry.project_id or "unassigned"
            result[proj] = result.get(proj, 0.0) + entry.amount
        return result

    def get_cost_by_vendor(self) -> Dict[str, float]:
        """Get total cost grouped by vendor."""
        result: Dict[str, float] = {}
        for entry in self._entries.values():
            vendor = entry.vendor_id or "unassigned"
            result[vendor] = result.get(vendor, 0.0) + entry.amount
        return result

    def get_monthly_cost(self, year: int, month: int) -> float:
        """Get total cost for a specific month."""
        return self.get_total_cost(
            start_date=datetime(year, month, 1),
            end_date=datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1),
        )

    def get_cost_trend(
        self,
        periods: int = 12,
        period_days: int = 30,
    ) -> List[Dict]:
        """Get cost trend over time periods."""
        trend = []
        now = datetime.now()
        for i in range(periods):
            end = now - timedelta(days=i * period_days)
            start = end - timedelta(days=period_days)
            total = self.get_total_cost(start_date=start, end_date=end)
            trend.append({
                "period_start": start,
                "period_end": end,
                "total_cost": total,
            })
        return list(reversed(trend))

    def search_entries(self, query: str) -> List[CostEntry]:
        """Search entries by description or tags."""
        query_lower = query.lower()
        return [
            e for e in self._entries.values()
            if query_lower in e.description.lower()
            or any(query_lower in tag.lower() for tag in e.tags)
        ]

    def get_entry_count(self) -> int:
        """Get total number of entries."""
        return len(self._entries)

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
