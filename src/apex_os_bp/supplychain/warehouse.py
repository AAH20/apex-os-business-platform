"""Warehouse management module.

Handles warehouse zones, inventory items, and stock movements
for tracking goods throughout the storage lifecycle.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class StockMovementType(str, Enum):
    """Type of stock movement."""

    RECEIPT = "receipt"
    ISSUE = "issue"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    RETURN = "return"
    DISPOSAL = "disposal"


@dataclass
class WarehouseZone:
    """A zone within a warehouse.

    Attributes:
        name: Zone name (e.g., "Receiving", "Storage", "Shipping").
        code: Short zone code.
        capacity: Maximum capacity in cubic meters.
        temperature_controlled: Whether the zone is temperature controlled.
        temperature_range: (min, max) temperature in Celsius.
        is_active: Whether the zone is active.
        id: Unique identifier.
    """

    name: str
    code: str = ""
    capacity: float = 0.0
    temperature_controlled: bool = False
    temperature_range: tuple[float, float] = (0.0, 0.0)
    is_active: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Zone name cannot be empty")
        if self.capacity < 0:
            raise ValueError("Zone capacity cannot be negative")

    @property
    def volume_m3(self) -> float:
        """Alias for capacity."""
        return self.capacity

    def to_dict(self) -> dict:
        """Serialize zone to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "capacity": self.capacity,
            "temperature_controlled": self.temperature_controlled,
            "temperature_range": list(self.temperature_range),
            "is_active": self.is_active,
        }


@dataclass
class InventoryItem:
    """An item stored in the warehouse.

    Attributes:
        product_sku: Product stock-keeping unit.
        product_name: Human-readable product name.
        quantity: Current quantity in stock.
        unit_cost: Cost per unit.
        zone_id: ID of the zone where the item is stored.
        reorder_point: Quantity threshold for reorder alert.
        reorder_quantity: Suggested reorder quantity.
        max_stock: Maximum stock level.
        lot_number: Lot/batch number.
        expiry_date: Expiry date if applicable.
        notes: Free-form notes.
        id: Unique identifier.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    product_sku: str
    product_name: str
    quantity: int = 0
    unit_cost: float = 0.0
    zone_id: str = ""
    reorder_point: int = 0
    reorder_quantity: int = 0
    max_stock: int = 0
    lot_number: str = ""
    expiry_date: Optional[str] = None
    notes: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.product_sku:
            raise ValueError("Product SKU cannot be empty")
        if self.quantity < 0:
            raise ValueError("Quantity cannot be negative")
        if self.unit_cost < 0:
            raise ValueError("Unit cost cannot be negative")
        if self.reorder_point < 0:
            raise ValueError("Reorder point cannot be negative")
        if self.reorder_quantity < 0:
            raise ValueError("Reorder quantity cannot be negative")
        if self.max_stock < 0:
            raise ValueError("Max stock cannot be negative")

    @property
    def total_value(self) -> float:
        """Total value of this inventory item."""
        return self.quantity * self.unit_cost

    @property
    def needs_reorder(self) -> bool:
        """Whether the item quantity is at or below the reorder point."""
        return self.quantity <= self.reorder_point

    @property
    def is_overstocked(self) -> bool:
        """Whether the item quantity exceeds the max stock level."""
        return self.max_stock > 0 and self.quantity > self.max_stock

    @property
    def is_expired(self) -> bool:
        """Whether the item has expired."""
        if not self.expiry_date:
            return False
        try:
            from datetime import date

            exp = date.fromisoformat(self.expiry_date)
            return exp < date.today()
        except (ValueError, TypeError):
            return False

    def add_stock(self, qty: int, unit_cost: Optional[float] = None) -> None:
        """Add stock to the item."""
        if qty <= 0:
            raise ValueError("Quantity to add must be positive")
        self.quantity += qty
        if unit_cost is not None and unit_cost >= 0:
            self.unit_cost = unit_cost
        self.updated_at = datetime.utcnow()

    def remove_stock(self, qty: int) -> None:
        """Remove stock from the item."""
        if qty <= 0:
            raise ValueError("Quantity to remove must be positive")
        if qty > self.quantity:
            raise ValueError("Cannot remove more than available quantity")
        self.quantity -= qty
        self.updated_at = datetime.utcnow()

    def adjust_stock(self, new_quantity: int, reason: str = "") -> None:
        """Adjust stock to a new quantity."""
        if new_quantity < 0:
            raise ValueError("Quantity cannot be negative")
        self.quantity = new_quantity
        if reason:
            self.notes = f"{self.notes}\nAdjustment: {reason}".strip()
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Serialize inventory item to dictionary."""
        return {
            "id": self.id,
            "product_sku": self.product_sku,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_cost": self.unit_cost,
            "total_value": self.total_value,
            "zone_id": self.zone_id,
            "reorder_point": self.reorder_point,
            "reorder_quantity": self.reorder_quantity,
            "max_stock": self.max_stock,
            "lot_number": self.lot_number,
            "expiry_date": self.expiry_date,
            "needs_reorder": self.needs_reorder,
            "is_overstocked": self.is_overstocked,
            "is_expired": self.is_expired,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class StockMovement:
    """A record of a stock movement.

    Attributes:
        item_id: ID of the inventory item.
        movement_type: Type of movement.
        quantity: Quantity moved.
        from_zone_id: Source zone (for transfers).
        to_zone_id: Destination zone (for transfers).
        reference: Reference document (PO number, etc.).
        notes: Free-form notes.
        id: Unique identifier.
        created_at: Creation timestamp.
    """

    item_id: str
    movement_type: StockMovementType
    quantity: int
    from_zone_id: str = ""
    to_zone_id: str = ""
    reference: str = ""
    notes: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.item_id:
            raise ValueError("Item ID cannot be empty")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")

    def to_dict(self) -> dict:
        """Serialize stock movement to dictionary."""
        return {
            "id": self.id,
            "item_id": self.item_id,
            "movement_type": self.movement_type.value,
            "quantity": self.quantity,
            "from_zone_id": self.from_zone_id,
            "to_zone_id": self.to_zone_id,
            "reference": self.reference,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Warehouse:
    """Represents a warehouse.

    Attributes:
        name: Warehouse name.
        code: Short warehouse code.
        address: Physical address.
        country_code: ISO 3166-1 alpha-2 country code.
        zones: Zones within the warehouse.
        is_active: Whether the warehouse is active.
        id: Unique identifier.
        created_at: Creation timestamp.
    """

    name: str
    code: str = ""
    address: str = ""
    country_code: str = ""
    zones: list[WarehouseZone] = field(default_factory=list)
    is_active: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Warehouse name cannot be empty")

    @property
    def total_capacity(self) -> float:
        """Total capacity across all zones."""
        return sum(z.capacity for z in self.zones)

    @property
    def zone_count(self) -> int:
        """Number of zones in the warehouse."""
        return len(self.zones)

    def add_zone(self, zone: WarehouseZone) -> None:
        """Add a zone to the warehouse."""
        self.zones.append(zone)

    def remove_zone(self, zone_id: str) -> bool:
        """Remove a zone by ID. Returns True if removed."""
        for i, zone in enumerate(self.zones):
            if zone.id == zone_id:
                self.zones.pop(i)
                return True
        return False

    def get_zone(self, zone_id: str) -> Optional[WarehouseZone]:
        """Get a zone by ID."""
        for zone in self.zones:
            if zone.id == zone_id:
                return zone
        return None

    def to_dict(self) -> dict:
        """Serialize warehouse to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "address": self.address,
            "country_code": self.country_code,
            "is_active": self.is_active,
            "total_capacity": self.total_capacity,
            "zone_count": self.zone_count,
            "zones": [z.to_dict() for z in self.zones],
            "created_at": self.created_at.isoformat(),
        }


class WarehouseManager:
    """Manages warehouses, inventory, and stock movements."""

    def __init__(self) -> None:
        self._warehouses: dict[str, Warehouse] = {}
        self._inventory: dict[str, InventoryItem] = {}
        self._movements: dict[str, StockMovement] = {}

    # ── Warehouse management ────────────────────────────────────────

    def add_warehouse(self, warehouse: Warehouse) -> Warehouse:
        """Register a new warehouse."""
        if warehouse.id in self._warehouses:
            raise ValueError(f"Warehouse with id {warehouse.id} already exists")
        self._warehouses[warehouse.id] = warehouse
        return warehouse

    def get_warehouse(self, warehouse_id: str) -> Optional[Warehouse]:
        """Retrieve a warehouse by ID."""
        return self._warehouses.get(warehouse_id)

    def remove_warehouse(self, warehouse_id: str) -> bool:
        """Remove a warehouse by ID. Returns True if removed."""
        if warehouse_id in self._warehouses:
            del self._warehouses[warehouse_id]
            return True
        return False

    def list_warehouses(self, active_only: bool = False) -> list[Warehouse]:
        """List warehouses, optionally filtering to active only."""
        warehouses = list(self._warehouses.values())
        if active_only:
            warehouses = [w for w in warehouses if w.is_active]
        return warehouses

    # ── Inventory management ───────────────────────────────────────

    def add_inventory_item(self, item: InventoryItem) -> InventoryItem:
        """Add an inventory item."""
        if item.id in self._inventory:
            raise ValueError(f"Inventory item with id {item.id} already exists")
        self._inventory[item.id] = item
        return item

    def get_inventory_item(self, item_id: str) -> Optional[InventoryItem]:
        """Retrieve an inventory item by ID."""
        return self._inventory.get(item_id)

    def get_inventory_by_sku(self, product_sku: str) -> list[InventoryItem]:
        """Get all inventory items for a specific SKU."""
        return [i for i in self._inventory.values() if i.product_sku == product_sku]

    def remove_inventory_item(self, item_id: str) -> bool:
        """Remove an inventory item by ID. Returns True if removed."""
        if item_id in self._inventory:
            del self._inventory[item_id]
            return True
        return False

    def list_inventory(
        self, zone_id: Optional[str] = None, warehouse_id: Optional[str] = None
    ) -> list[InventoryItem]:
        """List inventory items with optional filtering."""
        results = list(self._inventory.values())
        if zone_id is not None:
            results = [i for i in results if i.zone_id == zone_id]
        if warehouse_id is not None:
            # Filter by items in zones belonging to the warehouse
            warehouse = self._warehouses.get(warehouse_id)
            if warehouse:
                zone_ids = {z.id for z in warehouse.zones}
                results = [i for i in results if i.zone_id in zone_ids]
        return results

    def get_low_stock_items(self) -> list[InventoryItem]:
        """Get all items that need reordering."""
        return [i for i in self._inventory.values() if i.needs_reorder]

    def get_expired_items(self) -> list[InventoryItem]:
        """Get all expired items."""
        return [i for i in self._inventory.values() if i.is_expired]

    def get_total_inventory_value(self) -> float:
        """Calculate total value of all inventory."""
        return sum(i.total_value for i in self._inventory.values())

    def get_total_quantity(self) -> int:
        """Calculate total quantity across all inventory."""
        return sum(i.quantity for i in self._inventory.values())

    # ── Stock movement ─────────────────────────────────────────────

    def record_movement(self, movement: StockMovement) -> StockMovement:
        """Record a stock movement."""
        if movement.id in self._movements:
            raise ValueError(f"Movement with id {movement.id} already exists")
        self._movements[movement.id] = movement
        return movement

    def get_movement(self, movement_id: str) -> Optional[StockMovement]:
        """Retrieve a stock movement by ID."""
        return self._movements.get(movement_id)

    def list_movements(
        self,
        item_id: Optional[str] = None,
        movement_type: Optional[StockMovementType] = None,
    ) -> list[StockMovement]:
        """List stock movements with optional filtering."""
        results = list(self._movements.values())
        if item_id is not None:
            results = [m for m in results if m.item_id == item_id]
        if movement_type is not None:
            results = [m for m in results if m.movement_type == movement_type]
        return results

    def receive_stock(
        self,
        item_id: str,
        quantity: int,
        reference: str = "",
        notes: str = "",
    ) -> StockMovement:
        """Receive stock into inventory."""
        item = self._inventory.get(item_id)
        if not item:
            raise ValueError(f"Inventory item {item_id} not found")
        item.add_stock(quantity)
        movement = StockMovement(
            item_id=item_id,
            movement_type=StockMovementType.RECEIPT,
            quantity=quantity,
            to_zone_id=item.zone_id,
            reference=reference,
            notes=notes,
        )
        self._movements[movement.id] = movement
        return movement

    def issue_stock(
        self,
        item_id: str,
        quantity: int,
        reference: str = "",
        notes: str = "",
    ) -> StockMovement:
        """Issue stock from inventory."""
        item = self._inventory.get(item_id)
        if not item:
            raise ValueError(f"Inventory item {item_id} not found")
        item.remove_stock(quantity)
        movement = StockMovement(
            item_id=item_id,
            movement_type=StockMovementType.ISSUE,
            quantity=quantity,
            from_zone_id=item.zone_id,
            reference=reference,
            notes=notes,
        )
        self._movements[movement.id] = movement
        return movement

    def transfer_stock(
        self,
        item_id: str,
        quantity: int,
        to_zone_id: str,
        reference: str = "",
        notes: str = "",
    ) -> StockMovement:
        """Transfer stock between zones."""
        item = self._inventory.get(item_id)
        if not item:
            raise ValueError(f"Inventory item {item_id} not found")
        if quantity > item.quantity:
            raise ValueError("Cannot transfer more than available quantity")
        from_zone = item.zone_id
        item.remove_stock(quantity)
        # In a real system, you'd create a new item in the target zone
        # or update zone assignment. Here we track the movement.
        movement = StockMovement(
            item_id=item_id,
            movement_type=StockMovementType.TRANSFER,
            quantity=quantity,
            from_zone_id=from_zone,
            to_zone_id=to_zone_id,
            reference=reference,
            notes=notes,
        )
        self._movements[movement.id] = movement
        return movement

    def adjust_stock(
        self,
        item_id: str,
        new_quantity: int,
        reason: str = "",
    ) -> StockMovement:
        """Adjust stock quantity."""
        item = self._inventory.get(item_id)
        if not item:
            raise ValueError(f"Inventory item {item_id} not found")
        old_quantity = item.quantity
        item.adjust_stock(new_quantity, reason)
        movement = StockMovement(
            item_id=item_id,
            movement_type=StockMovementType.ADJUSTMENT,
            quantity=abs(new_quantity - old_quantity),
            reference=reason,
            notes=reason,
        )
        self._movements[movement.id] = movement
        return movement

    # ── Statistics ─────────────────────────────────────────────────

    def count_warehouses(self) -> int:
        """Return total number of warehouses."""
        return len(self._warehouses)

    def count_inventory_items(self) -> int:
        """Return total number of inventory items."""
        return len(self._inventory)

    def count_movements(self) -> int:
        """Return total number of stock movements."""
        return len(self._movements)

    def clear(self) -> None:
        """Remove all warehouses, inventory, and movements."""
        self._warehouses.clear()
        self._inventory.clear()
        self._movements.clear()
