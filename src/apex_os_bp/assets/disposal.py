"""Asset disposal."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Dict, List, Optional

from apex_os_bp.assets.models import (
    Asset,
    AssetStatus,
    DisposalMethod,
    DisposalRecord,
)


class AssetDisposal:
    """Manage asset disposal process."""

    def __init__(self):
        self._records: Dict[str, DisposalRecord] = {}

    def dispose_asset(
        self,
        asset: Asset,
        disposal_method: DisposalMethod,
        proceeds: float,
        book_value_at_disposal: float,
        disposal_date: Optional[date] = None,
        buyer: str = "",
        reason: str = "",
        approved_by: str = "",
    ) -> DisposalRecord:
        """Dispose of an asset."""
        if asset.status == AssetStatus.DISPOSED:
            raise ValueError(f"Asset {asset.id} is already disposed")

        gain_loss = proceeds - book_value_at_disposal

        record = DisposalRecord(
            id=str(uuid.uuid4()),
            asset_id=asset.id,
            disposal_method=disposal_method,
            disposal_date=disposal_date or date.today(),
            proceeds=proceeds,
            book_value_at_disposal=book_value_at_disposal,
            gain_loss=gain_loss,
            buyer=buyer,
            reason=reason,
            approved_by=approved_by,
        )
        self._records[record.id] = record

        # Update asset status
        asset.status = AssetStatus.DISPOSED

        return record

    def get_disposal(self, record_id: str) -> Optional[DisposalRecord]:
        """Get disposal record by ID."""
        return self._records.get(record_id)

    def get_disposals_for_asset(self, asset_id: str) -> List[DisposalRecord]:
        """Get all disposal records for an asset."""
        return [r for r in self._records.values() if r.asset_id == asset_id]

    def get_disposal_history(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[DisposalRecord]:
        """Get disposal history, optionally filtered by date range."""
        records = list(self._records.values())
        if start_date:
            records = [r for r in records if r.disposal_date >= start_date]
        if end_date:
            records = [r for r in records if r.disposal_date <= end_date]
        return sorted(records, key=lambda r: r.disposal_date, reverse=True)

    def get_total_proceeds(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> float:
        """Get total disposal proceeds."""
        records = self.get_disposal_history(start_date, end_date)
        return sum(r.proceeds for r in records)

    def get_total_gain_loss(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> float:
        """Get total gain/loss on disposals."""
        records = self.get_disposal_history(start_date, end_date)
        return sum(r.gain_loss for r in records)

    def get_disposals_by_method(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[DisposalMethod, List[DisposalRecord]]:
        """Group disposals by method."""
        records = self.get_disposal_history(start_date, end_date)
        result: Dict[DisposalMethod, List[DisposalRecord]] = {}
        for r in records:
            if r.disposal_method not in result:
                result[r.disposal_method] = []
            result[r.disposal_method].append(r)
        return result

    @staticmethod
    def calculate_gain_loss(
        proceeds: float,
        book_value: float,
    ) -> float:
        """Calculate gain or loss on disposal."""
        return proceeds - book_value

    def is_profitable_disposal(self, record: DisposalRecord) -> bool:
        """Check if disposal resulted in a gain."""
        return record.gain_loss > 0
