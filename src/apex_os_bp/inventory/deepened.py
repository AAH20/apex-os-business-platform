"""Deepened Inventory Module for APEX-OS Business Platform.

Features: stock management with reorder points, warehouse management with
bin tracking, serial number tracking with genealogy, cycle counting with
variance, and inventory valuation with FIFO/LIFO.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

# 1. Stock Management with Reorder Points


class StockStatus(Enum):
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    OVERSTOCK = "overstock"


@dataclass
class StockItem:
    sku: str
    name: str
    quantity: int = 0
    reorder_point: int = 0
    reorder_quantity: int = 0
    max_stock: int = 0
    unit_cost: Decimal = Decimal("0.00")
    location_id: Optional[str] = None

    @property
    def status(self) -> StockStatus:
        if self.quantity <= 0:
            return StockStatus.OUT_OF_STOCK
        if self.quantity <= self.reorder_point:
            return StockStatus.LOW_STOCK
        if self.max_stock > 0 and self.quantity > self.max_stock:
            return StockStatus.OVERSTOCK
        return StockStatus.IN_STOCK

    @property
    def needs_reorder(self) -> bool:
        return self.quantity <= self.reorder_point

    @property
    def stock_value(self) -> Decimal:
        return self.unit_cost * self.quantity


class StockManager:
    def __init__(self):
        self._items: dict[str, StockItem] = {}

    def add_item(self, item: StockItem) -> None:
        self._items[item.sku] = item

    def get_item(self, sku: str) -> Optional[StockItem]:
        return self._items.get(sku)

    def adjust_stock(self, sku: str, delta: int) -> StockItem:
        item = self._items[sku]
        item.quantity += delta
        return item

    def get_reorder_alerts(self) -> list[StockItem]:
        return [i for i in self._items.values() if i.needs_reorder]

    def get_low_stock(self) -> list[StockItem]:
        return [i for i in self._items.values() if i.status == StockStatus.LOW_STOCK]

# 2. Warehouse Management with Bin Tracking


@dataclass
class Bin:
    bin_id: str
    warehouse_id: str
    zone: str
    aisle: str
    rack: str
    shelf: str
    capacity: int = 0

    @property
    def full_id(self) -> str:
        return f"{self.warehouse_id}-{self.zone}-{self.aisle}-{self.rack}-{self.shelf}"


@dataclass
class Warehouse:
    warehouse_id: str
    name: str
    address: str = ""
    bins: dict[str, Bin] = field(default_factory=dict)
    stock: dict[str, int] = field(default_factory=dict)

    def add_bin(self, bin: Bin) -> None:
        self.bins[bin.bin_id] = bin

    def remove_bin(self, bin_id: str) -> None:
        self.bins.pop(bin_id, None)

    def assign_stock(self, sku: str, bin_id: str, quantity: int) -> None:
        if bin_id not in self.bins:
            raise ValueError(f"Bin {bin_id} not found")
        self.stock[sku] = self.stock.get(sku, 0) + quantity

    def get_bin_for_sku(self, sku: str) -> list[str]:
        return [b for b in self.bins if sku in self.stock]


class WarehouseManager:
    def __init__(self):
        self._warehouses: dict[str, Warehouse] = {}

    def add_warehouse(self, wh: Warehouse) -> None:
        self._warehouses[wh.warehouse_id] = wh

    def get_warehouse(self, wh_id: str) -> Optional[Warehouse]:
        return self._warehouses.get(wh_id)

    def find_stock(self, sku: str) -> list[tuple[str, int]]:
        return [(w.warehouse_id, w.stock[sku]) for w in self._warehouses.values() if sku in w.stock]

# 3. Serial Number Tracking with Genealogy


@dataclass
class SerialRecord:
    serial_number: str
    sku: str
    status: str = "active"
    parent_serials: list[str] = field(default_factory=list)
    child_serials: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    def add_parent(self, parent_sn: str) -> None:
        if parent_sn not in self.parent_serials:
            self.parent_serials.append(parent_sn)

    def add_child(self, child_sn: str) -> None:
        if child_sn not in self.child_serials:
            self.child_serials.append(child_sn)


class SerialTracker:
    def __init__(self):
        self._serials: dict[str, SerialRecord] = {}

    def register(self, record: SerialRecord) -> None:
        self._serials[record.serial_number] = record

    def get(self, serial_number: str) -> Optional[SerialRecord]:
        return self._serials.get(serial_number)

    def link_parent_child(self, parent_sn: str, child_sn: str) -> None:
        parent = self._serials.get(parent_sn)
        child = self._serials.get(child_sn)
        if parent and child:
            parent.add_child(child_sn)
            child.add_parent(parent_sn)

    def get_ancestors(self, serial_number: str) -> list[str]:
        record = self._serials.get(serial_number)
        if not record:
            return []
        result, queue, visited = [], list(record.parent_serials), set()
        while queue:
            sn = queue.pop(0)
            if sn in visited:
                continue
            visited.add(sn)
            result.append(sn)
            parent = self._serials.get(sn)
            if parent:
                queue.extend(parent.parent_serials)
        return result

    def get_descendants(self, serial_number: str) -> list[str]:
        record = self._serials.get(serial_number)
        if not record:
            return []
        result, queue, visited = [], list(record.child_serials), set()
        while queue:
            sn = queue.pop(0)
            if sn in visited:
                continue
            visited.add(sn)
            result.append(sn)
            child = self._serials.get(sn)
            if child:
                queue.extend(child.child_serials)
        return result

# 4. Cycle Counting with Variance


class CountStatus(Enum):
    PENDING = "pending"
    COUNTED = "counted"
    ADJUSTED = "adjusted"
    APPROVED = "approved"


@dataclass
class CycleCount:
    count_id: str
    sku: str
    bin_id: str
    expected_qty: int
    counted_qty: int = 0
    status: CountStatus = CountStatus.PENDING
    counted_by: str = ""
    counted_at: Optional[datetime] = None
    notes: str = ""

    @property
    def variance(self) -> int:
        return self.counted_qty - self.expected_qty

    @property
    def variance_pct(self) -> float:
        if self.expected_qty == 0:
            return 0.0
        return (self.variance / self.expected_qty) * 100


class CycleCountManager:
    def __init__(self):
        self._counts: dict[str, CycleCount] = {}

    def schedule(self, sku: str, bin_id: str, expected_qty: int) -> CycleCount:
        cc = CycleCount(count_id=str(uuid.uuid4())[:8], sku=sku, bin_id=bin_id, expected_qty=expected_qty)
        self._counts[cc.count_id] = cc
        return cc

    def record_count(self, count_id: str, counted_qty: int, counted_by: str) -> CycleCount:
        cc = self._counts[count_id]
        cc.counted_qty = counted_qty
        cc.counted_by = counted_by
        cc.counted_at = datetime.now()
        cc.status = CountStatus.COUNTED
        return cc

    def get_variances(self, threshold_pct: float = 5.0) -> list[CycleCount]:
        return [c for c in self._counts.values() if abs(c.variance_pct) > threshold_pct]

    def approve(self, count_id: str) -> CycleCount:
        cc = self._counts[count_id]
        cc.status = CountStatus.APPROVED
        return cc

# 5. Inventory Valuation with FIFO/LIFO


class ValuationMethod(Enum):
    FIFO = "fifo"
    LIFO = "lifo"


@dataclass
class StockLayer:
    layer_id: str
    sku: str
    quantity: int
    unit_cost: Decimal
    received_at: datetime = field(default_factory=datetime.now)

    @property
    def total_cost(self) -> Decimal:
        return self.unit_cost * self.quantity


class InventoryValuator:
    def __init__(self):
        self._layers: dict[str, list[StockLayer]] = {}

    def add_layer(self, layer: StockLayer) -> None:
        self._layers.setdefault(layer.sku, []).append(layer)

    def consume(self, sku: str, quantity: int, method: ValuationMethod = ValuationMethod.FIFO) -> Decimal:
        layers = self._layers.get(sku, [])
        layers.sort(key=lambda l: l.received_at, reverse=(method == ValuationMethod.LIFO))
        remaining, total_cost = quantity, Decimal("0.00")
        for layer in layers:
            if remaining <= 0:
                break
            take = min(remaining, layer.quantity)
            total_cost += layer.unit_cost * take
            layer.quantity -= take
            remaining -= take
        self._layers[sku] = [l for l in layers if l.quantity > 0]
        return total_cost

    def get_inventory_value(self, sku: str, method: ValuationMethod = ValuationMethod.FIFO) -> Decimal:
        return sum(l.total_cost for l in self._layers.get(sku, []))

    def get_total_value(self, method: ValuationMethod = ValuationMethod.FIFO) -> Decimal:
        return sum(self.get_inventory_value(sku, method) for sku in self._layers)
