"""Inventory data models."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class ProductCategory(Enum):
    """Product categories."""
    RAW_MATERIAL = "raw_material"
    FINISHED_GOOD = "finished_good"
    MERCHANDISE = "merchandise"
    SUPPLIES = "supplies"


class OrderStatus(Enum):
    """Order status."""
    DRAFT = "draft"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class ValuationMethod(Enum):
    """Inventory valuation methods."""
    FIFO = "fifo"
    LIFO = "lifo"
    WEIGHTED_AVERAGE = "weighted_average"
    STANDARD_COST = "standard_cost"


@dataclass
class Product:
    """Product catalog entry."""
    id: str
    sku: str
    name: str
    category: ProductCategory
    unit_price: float
    unit_cost: float
    unit_of_measure: str = "ea"
    description: str = ""
    reorder_point: int = 0
    reorder_quantity: int = 0
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        sku: str,
        name: str,
        category: ProductCategory,
        unit_price: float,
        unit_cost: float,
        **kwargs,
    ) -> "Product":
        """Create a new product with auto-generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            sku=sku,
            name=name,
            category=category,
            unit_price=unit_price,
            unit_cost=unit_cost,
            **kwargs,
        )


@dataclass
class StockItem:
    """Stock item tracking a product's quantity in a location."""
    product_id: str
    location: str
    quantity: int = 0
    reserved_quantity: int = 0
    lot_number: Optional[str] = None
    expiry_date: Optional[str] = None
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def available_quantity(self) -> int:
        """Available quantity (total minus reserved)."""
        return self.quantity - self.reserved_quantity

    def adjust(self, delta: int) -> None:
        """Adjust quantity by delta (positive or negative)."""
        new_qty = self.quantity + delta
        if new_qty < 0:
            raise ValueError(f"Insufficient stock: {self.quantity} + {delta} = {new_qty}")
        self.quantity = new_qty
        self.last_updated = datetime.now().isoformat()

    def reserve(self, amount: int) -> None:
        """Reserve stock."""
        if amount > self.available_quantity:
            raise ValueError(
                f"Cannot reserve {amount}, only {self.available_quantity} available"
            )
        self.reserved_quantity += amount
        self.last_updated = datetime.now().isoformat()

    def release(self, amount: int) -> None:
        """Release reserved stock."""
        if amount > self.reserved_quantity:
            raise ValueError(
                f"Cannot release {amount}, only {self.reserved_quantity} reserved"
            )
        self.reserved_quantity -= amount
        self.last_updated = datetime.now().isoformat()


@dataclass
class StockMovement:
    """Stock movement record (inbound or outbound)."""
    id: str
    product_id: str
    location: str
    quantity: int
    movement_type: str  # "in" or "out"
    reference: Optional[str] = None  # PO or SO ID
    unit_cost: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""

    @classmethod
    def create(
        cls,
        product_id: str,
        location: str,
        quantity: int,
        movement_type: str,
        **kwargs,
    ) -> "StockMovement":
        """Create a new stock movement."""
        return cls(
            id=str(uuid.uuid4()),
            product_id=product_id,
            location=location,
            quantity=quantity,
            movement_type=movement_type,
            **kwargs,
        )


@dataclass
class PurchaseOrderLine:
    """Purchase order line item."""
    product_id: str
    quantity: int
    unit_cost: float
    received_quantity: int = 0

    @property
    def line_total(self) -> float:
        """Total cost for this line."""
        return self.quantity * self.unit_cost

    @property
    def is_fully_received(self) -> bool:
        """Check if line is fully received."""
        return self.received_quantity >= self.quantity


@dataclass
class PurchaseOrder:
    """Purchase order."""
    id: str
    supplier_id: str
    lines: List[PurchaseOrderLine] = field(default_factory=list)
    status: OrderStatus = OrderStatus.DRAFT
    order_date: str = field(default_factory=lambda: datetime.now().isoformat())
    expected_date: Optional[str] = None
    received_date: Optional[str] = None
    notes: str = ""
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def create(cls, supplier_id: str, **kwargs) -> "PurchaseOrder":
        """Create a new purchase order."""
        return cls(
            id=str(uuid.uuid4()),
            supplier_id=supplier_id,
            **kwargs,
        )

    @property
    def total_cost(self) -> float:
        """Total cost of all lines."""
        return sum(line.line_total for line in self.lines)

    @property
    def total_quantity(self) -> int:
        """Total quantity of all lines."""
        return sum(line.quantity for line in self.lines)

    @property
    def is_fully_received(self) -> bool:
        """Check if all lines are fully received."""
        return all(line.is_fully_received for line in self.lines) if self.lines else False


@dataclass
class SalesOrderLine:
    """Sales order line item."""
    product_id: str
    quantity: int
    unit_price: float
    fulfilled_quantity: int = 0

    @property
    def line_total(self) -> float:
        """Total revenue for this line."""
        return self.quantity * self.unit_price

    @property
    def is_fully_fulfilled(self) -> bool:
        """Check if line is fully fulfilled."""
        return self.fulfilled_quantity >= self.quantity


@dataclass
class SalesOrder:
    """Sales order."""
    id: str
    customer_id: str
    lines: List[SalesOrderLine] = field(default_factory=list)
    status: OrderStatus = OrderStatus.DRAFT
    order_date: str = field(default_factory=lambda: datetime.now().isoformat())
    required_date: Optional[str] = None
    shipped_date: Optional[str] = None
    notes: str = ""
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def create(cls, customer_id: str, **kwargs) -> "SalesOrder":
        """Create a new sales order."""
        return cls(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            **kwargs,
        )

    @property
    def total_revenue(self) -> float:
        """Total revenue of all lines."""
        return sum(line.line_total for line in self.lines)

    @property
    def total_quantity(self) -> int:
        """Total quantity of all lines."""
        return sum(line.quantity for line in self.lines)

    @property
    def is_fully_fulfilled(self) -> bool:
        """Check if all lines are fully fulfilled."""
        return all(line.is_fully_fulfilled for line in self.lines) if self.lines else False
