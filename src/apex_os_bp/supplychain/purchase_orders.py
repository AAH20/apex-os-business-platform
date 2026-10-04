"""Purchase order module.

Manages the full lifecycle of purchase orders from draft through
receipt and closure.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional



class PurchaseOrderStatus(str, Enum):
    """Lifecycle status of a purchase order."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    SENT = "sent"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"
    CLOSED = "closed"


@dataclass
class PurchaseOrderItem:
    """Line item within a purchase order.

    Attributes:
        product_sku: Product stock-keeping unit.
        product_name: Human-readable product name.
        quantity: Ordered quantity.
        unit_price: Price per unit.
        received_quantity: Quantity received so far.
        notes: Line-item notes.
    """

    product_sku: str
    product_name: str
    quantity: int
    unit_price: float
    received_quantity: int = 0
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.product_sku:
            raise ValueError("Product SKU cannot be empty")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative")
        if self.received_quantity < 0:
            raise ValueError("Received quantity cannot be negative")
        if self.received_quantity > self.quantity:
            raise ValueError("Received quantity cannot exceed ordered quantity")

    @property
    def line_total(self) -> float:
        """Total cost for this line item."""
        return self.quantity * self.unit_price

    @property
    def pending_quantity(self) -> int:
        """Quantity not yet received."""
        return self.quantity - self.received_quantity

    @property
    def is_fully_received(self) -> bool:
        """Whether the full quantity has been received."""
        return self.received_quantity >= self.quantity

    def receive(self, qty: int) -> None:
        """Record receipt of a quantity."""
        if qty <= 0:
            raise ValueError("Receive quantity must be positive")
        if self.received_quantity + qty > self.quantity:
            raise ValueError("Cannot receive more than ordered quantity")
        self.received_quantity += qty

    def to_dict(self) -> dict:
        """Serialize line item to dictionary."""
        return {
            "product_sku": self.product_sku,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "received_quantity": self.received_quantity,
            "line_total": self.line_total,
            "pending_quantity": self.pending_quantity,
            "is_fully_received": self.is_fully_received,
            "notes": self.notes,
        }


@dataclass
class PurchaseOrder:
    """Represents a purchase order.

    Attributes:
        supplier_id: ID of the supplier.
        items: Line items on the order.
        status: Current lifecycle status.
        order_date: Date the order was created.
        expected_delivery: Expected delivery date.
        actual_delivery: Actual delivery date.
        currency: ISO 4217 currency code.
        notes: Free-form notes.
        id: Unique identifier.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    supplier_id: str
    items: list[PurchaseOrderItem] = field(default_factory=list)
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    order_date: date = field(default_factory=date.today)
    expected_delivery: Optional[date] = None
    actual_delivery: Optional[date] = None
    currency: str = "USD"
    notes: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.supplier_id:
            raise ValueError("Supplier ID cannot be empty")

    @property
    def total_amount(self) -> float:
        """Total value of the purchase order."""
        return sum(item.line_total for item in self.items)

    @property
    def total_quantity(self) -> int:
        """Total quantity across all line items."""
        return sum(item.quantity for item in self.items)

    @property
    def total_received(self) -> int:
        """Total quantity received across all line items."""
        return sum(item.received_quantity for item in self.items)

    @property
    def is_fully_received(self) -> bool:
        """Whether all items have been fully received."""
        return all(item.is_fully_received for item in self.items) and len(self.items) > 0

    @property
    def is_partially_received(self) -> bool:
        """Whether some but not all items have been received."""
        if not self.items:
            return False
        any_received = any(item.received_quantity > 0 for item in self.items)
        return any_received and not self.is_fully_received

    def add_item(self, item: PurchaseOrderItem) -> None:
        """Add a line item to the order."""
        if self.status != PurchaseOrderStatus.DRAFT:
            raise ValueError("Can only add items to a draft purchase order")
        self.items.append(item)
        self.updated_at = datetime.utcnow()

    def remove_item(self, product_sku: str) -> bool:
        """Remove a line item by SKU. Returns True if removed."""
        if self.status != PurchaseOrderStatus.DRAFT:
            raise ValueError("Can only remove items from a draft purchase order")
        for i, item in enumerate(self.items):
            if item.product_sku == product_sku:
                self.items.pop(i)
                self.updated_at = datetime.utcnow()
                return True
        return False

    def submit(self) -> None:
        """Submit the purchase order for approval."""
        if self.status != PurchaseOrderStatus.DRAFT:
            raise ValueError("Only draft purchase orders can be submitted")
        if not self.items:
            raise ValueError("Cannot submit a purchase order with no items")
        self.status = PurchaseOrderStatus.SUBMITTED
        self.updated_at = datetime.utcnow()

    def approve(self) -> None:
        """Approve the purchase order."""
        if self.status != PurchaseOrderStatus.SUBMITTED:
            raise ValueError("Only submitted purchase orders can be approved")
        self.status = PurchaseOrderStatus.APPROVED
        self.updated_at = datetime.utcnow()

    def send_to_supplier(self) -> None:
        """Mark the order as sent to the supplier."""
        if self.status != PurchaseOrderStatus.APPROVED:
            raise ValueError("Only approved purchase orders can be sent")
        self.status = PurchaseOrderStatus.SENT
        self.updated_at = datetime.utcnow()

    def receive_item(self, product_sku: str, qty: int) -> None:
        """Record receipt of a quantity for a specific item."""
        if self.status not in (
            PurchaseOrderStatus.SENT,
            PurchaseOrderStatus.PARTIALLY_RECEIVED,
        ):
            raise ValueError("Can only receive items for sent purchase orders")
        for item in self.items:
            if item.product_sku == product_sku:
                item.receive(qty)
                break
        else:
            raise ValueError(f"Item with SKU {product_sku} not found")

        # Update status based on receipt
        if self.is_fully_received:
            self.status = PurchaseOrderStatus.RECEIVED
            self.actual_delivery = date.today()
        elif self.is_partially_received:
            self.status = PurchaseOrderStatus.PARTIALLY_RECEIVED
        self.updated_at = datetime.utcnow()

    def cancel(self, reason: str = "") -> None:
        """Cancel the purchase order."""
        if self.status in (
            PurchaseOrderStatus.RECEIVED,
            PurchaseOrderStatus.CLOSED,
            PurchaseOrderStatus.CANCELLED,
        ):
            raise ValueError("Cannot cancel a received, closed, or already cancelled order")
        self.status = PurchaseOrderStatus.CANCELLED
        if reason:
            self.notes = f"{self.notes}\nCancelled: {reason}".strip()
        self.updated_at = datetime.utcnow()

    def close(self) -> None:
        """Close the purchase order."""
        if self.status != PurchaseOrderStatus.RECEIVED:
            raise ValueError("Only received purchase orders can be closed")
        self.status = PurchaseOrderStatus.CLOSED
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Serialize purchase order to dictionary."""
        return {
            "id": self.id,
            "supplier_id": self.supplier_id,
            "status": self.status.value,
            "order_date": self.order_date.isoformat(),
            "expected_delivery": self.expected_delivery.isoformat()
            if self.expected_delivery
            else None,
            "actual_delivery": self.actual_delivery.isoformat()
            if self.actual_delivery
            else None,
            "currency": self.currency,
            "total_amount": self.total_amount,
            "total_quantity": self.total_quantity,
            "total_received": self.total_received,
            "is_fully_received": self.is_fully_received,
            "is_partially_received": self.is_partially_received,
            "items": [item.to_dict() for item in self.items],
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class PurchaseOrderManager:
    """Manages a collection of purchase orders."""

    def __init__(self) -> None:
        self._orders: dict[str, PurchaseOrder] = {}

    def create_order(
        self, supplier_id: str, currency: str = "USD"
    ) -> PurchaseOrder:
        """Create a new draft purchase order."""
        order = PurchaseOrder(supplier_id=supplier_id, currency=currency)
        self._orders[order.id] = order
        return order

    def get_order(self, order_id: str) -> Optional[PurchaseOrder]:
        """Retrieve a purchase order by ID."""
        return self._orders.get(order_id)

    def remove_order(self, order_id: str) -> bool:
        """Remove a purchase order by ID. Returns True if removed."""
        if order_id in self._orders:
            del self._orders[order_id]
            return True
        return False

    def list_orders(
        self,
        status: Optional[PurchaseOrderStatus] = None,
        supplier_id: Optional[str] = None,
    ) -> list[PurchaseOrder]:
        """List purchase orders with optional filtering."""
        results = list(self._orders.values())
        if status is not None:
            results = [o for o in results if o.status == status]
        if supplier_id is not None:
            results = [o for o in results if o.supplier_id == supplier_id]
        return results

    def get_orders_by_supplier(self, supplier_id: str) -> list[PurchaseOrder]:
        """Get all purchase orders for a specific supplier."""
        return [o for o in self._orders.values() if o.supplier_id == supplier_id]

    def get_open_orders(self) -> list[PurchaseOrder]:
        """Get all orders that are not received, closed, or cancelled."""
        open_statuses = {
            PurchaseOrderStatus.DRAFT,
            PurchaseOrderStatus.SUBMITTED,
            PurchaseOrderStatus.APPROVED,
            PurchaseOrderStatus.SENT,
            PurchaseOrderStatus.PARTIALLY_RECEIVED,
        }
        return [o for o in self._orders.values() if o.status in open_statuses]

    def get_total_spend(self, supplier_id: Optional[str] = None) -> float:
        """Calculate total spend, optionally filtered by supplier."""
        orders = self.list_orders(supplier_id=supplier_id)
        return sum(o.total_amount for o in orders)

    def count(self) -> int:
        """Return total number of purchase orders."""
        return len(self._orders)

    def clear(self) -> None:
        """Remove all purchase orders."""
        self._orders.clear()
