"""Asset valuation."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Dict, List, Optional

from apex_os_bp.assets.models import Asset, ValuationRecord


class AssetValuator:
    """Asset valuation and revaluation."""

    def __init__(self):
        self._records: Dict[str, ValuationRecord] = {}

    def record_valuation(
        self,
        asset_id: str,
        market_value: float,
        book_value: float,
        valuation_method: str,
        valuation_date: Optional[date] = None,
        appraiser: str = "",
        notes: str = "",
    ) -> ValuationRecord:
        """Record a valuation for an asset."""
        record = ValuationRecord(
            id=str(uuid.uuid4()),
            asset_id=asset_id,
            valuation_date=valuation_date or date.today(),
            market_value=market_value,
            book_value=book_value,
            valuation_method=valuation_method,
            appraiser=appraiser,
            notes=notes,
        )
        self._records[record.id] = record
        return record

    def get_valuation(self, record_id: str) -> Optional[ValuationRecord]:
        """Get valuation record by ID."""
        return self._records.get(record_id)

    def get_valuations_for_asset(self, asset_id: str) -> List[ValuationRecord]:
        """Get all valuations for an asset."""
        return [r for r in self._records.values() if r.asset_id == asset_id]

    def get_latest_valuation(self, asset_id: str) -> Optional[ValuationRecord]:
        """Get the most recent valuation for an asset."""
        records = self.get_valuations_for_asset(asset_id)
        if not records:
            return None
        return max(records, key=lambda r: r.valuation_date)

    def get_valuation_history(self, asset_id: str) -> List[ValuationRecord]:
        """Get valuation history sorted by date."""
        records = self.get_valuations_for_asset(asset_id)
        return sorted(records, key=lambda r: r.valuation_date)

    @staticmethod
    def calculate_impairment(
        asset: Asset,
        recoverable_amount: float,
        book_value: float,
    ) -> float:
        """Calculate impairment loss."""
        if recoverable_amount >= book_value:
            return 0.0
        return book_value - recoverable_amount

    @staticmethod
    def get_net_realizable_value(
        asset: Asset,
        estimated_selling_price: float,
        selling_costs: float = 0.0,
    ) -> float:
        """Calculate net realizable value."""
        return estimated_selling_price - selling_costs

    @staticmethod
    def get_replacement_cost(
        original_cost: float,
        inflation_rate: float,
        years: int,
    ) -> float:
        """Calculate current replacement cost."""
        return original_cost * (1 + inflation_rate) ** years

    @staticmethod
    def get_depreciated_replacement_cost(
        replacement_cost: float,
        age_years: int,
        useful_life_years: int,
    ) -> float:
        """Calculate depreciated replacement cost."""
        if useful_life_years <= 0:
            return replacement_cost
        remaining_life = max(0, useful_life_years - age_years)
        return replacement_cost * remaining_life / useful_life_years

    def get_total_valuation(self, asset_ids: List[str]) -> Dict[str, float]:
        """Get total valuation for a set of assets."""
        result = {}
        for asset_id in asset_ids:
            latest = self.get_latest_valuation(asset_id)
            if latest:
                result[asset_id] = latest.market_value
        return result
