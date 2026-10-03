"""Deepened assets module: tracking, maintenance, lifecycle, valuation, reporting."""
from __future__ import annotations
import enum
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

# 1. Asset Tracking with Depreciation
class DepreciationMethod(enum.Enum):
    STRAIGHT_LINE = "straight_line"
    DECLINING_BALANCE = "declining_balance"
    SUM_OF_YEARS_DIGITS = "sum_of_years_digits"

@dataclass
class Asset:
    asset_id: str
    name: str
    category: str
    purchase_cost: float
    salvage_value: float
    useful_life_years: int
    purchase_date: date
    depreciation_method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE
    depreciation_rate: float = 2.0
    _accumulated_depreciation: float = 0.0

    def annual_depreciation(self, year: Optional[int] = None) -> float:
        if year is None: year = date.today().year
        age = year - self.purchase_date.year
        if age < 0 or age >= self.useful_life_years: return 0.0
        if self.depreciation_method == DepreciationMethod.STRAIGHT_LINE:
            return (self.purchase_cost - self.salvage_value) / self.useful_life_years
        if self.depreciation_method == DepreciationMethod.DECLINING_BALANCE:
            rate = self.depreciation_rate / self.useful_life_years
            return max(self.purchase_cost * (1 - rate) ** age * rate, 0.0)
        remaining = self.useful_life_years - age
        total_digits = self.useful_life_years * (self.useful_life_years + 1) // 2
        return (self.purchase_cost - self.salvage_value) * remaining / total_digits

    def book_value(self, as_of: Optional[date] = None) -> float:
        if as_of is None: as_of = date.today()
        years_elapsed = (as_of - self.purchase_date).days / 365.25
        if self.depreciation_method == DepreciationMethod.STRAIGHT_LINE:
            annual = (self.purchase_cost - self.salvage_value) / self.useful_life_years
            accumulated = min(annual * years_elapsed, self.purchase_cost - self.salvage_value)
        elif self.depreciation_method == DepreciationMethod.DECLINING_BALANCE:
            rate = self.depreciation_rate / self.useful_life_years
            accumulated = self.purchase_cost * (1 - (1 - rate) ** years_elapsed)
        else:
            total_digits = self.useful_life_years * (self.useful_life_years + 1) // 2
            accumulated = sum(
                (self.purchase_cost - self.salvage_value) * (self.useful_life_years - y) / total_digits
                for y in range(int(years_elapsed)))
        return max(self.purchase_cost - accumulated, self.salvage_value)

    def record_depreciation(self, amount: float) -> None:
        self._accumulated_depreciation += amount

    @property
    def accumulated_depreciation(self) -> float:
        return self._accumulated_depreciation

    def is_fully_depreciated(self) -> bool:
        return self.book_value() <= self.salvage_value

# 2. Asset Maintenance with Scheduling
class MaintenanceStatus(enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"

@dataclass
class MaintenanceRecord:
    record_id: str
    asset_id: str
    description: str
    scheduled_date: date
    completed_date: Optional[date] = None
    cost: float = 0.0
    status: MaintenanceStatus = MaintenanceStatus.SCHEDULED
    technician: str = ""

    def complete(self, completion_date: date, cost: float) -> None:
        self.completed_date, self.cost, self.status = completion_date, cost, MaintenanceStatus.COMPLETED

    def check_overdue(self) -> bool:
        if self.status == MaintenanceStatus.COMPLETED: return False
        if date.today() > self.scheduled_date:
            self.status = MaintenanceStatus.OVERDUE
            return True
        return False

@dataclass
class MaintenanceSchedule:
    schedule_id: str
    asset_id: str
    interval_days: int
    last_maintenance: Optional[date] = None
    records: list[MaintenanceRecord] = field(default_factory=list)

    def next_due_date(self) -> date:
        return date.today() if self.last_maintenance is None else self.last_maintenance + timedelta(days=self.interval_days)

    def is_due(self) -> bool:
        return date.today() >= self.next_due_date()

    def schedule_maintenance(self, description: str, technician: str = "") -> MaintenanceRecord:
        record = MaintenanceRecord(record_id=f"MNT-{len(self.records)+1:04d}", asset_id=self.asset_id,
                                   description=description, scheduled_date=self.next_due_date(), technician=technician)
        self.records.append(record)
        return record

    def complete_latest(self, completion_date: date, cost: float) -> None:
        for r in reversed(self.records):
            if r.status != MaintenanceStatus.COMPLETED:
                r.complete(completion_date, cost)
                self.last_maintenance = completion_date
                return

# 3. Asset Lifecycle (Procurement → Retirement)
class LifecycleStage(enum.Enum):
    PROCUREMENT = "procurement"
    DEPLOYMENT = "deployment"
    OPERATION = "operation"
    MAINTENANCE = "maintenance"
    RETIREMENT = "retirement"
    DISPOSED = "disposed"

@dataclass
class LifecycleEvent:
    event_id: str
    asset_id: str
    from_stage: LifecycleStage
    to_stage: LifecycleStage
    event_date: date
    notes: str = ""

@dataclass
class AssetLifecycle:
    asset_id: str
    current_stage: LifecycleStage = LifecycleStage.PROCUREMENT
    events: list[LifecycleEvent] = field(default_factory=list)
    _TRANSITIONS: dict[LifecycleStage, set[LifecycleStage]] = field(default_factory=lambda: {
        LifecycleStage.PROCUREMENT: {LifecycleStage.DEPLOYMENT, LifecycleStage.DISPOSED},
        LifecycleStage.DEPLOYMENT: {LifecycleStage.OPERATION, LifecycleStage.DISPOSED},
        LifecycleStage.OPERATION: {LifecycleStage.MAINTENANCE, LifecycleStage.RETIREMENT},
        LifecycleStage.MAINTENANCE: {LifecycleStage.OPERATION, LifecycleStage.RETIREMENT},
        LifecycleStage.RETIREMENT: {LifecycleStage.DISPOSED},
        LifecycleStage.DISPOSED: set()}, repr=False)

    def transition(self, to_stage: LifecycleStage, event_date: Optional[date] = None, notes: str = "") -> LifecycleEvent:
        if to_stage not in self._TRANSITIONS.get(self.current_stage, set()):
            raise ValueError(f"Invalid transition: {self.current_stage.value} → {to_stage.value}")
        event = LifecycleEvent(event_id=f"EVT-{len(self.events)+1:04d}", asset_id=self.asset_id,
                               from_stage=self.current_stage, to_stage=to_stage,
                               event_date=event_date or date.today(), notes=notes)
        self.events.append(event)
        self.current_stage = to_stage
        return event

    def can_transition_to(self, stage: LifecycleStage) -> bool:
        return stage in self._TRANSITIONS.get(self.current_stage, set())

    @property
    def is_active(self) -> bool:
        return self.current_stage not in (LifecycleStage.RETIREMENT, LifecycleStage.DISPOSED)

    @property
    def stage_history(self) -> list[LifecycleEvent]:
        return list(self.events)

# 4. Asset Valuation with Impairment
@dataclass
class ImpairmentRecord:
    record_id: str
    asset_id: str
    impairment_date: date
    carrying_amount: float
    recoverable_amount: float
    loss: float
    reason: str = ""

@dataclass
class AssetValuation:
    asset_id: str
    carrying_amount: float
    fair_value: float
    value_in_use: float
    impairments: list[ImpairmentRecord] = field(default_factory=list)

    @property
    def recoverable_amount(self) -> float:
        return max(self.fair_value, self.value_in_use)

    def is_impaired(self) -> bool:
        return self.carrying_amount > self.recoverable_amount

    def assess_impairment(self, as_of: Optional[date] = None, reason: str = "") -> Optional[ImpairmentRecord]:
        if not self.is_impaired(): return None
        loss = self.carrying_amount - self.recoverable_amount
        record = ImpairmentRecord(record_id=f"IMP-{len(self.impairments)+1:04d}", asset_id=self.asset_id,
                                  impairment_date=as_of or date.today(), carrying_amount=self.carrying_amount,
                                  recoverable_amount=self.recoverable_amount, loss=loss, reason=reason)
        self.impairments.append(record)
        self.carrying_amount = self.recoverable_amount
        return record

    def total_impairment_loss(self) -> float:
        return sum(r.loss for r in self.impairments)

    def net_book_value(self) -> float:
        return self.carrying_amount - self.total_impairment_loss()

# 5. Asset Reporting with Utilization
@dataclass
class UtilizationRecord:
    asset_id: str
    period_start: date
    period_end: date
    hours_used: float
    hours_available: float

    @property
    def utilization_rate(self) -> float:
        return min(self.hours_used / self.hours_available, 1.0) if self.hours_available > 0 else 0.0

@dataclass
class AssetReport:
    report_id: str
    generated_date: date = field(default_factory=date.today)
    assets: list[Asset] = field(default_factory=list)
    utilization_records: list[UtilizationRecord] = field(default_factory=list)
    valuations: list[AssetValuation] = field(default_factory=list)
    lifecycles: list[AssetLifecycle] = field(default_factory=list)

    def total_book_value(self) -> float:
        return sum(a.book_value() for a in self.assets)

    def total_accumulated_depreciation(self) -> float:
        return sum(a.accumulated_depreciation for a in self.assets)

    def average_utilization(self) -> float:
        if not self.utilization_records: return 0.0
        return sum(r.utilization_rate for r in self.utilization_records) / len(self.utilization_records)

    def assets_by_category(self) -> dict[str, list[Asset]]:
        result: dict[str, list[Asset]] = {}
        for a in self.assets: result.setdefault(a.category, []).append(a)
        return result

    def assets_by_lifecycle_stage(self) -> dict[LifecycleStage, int]:
        result: dict[LifecycleStage, int] = {}
        for lc in self.lifecycles: result[lc.current_stage] = result.get(lc.current_stage, 0) + 1
        return result

    def impaired_assets(self) -> list[AssetValuation]:
        return [v for v in self.valuations if v.is_impaired()]

    def total_impairment(self) -> float:
        return sum(v.total_impairment_loss() for v in self.valuations)

    def depreciation_schedule(self, years: int) -> list[dict]:
        schedule = []
        current_year = date.today().year
        for y in range(years):
            year = current_year + y
            row = {"year": year, "depreciation": 0.0, "book_value": 0.0}
            for a in self.assets:
                row["depreciation"] += a.annual_depreciation(year)
                row["book_value"] += a.book_value(date(year, 12, 31))
            schedule.append(row)
        return schedule

    def summary(self) -> dict:
        return {
            "report_id": self.report_id, "generated_date": self.generated_date.isoformat(),
            "total_assets": len(self.assets), "total_book_value": round(self.total_book_value(), 2),
            "total_accumulated_depreciation": round(self.total_accumulated_depreciation(), 2),
            "average_utilization": round(self.average_utilization(), 4),
            "total_impairment": round(self.total_impairment(), 2),
            "impaired_asset_count": len(self.impaired_assets()),
            "lifecycle_breakdown": {s.value: c for s, c in self.assets_by_lifecycle_stage().items()},
            "category_breakdown": {cat: len(a) for cat, a in self.assets_by_category().items()},
        }
