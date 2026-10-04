"""Asset maintenance scheduling."""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Dict, List, Optional

from apex_os_bp.assets.models import (
    MaintenanceRecord,
    MaintenanceStatus,
    MaintenanceType,
)


class MaintenanceScheduler:
    """Schedule and track asset maintenance."""

    def __init__(self):
        self._records: Dict[str, MaintenanceRecord] = {}

    def schedule_maintenance(
        self,
        asset_id: str,
        maintenance_type: MaintenanceType,
        scheduled_date: date,
        description: str = "",
        technician: str = "",
        cost: float = 0.0,
        next_scheduled_date: Optional[date] = None,
    ) -> MaintenanceRecord:
        """Schedule a maintenance task."""
        record = MaintenanceRecord(
            id=str(uuid.uuid4()),
            asset_id=asset_id,
            maintenance_type=maintenance_type,
            status=MaintenanceStatus.SCHEDULED,
            scheduled_date=scheduled_date,
            description=description,
            technician=technician,
            cost=cost,
            next_scheduled_date=next_scheduled_date,
        )
        self._records[record.id] = record
        return record

    def start_maintenance(self, record_id: str) -> MaintenanceRecord:
        """Mark maintenance as in progress."""
        record = self._records.get(record_id)
        if not record:
            raise ValueError(f"Maintenance record not found: {record_id}")
        if record.status != MaintenanceStatus.SCHEDULED:
            raise ValueError(f"Cannot start maintenance with status: {record.status}")
        record.status = MaintenanceStatus.IN_PROGRESS
        return record

    def complete_maintenance(
        self,
        record_id: str,
        completion_date: Optional[date] = None,
        notes: str = "",
    ) -> MaintenanceRecord:
        """Mark maintenance as completed."""
        record = self._records.get(record_id)
        if not record:
            raise ValueError(f"Maintenance record not found: {record_id}")
        if record.status != MaintenanceStatus.IN_PROGRESS:
            raise ValueError(f"Cannot complete maintenance with status: {record.status}")
        record.status = MaintenanceStatus.COMPLETED
        record.completed_date = completion_date or date.today()
        if notes:
            record.notes = notes
        return record

    def cancel_maintenance(self, record_id: str, reason: str = "") -> MaintenanceRecord:
        """Cancel a scheduled maintenance."""
        record = self._records.get(record_id)
        if not record:
            raise ValueError(f"Maintenance record not found: {record_id}")
        if record.status not in (MaintenanceStatus.SCHEDULED, MaintenanceStatus.OVERDUE):
            raise ValueError(f"Cannot cancel maintenance with status: {record.status}")
        record.status = MaintenanceStatus.CANCELLED
        if reason:
            record.notes = reason
        return record

    def get_record(self, record_id: str) -> Optional[MaintenanceRecord]:
        """Get maintenance record by ID."""
        return self._records.get(record_id)

    def get_records_for_asset(self, asset_id: str) -> List[MaintenanceRecord]:
        """Get all maintenance records for an asset."""
        return [r for r in self._records.values() if r.asset_id == asset_id]

    def get_upcoming_maintenance(
        self,
        days: int = 30,
        as_of: Optional[date] = None,
    ) -> List[MaintenanceRecord]:
        """Get maintenance scheduled within the next N days."""
        as_of = as_of or date.today()
        cutoff = as_of + timedelta(days=days)
        return [
            r for r in self._records.values()
            if r.status == MaintenanceStatus.SCHEDULED
            and as_of <= r.scheduled_date <= cutoff
        ]

    def get_overdue_maintenance(self, as_of: Optional[date] = None) -> List[MaintenanceRecord]:
        """Get overdue maintenance tasks."""
        as_of = as_of or date.today()
        overdue = []
        for r in self._records.values():
            if r.status == MaintenanceStatus.SCHEDULED and r.scheduled_date < as_of:
                r.status = MaintenanceStatus.OVERDUE
                overdue.append(r)
        return overdue

    def get_maintenance_cost(self, asset_id: str) -> float:
        """Get total maintenance cost for an asset."""
        return sum(
            r.cost for r in self._records.values()
            if r.asset_id == asset_id and r.status == MaintenanceStatus.COMPLETED
        )

    def get_maintenance_history(
        self,
        asset_id: str,
        maintenance_type: Optional[MaintenanceType] = None,
    ) -> List[MaintenanceRecord]:
        """Get maintenance history for an asset, optionally filtered by type."""
        records = self.get_records_for_asset(asset_id)
        if maintenance_type:
            records = [r for r in records if r.maintenance_type == maintenance_type]
        return sorted(records, key=lambda r: r.scheduled_date, reverse=True)

    def schedule_recurring(
        self,
        asset_id: str,
        maintenance_type: MaintenanceType,
        first_date: date,
        interval_days: int,
        occurrences: int,
        description: str = "",
        technician: str = "",
        cost: float = 0.0,
    ) -> List[MaintenanceRecord]:
        """Schedule recurring maintenance."""
        records = []
        for i in range(occurrences):
            scheduled = first_date + timedelta(days=interval_days * i)
            next_date = first_date + timedelta(days=interval_days * (i + 1))
            record = self.schedule_maintenance(
                asset_id=asset_id,
                maintenance_type=maintenance_type,
                scheduled_date=scheduled,
                description=description,
                technician=technician,
                cost=cost,
                next_scheduled_date=next_date if i < occurrences - 1 else None,
            )
            records.append(record)
        return records
