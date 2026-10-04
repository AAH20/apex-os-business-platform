"""Deepened manufacturing module: MRP, SPC quality, predictive maintenance,
versioned BOM, and real-time shop floor control."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


# ── 1. Bill of Materials with Versioning ──────────────────────────────────

class BOMStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    OBSOLETE = "obsolete"


@dataclass
class BOMComponent:
    item_id: str
    quantity: float
    scrap_factor: float = 0.0


@dataclass
class BOMVersion:
    version: int
    components: list[BOMComponent]
    status: BOMStatus
    effective_from: datetime
    effective_to: Optional[datetime] = None


class BillOfMaterials:
    def __init__(self, product_id: str):
        self.product_id = product_id
        self._versions: list[BOMVersion] = []

    def add_version(self, components: list[BOMComponent]) -> BOMVersion:
        v = len(self._versions) + 1
        if self._versions:
            self._versions[-1].status = BOMStatus.OBSOLETE
            self._versions[-1].effective_to = datetime.now()
        bv = BOMVersion(v, components, BOMStatus.ACTIVE, datetime.now())
        self._versions.append(bv)
        return bv

    def explode(self, quantity: float, version: Optional[int] = None) -> dict[str, float]:
        bv = next((b for b in self._versions if b.version == version), self._versions[-1])
        return {c.item_id: quantity * c.quantity * (1 + c.scrap_factor) for c in bv.components}


# ── 2. Production Planning with MRP ───────────────────────────────────────

@dataclass
class InventoryRecord:
    item_id: str
    on_hand: float
    allocated: float = 0.0
    safety_stock: float = 0.0

    @property
    def available(self) -> float:
        return self.on_hand - self.allocated


@dataclass
class MRPRequirement:
    item_id: str
    gross: float
    net: float
    due_date: datetime
    source: str


class MRPPlanner:
    def __init__(self):
        self.inventory: dict[str, InventoryRecord] = {}
        self.boms: dict[str, BillOfMaterials] = {}
        self.lead_times: dict[str, int] = {}  # days

    def register_bom(self, product_id: str, bom: BillOfMaterials) -> None:
        self.boms[product_id] = bom

    def plan(self, demands: list[tuple[str, float, datetime]]) -> list[MRPRequirement]:
        reqs: list[MRPRequirement] = []
        for item_id, qty, due in demands:
            inv = self.inventory.get(item_id, InventoryRecord(item_id, 0))
            net = max(0.0, qty - inv.available + inv.safety_stock)
            if net > 0:
                lt = self.lead_times.get(item_id, 7)
                reqs.append(MRPRequirement(item_id, qty, net, due - timedelta(days=lt), "MRP"))
            if item_id in self.boms:
                for comp_id, comp_qty in self.boms[item_id].explode(net).items():
                    reqs.append(MRPRequirement(comp_id, comp_qty, comp_qty, due, f"BOM:{item_id}"))
        return reqs


# ── 3. Quality Control with SPC ───────────────────────────────────────────

@dataclass
class SPCMeasurement:
    timestamp: datetime
    value: float
    sample_size: int = 1


class SPCControl:
    def __init__(self, lsl: float, usl: float, target: float):
        self.lsl, self.usl, self.target = lsl, usl, target
        self.measurements: list[SPCMeasurement] = []

    def add(self, value: float, n: int = 1) -> None:
        self.measurements.append(SPCMeasurement(datetime.now(), value, n))

    @property
    def mean(self) -> float:
        return sum(m.value for m in self.measurements) / len(self.measurements) if self.measurements else 0.0

    @property
    def std_dev(self) -> float:
        if len(self.measurements) < 2:
            return 0.0
        m = self.mean
        return (sum((x.value - m) ** 2 for x in self.measurements) / (len(self.measurements) - 1)) ** 0.5

    def cpk(self) -> float:
        sigma = self.std_dev
        if sigma == 0:
            return float("inf")
        cpu = (self.usl - self.mean) / (3 * sigma)
        cpl = (self.mean - self.lsl) / (3 * sigma)
        return min(cpu, cpl)

    def is_in_control(self) -> bool:
        return all(self.lsl <= m.value <= self.usl for m in self.measurements[-20:])


# ── 4. Maintenance Scheduling with Predictive ──────────────────────────────

class MaintenanceType(Enum):
    PREVENTIVE = "preventive"
    PREDICTIVE = "predictive"
    CORRECTIVE = "corrective"


@dataclass
class Equipment:
    equipment_id: str
    name: str
    health_score: float = 100.0
    last_maintenance: Optional[datetime] = None
    failure_probability: float = 0.0


class MaintenanceScheduler:
    def __init__(self):
        self.equipment: dict[str, Equipment] = {}
        self.schedule: list[tuple[str, MaintenanceType, datetime]] = []

    def register(self, eq: Equipment) -> None:
        self.equipment[eq.equipment_id] = eq

    def predict_failure(self, eq_id: str, sensor_trend: list[float]) -> float:
        eq = self.equipment[eq_id]
        if len(sensor_trend) < 2:
            return eq.failure_probability
        slope = (sensor_trend[-1] - sensor_trend[0]) / len(sensor_trend)
        eq.failure_probability = min(1.0, max(0.0, 0.5 + slope * 0.1))
        eq.health_score = max(0.0, 100.0 - eq.failure_probability * 100)
        return eq.failure_probability

    def schedule_maintenance(self, horizon_days: int = 30) -> list[tuple[str, MaintenanceType, datetime]]:
        now = datetime.now()
        self.schedule.clear()
        for eq in self.equipment.values():
            if eq.failure_probability > 0.7:
                self.schedule.append((eq.equipment_id, MaintenanceType.PREDICTIVE, now + timedelta(days=1)))
            elif eq.health_score < 50:
                self.schedule.append((eq.equipment_id, MaintenanceType.PREVENTIVE, now + timedelta(days=7)))
        return self.schedule


# ── 5. Shop Floor Control with Real-Time Monitoring ───────────────────────

class WorkOrderStatus(Enum):
    CREATED = "created"
    RELEASED = "released"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SCRAPPED = "scrapped"


@dataclass
class WorkOrder:
    wo_id: str
    product_id: str
    quantity: float
    status: WorkOrderStatus
    progress: float = 0.0


class ShopFloorController:
    def __init__(self):
        self.work_orders: dict[str, WorkOrder] = {}
        self.oee: float = 0.0
        self._downtime_events: list[tuple[datetime, float]] = []

    def create_wo(self, wo_id: str, product_id: str, qty: float) -> WorkOrder:
        wo = WorkOrder(wo_id, product_id, qty, WorkOrderStatus.CREATED)
        self.work_orders[wo_id] = wo
        return wo

    def start(self, wo_id: str) -> None:
        self.work_orders[wo_id].status = WorkOrderStatus.IN_PROGRESS

    def update_progress(self, wo_id: str, pct: float) -> None:
        wo = self.work_orders[wo_id]
        wo.progress = min(100.0, max(0.0, pct))
        if wo.progress >= 100:
            wo.status = WorkOrderStatus.COMPLETED

    def record_downtime(self, minutes: float) -> None:
        self._downtime_events.append((datetime.now(), minutes))

    def compute_oee(self, availability: float, performance: float, quality: float) -> float:
        self.oee = availability * performance * quality
        return self.oee

    def real_time_snapshot(self) -> dict:
        active = [wo for wo in self.work_orders.values() if wo.status == WorkOrderStatus.IN_PROGRESS]
        return {
            "active_orders": len(active),
            "oee": self.oee,
            "total_downtime_min": sum(d for _, d in self._downtime_events),
            "orders": {
                wid: {"status": wo.status.value, "progress": wo.progress}
                for wid, wo in self.work_orders.items()
            },
        }
