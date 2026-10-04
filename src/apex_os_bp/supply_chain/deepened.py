"""Deepened supply chain module: forecasting, suppliers, logistics, warehouse, procurement."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import statistics


# ── Demand Forecasting ──────────────────────────────────────────────────────

@dataclass
class DemandForecast:
    product_id: str
    horizon_days: int
    predicted_demand: list[float]
    confidence_interval: tuple[float, float]
    method: str = "moving_average"


class DemandForecaster:
    """ML-style demand forecasting using exponential smoothing + seasonality."""

    def __init__(self, alpha: float = 0.3, seasonality_period: int = 7):
        self.alpha = alpha
        self.seasonality_period = seasonality_period

    def forecast(self, product_id: str, history: list[float], horizon: int = 30) -> DemandForecast:
        if not history:
            return DemandForecast(product_id, horizon, [0.0] * horizon, (0.0, 0.0))
        smoothed = self._exponential_smoothing(history)
        seasonal = self._seasonal_factors(history)
        predictions = []
        for h in range(horizon):
            base = smoothed[-1]
            factor = seasonal[h % self.seasonality_period] if seasonal else 1.0
            predictions.append(max(0.0, base * factor))
        stdev = statistics.stdev(history) if len(history) > 1 else 0.0
        ci = (max(0.0, predictions[-1] - 1.96 * stdev), predictions[-1] + 1.96 * stdev)
        return DemandForecast(product_id, horizon, predictions, ci)

    def _exponential_smoothing(self, data: list[float]) -> list[float]:
        result = [data[0]]
        for val in data[1:]:
            result.append(self.alpha * val + (1 - self.alpha) * result[-1])
        return result

    def _seasonal_factors(self, data: list[float]) -> list[float]:
        if len(data) < self.seasonality_period * 2:
            return [1.0] * self.seasonality_period
        avg = statistics.mean(data)
        buckets: list[list[float]] = [[] for _ in range(self.seasonality_period)]
        for i, v in enumerate(data):
            buckets[i % self.seasonality_period].append(v)
        return [statistics.mean(b) / avg if avg else 1.0 for b in buckets]


# ── Supplier Management ─────────────────────────────────────────────────────

class SupplierRating(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"


@dataclass
class Supplier:
    supplier_id: str
    name: str
    lead_time_days: int
    quality_score: float  # 0-100
    cost_score: float  # 0-100 (higher = more cost-effective)
    reliability_score: float  # 0-100
    active: bool = True

    @property
    def composite_score(self) -> float:
        return round(0.4 * self.quality_score + 0.3 * self.cost_score + 0.3 * self.reliability_score, 2)

    @property
    def rating(self) -> SupplierRating:
        s = self.composite_score
        if s >= 85:
            return SupplierRating.EXCELLENT
        if s >= 70:
            return SupplierRating.GOOD
        if s >= 50:
            return SupplierRating.AVERAGE
        return SupplierRating.POOR


class SupplierManager:
    def __init__(self):
        self._suppliers: dict[str, Supplier] = {}

    def add_supplier(self, supplier: Supplier) -> None:
        self._suppliers[supplier.supplier_id] = supplier

    def get_supplier(self, sid: str) -> Supplier | None:
        return self._suppliers.get(sid)

    def rank_suppliers(self) -> list[Supplier]:
        return sorted(self._suppliers.values(), key=lambda s: s.composite_score, reverse=True)

    def best_supplier(self, min_rating: SupplierRating = SupplierRating.GOOD) -> Supplier | None:
        for s in self.rank_suppliers():
            if s.rating.value in (SupplierRating.EXCELLENT.value, SupplierRating.GOOD.value):
                return s
        return None


# ── Logistics Optimization ──────────────────────────────────────────────────

@dataclass
class RouteStop:
    location: str
    demand: float
    time_window: tuple[int, int]  # (earliest, latest) in minutes from start


@dataclass
class Route:
    stops: list[RouteStop]
    total_distance: float
    total_time: float
    vehicle_id: str


class LogisticsOptimizer:
    """Greedy nearest-neighbor routing with capacity constraints."""

    def __init__(self, depot: str = "depot", vehicle_capacity: float = 1000.0, speed_kmh: float = 50.0):
        self.depot = depot
        self.vehicle_capacity = vehicle_capacity
        self.speed_kmh = speed_kmh

    def optimize_routes(self, stops: list[RouteStop], num_vehicles: int = 1) -> list[Route]:
        if not stops:
            return []
        unassigned = list(stops)
        routes: list[Route] = []
        for v in range(num_vehicles):
            if not unassigned:
                break
            route_stops, total_dist = self._build_route(unassigned)
            unassigned = [s for s in unassigned if s not in route_stops]
            total_time = (total_dist / self.speed_kmh) * 60
            routes.append(Route(route_stops, total_dist, total_time, f"V{v+1}"))
        if unassigned:
            route_stops, total_dist = self._build_route(unassigned)
            routes.append(Route(route_stops, total_dist, (total_dist / self.speed_kmh) * 60, f"V{len(routes)+1}"))
        return routes

    def _build_route(self, stops: list[RouteStop]) -> tuple[list[RouteStop], float]:
        remaining = list(stops)
        route: list[RouteStop] = []
        current = self.depot
        total_dist = 0.0
        while remaining:
            nearest = min(remaining, key=lambda s: self._distance(current, s.location))
            if sum(s.demand for s in route) + nearest.demand > self.vehicle_capacity:
                break
            total_dist += self._distance(current, nearest.location)
            route.append(nearest)
            current = nearest.location
            remaining.remove(nearest)
        total_dist += self._distance(current, self.depot)
        return route, total_dist

    @staticmethod
    def _distance(a: str, b: str) -> float:
        return abs(hash(a) - hash(b)) % 100 + 1.0


# ── Warehouse Management ────────────────────────────────────────────────────

@dataclass
class Bin:
    bin_id: str
    zone: str
    aisle: int
    shelf: int
    capacity: float
    occupied: float = 0.0
    sku: str | None = None

    @property
    def available(self) -> float:
        return self.capacity - self.occupied

    @property
    def utilization_pct(self) -> float:
        return round((self.occupied / self.capacity) * 100, 1) if self.capacity else 0.0


class WarehouseManager:
    def __init__(self):
        self._bins: dict[str, Bin] = {}

    def add_bin(self, bin_obj: Bin) -> None:
        self._bins[bin_obj.bin_id] = bin_obj

    def find_bin(self, sku: str, quantity: float) -> Bin | None:
        for b in self._bins.values():
            if b.sku == sku and b.available >= quantity:
                return b
        for b in self._bins.values():
            if b.sku is None and b.available >= quantity:
                return b
        return None

    def store(self, sku: str, quantity: float) -> str | None:
        bin_obj = self.find_bin(sku, quantity)
        if bin_obj is None:
            return None
        bin_obj.sku = sku
        bin_obj.occupied += quantity
        return bin_obj.bin_id

    def retrieve(self, sku: str, quantity: float) -> float:
        remaining = quantity
        for b in self._bins.values():
            if b.sku == sku and remaining > 0:
                take = min(b.occupied, remaining)
                b.occupied -= take
                remaining -= take
                if b.occupied == 0:
                    b.sku = None
        return quantity - remaining

    def utilization_report(self) -> dict[str, float]:
        if not self._bins:
            return {}
        total_cap = sum(b.capacity for b in self._bins.values())
        total_occ = sum(b.occupied for b in self._bins.values())
        return {
            "total_bins": len(self._bins),
            "total_capacity": total_cap,
            "total_occupied": total_occ,
            "overall_utilization_pct": round((total_occ / total_cap) * 100, 1) if total_cap else 0.0,
        }


# ── Procurement & Approval Workflows ────────────────────────────────────────

class ApprovalStatus(Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class PurchaseOrder:
    po_id: str
    supplier_id: str
    items: dict[str, float]  # sku -> quantity
    total_cost: float
    status: ApprovalStatus = ApprovalStatus.DRAFT
    approver: str | None = None
    created_at: datetime = field(default_factory=datetime.now)


class ProcurementWorkflow:
    def __init__(self, approval_threshold: float = 10000.0):
        self.approval_threshold = approval_threshold
        self._pos: dict[str, PurchaseOrder] = {}

    def create_po(
        self,
        po_id: str,
        supplier_id: str,
        items: dict[str, float],
        unit_costs: dict[str, float]
    ) -> PurchaseOrder:
        total = sum(items[sku] * unit_costs.get(sku, 0) for sku in items)
        po = PurchaseOrder(po_id, supplier_id, items, total)
        self._pos[po_id] = po
        return po

    def submit_for_approval(self, po_id: str) -> bool:
        po = self._pos.get(po_id)
        if po and po.status == ApprovalStatus.DRAFT:
            po.status = ApprovalStatus.PENDING
            return True
        return False

    def approve(self, po_id: str, approver: str) -> bool:
        po = self._pos.get(po_id)
        if po and po.status == ApprovalStatus.PENDING:
            po.status = ApprovalStatus.APPROVED
            po.approver = approver
            return True
        return False

    def reject(self, po_id: str, approver: str) -> bool:
        po = self._pos.get(po_id)
        if po and po.status == ApprovalStatus.PENDING:
            po.status = ApprovalStatus.REJECTED
            po.approver = approver
            return True
        return False

    def auto_approve(self, po_id: str) -> bool:
        po = self._pos.get(po_id)
        if po and po.status == ApprovalStatus.PENDING and po.total_cost < self.approval_threshold:
            return self.approve(po_id, "system_auto")
        return False

    def pending_pos(self) -> list[PurchaseOrder]:
        return [po for po in self._pos.values() if po.status == ApprovalStatus.PENDING]
