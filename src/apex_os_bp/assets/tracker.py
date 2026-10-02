"""Asset tracking and management."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Dict, List, Optional

from apex_os_bp.assets.models import (
    Asset,
    AssetCategory,
    AssetStatus,
    DepreciationMethod,
)


class AssetTracker:
    """Track and manage assets."""

    def __init__(self):
        self._assets: Dict[str, Asset] = {}

    def register_asset(
        self,
        name: str,
        category: AssetCategory,
        purchase_date: date,
        purchase_cost: float,
        salvage_value: float = 0.0,
        useful_life_years: int = 5,
        depreciation_method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE,
        location: str = "",
        assigned_to: str = "",
        serial_number: str = "",
        description: str = "",
        metadata: Optional[Dict] = None,
    ) -> Asset:
        """Register a new asset."""
        asset_id = str(uuid.uuid4())
        asset = Asset(
            id=asset_id,
            name=name,
            category=category,
            status=AssetStatus.ACTIVE,
            purchase_date=purchase_date,
            purchase_cost=purchase_cost,
            salvage_value=salvage_value,
            useful_life_years=useful_life_years,
            depreciation_method=depreciation_method,
            location=location,
            assigned_to=assigned_to,
            serial_number=serial_number,
            description=description,
            metadata=metadata or {},
        )
        self._assets[asset_id] = asset
        return asset

    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """Get asset by ID."""
        return self._assets.get(asset_id)

    def get_all_assets(self) -> List[Asset]:
        """Get all registered assets."""
        return list(self._assets.values())

    def get_assets_by_category(self, category: AssetCategory) -> List[Asset]:
        """Get assets filtered by category."""
        return [a for a in self._assets.values() if a.category == category]

    def get_assets_by_status(self, status: AssetStatus) -> List[Asset]:
        """Get assets filtered by status."""
        return [a for a in self._assets.values() if a.status == status]

    def get_assets_by_location(self, location: str) -> List[Asset]:
        """Get assets filtered by location."""
        return [a for a in self._assets.values() if a.location == location]

    def get_assets_by_assignee(self, assigned_to: str) -> List[Asset]:
        """Get assets filtered by assignee."""
        return [a for a in self._assets.values() if a.assigned_to == assigned_to]

    def update_asset(
        self,
        asset_id: str,
        **kwargs,
    ) -> Asset:
        """Update asset properties."""
        asset = self._assets.get(asset_id)
        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        for key, value in kwargs.items():
            if hasattr(asset, key):
                setattr(asset, key, value)

        from datetime import datetime
        asset.updated_at = datetime.now()
        return asset

    def assign_asset(self, asset_id: str, assignee: str) -> Asset:
        """Assign asset to a person."""
        return self.update_asset(asset_id, assigned_to=assignee)

    def relocate_asset(self, asset_id: str, location: str) -> Asset:
        """Move asset to a new location."""
        return self.update_asset(asset_id, location=location)

    def set_asset_status(self, asset_id: str, status: AssetStatus) -> Asset:
        """Set asset status."""
        return self.update_asset(asset_id, status=status)

    def remove_asset(self, asset_id: str) -> None:
        """Remove an asset from tracking."""
        if asset_id not in self._assets:
            raise ValueError(f"Asset not found: {asset_id}")
        del self._assets[asset_id]

    def get_total_asset_value(self) -> float:
        """Get total purchase cost of all assets."""
        return sum(a.purchase_cost for a in self._assets.values())

    def get_total_book_value(self) -> float:
        """Get total book value (purchase cost - accumulated depreciation)."""
        from apex_os_bp.assets.depreciation import DepreciationCalculator

        total = 0.0
        for asset in self._assets.values():
            if asset.status != AssetStatus.DISPOSED:
                book_value = DepreciationCalculator.get_book_value(asset, date.today())
                total += book_value
        return round(total, 2)

    def get_asset_count(self) -> int:
        """Get total number of tracked assets."""
        return len(self._assets)

    def get_asset_count_by_category(self) -> Dict[AssetCategory, int]:
        """Get asset count grouped by category."""
        result: Dict[AssetCategory, int] = {}
        for asset in self._assets.values():
            result[asset.category] = result.get(asset.category, 0) + 1
        return result

    def get_asset_count_by_status(self) -> Dict[AssetStatus, int]:
        """Get asset count grouped by status."""
        result: Dict[AssetStatus, int] = {}
        for asset in self._assets.values():
            result[asset.status] = result.get(asset.status, 0) + 1
        return result

    def search_assets(self, query: str) -> List[Asset]:
        """Search assets by name, description, or serial number."""
        query = query.lower()
        return [
            a for a in self._assets.values()
            if query in a.name.lower()
            or query in a.description.lower()
            or query in a.serial_number.lower()
        ]

    def get_depreciable_assets(self) -> List[Asset]:
        """Get all assets that are not yet fully depreciated."""
        return [
            a for a in self._assets.values()
            if a.status not in (AssetStatus.DISPOSED, AssetStatus.RETIRED)
        ]
