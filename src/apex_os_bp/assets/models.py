"""Asset management data models."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional


class AssetCategory(Enum):
    """Asset categories."""
    VEHICLE = "vehicle"
    MACHINERY = "machinery"
    FURNITURE = "furniture"
    ELECTRONICS = "electronics"
    BUILDING = "building"
    LAND = "land"
    SOFTWARE = "software"
    OTHER = "other"


class AssetStatus(Enum):
    """Asset lifecycle status."""
    ACTIVE = "active"
    IN_MAINTENANCE = "in_maintenance"
    IDLE = "idle"
    DISPOSED = "disposed"
    RETIRED = "retired"


class DepreciationMethod(Enum):
    """Depreciation calculation methods."""
    STRAIGHT_LINE = "straight_line"
    DECLINING_BALANCE = "declining_balance"
    SUM_OF_YEARS_DIGITS = "sum_of_years_digits"
    UNITS_OF_PRODUCTION = "units_of_production"


class MaintenanceType(Enum):
    """Types of maintenance."""
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"
    PREDICTIVE = "predictive"
    INSPECTION = "inspection"


class MaintenanceStatus(Enum):
    """Maintenance task status."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class DisposalMethod(Enum):
    """Asset disposal methods."""
    SALE = "sale"
    TRADE_IN = "trade_in"
    DONATION = "donation"
    SCRAP = "scrap"
    RECYCLING = "recycling"


@dataclass
class Asset:
    """Core asset data structure."""
    id: str
    name: str
    category: AssetCategory
    status: AssetStatus
    purchase_date: date
    purchase_cost: float
    salvage_value: float
    useful_life_years: int
    depreciation_method: DepreciationMethod
    location: str = ""
    assigned_to: str = ""
    serial_number: str = ""
    description: str = ""
    metadata: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.purchase_cost < 0:
            raise ValueError("Purchase cost cannot be negative")
        if self.salvage_value < 0:
            raise ValueError("Salvage value cannot be negative")
        if self.useful_life_years <= 0:
            raise ValueError("Useful life must be positive")
        if self.salvage_value > self.purchase_cost:
            raise ValueError("Salvage value cannot exceed purchase cost")


@dataclass
class DepreciationRecord:
    """Single depreciation period record."""
    id: str
    asset_id: str
    period_start: date
    period_end: date
    depreciation_amount: float
    accumulated_depreciation: float
    book_value: float
    method: DepreciationMethod


@dataclass
class MaintenanceRecord:
    """Maintenance task record."""
    id: str
    asset_id: str
    maintenance_type: MaintenanceType
    status: MaintenanceStatus
    scheduled_date: date
    completed_date: Optional[date] = None
    cost: float = 0.0
    description: str = ""
    technician: str = ""
    notes: str = ""
    next_scheduled_date: Optional[date] = None


@dataclass
class ValuationRecord:
    """Asset valuation snapshot."""
    id: str
    asset_id: str
    valuation_date: date
    market_value: float
    book_value: float
    valuation_method: str
    appraiser: str = ""
    notes: str = ""


@dataclass
class DisposalRecord:
    """Asset disposal record."""
    id: str
    asset_id: str
    disposal_method: DisposalMethod
    disposal_date: date
    proceeds: float
    book_value_at_disposal: float
    gain_loss: float
    buyer: str = ""
    reason: str = ""
    approved_by: str = ""
