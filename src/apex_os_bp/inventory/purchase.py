"""Purchase order management."""
from __future__ import annotations

from typing import Dict, List, Optional

from apex_os_bp.inventory.models import (
    OrderStatus,
    PurchaseOrder,
    PurchaseOrderLine,
)


class PurchaseOrderManager:
    """Purchase order management."""

    def __init__(self):
        self._orders: Dict[str, PurchaseOrder] = {}

    def create_order(
        self,
        supplier_id: str,
        lines: Optional[List[PurchaseOrderLine]] = None,
        **kwargs,
    ) -> PurchaseOrder:
        """Create a new purchase order."""
        order = PurchaseOrder.create(
            supplier_id=supplier_id,
            lines=lines or [],
            **kwargs,
        )
        self._orders[order.id] = order
        return order

    def get_order(self, order_id: str) -> Optional[PurchaseOrder]:
        """Get purchase order by ID."""
        return self._orders.get(order_id)

    def add_line(
        self,
        order_id: str,
        product_id: str,
        quantity: int,
        unit_cost: float,
    ) -> PurchaseOrderLine:
        """Add a line item to a purchase order."""
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Purchase order not found: {order_id}")
        if order.status != OrderStatus.DRAFT:
            raise ValueError(f"Cannot modify order with status: {order.status}")
        line = PurchaseOrderLine(
            product_id=product_id,
            quantity=quantity,
            unit_cost=unit_cost,
        )
        order.lines.append(line)
        return line

    def update_line(
        self,
        order_id: str,
        line_index: int,
        **kwargs,
    ) -> PurchaseOrderLine:
        """Update a line item."""
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Purchase order not found: {order_id}")
        if line_index >= len(order.lines):
            raise ValueError(f"Line index out of range: {line_index}")
        line = order.lines[line_index]
        for key, value in kwargs.items():
            if hasattr(line, key):
                setattr(line, key, value)
        return line

    def remove_line(self, order_id: str, line_index: int) -> None:
        """Remove a line item."""
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Purchase order not found: {order_id}")
        if line_index >= len(order.lines):
            raise ValueError(f"Line index out of range: {line_index}")
        order.lines.pop(line_index)

    def submit_order(self, order_id: str) -> PurchaseOrder:
        """Submit purchase order for approval."""
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Purchase order not found: {order_id}")
        if order.status != OrderStatus.DRAFT:
            raise ValueError(f"Cannot submit order with status: {order.status}")
        order.status = OrderStatus.PENDING
        return order

    def confirm_order(self, order_id: str) -> PurchaseOrder:
        """Confirm purchase order."""
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Purchase order not found: {order_id}")
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Cannot confirm order with status: {order.status}")
        order.status = OrderStatus.CONFIRMED
        return order

    def mark_shipped(self, order_id: str) -> PurchaseOrder:
        """Mark order as shipped by supplier."""
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Purchase order not found: {order_id}")
        if order.status != OrderStatus.CONFIRMED:
            raise ValueError(f"Cannot ship order with status: {order.status}")
        order.status = OrderStatus.SHIPPED
        return order

    def receive_order(
        self,
        order_id: str,
        received_quantities: Optional[Dict[int, int]] = None,
    ) -> PurchaseOrder:
        """Receive purchase order (fully or partially)."""
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Purchase order not found: {order_id}")
        if order.status not in (OrderStatus.SHIPPED, OrderStatus.CONFIRMED):
            raise ValueError(f"Cannot receive order with status: {order.status}")

        if received_quantities:
            for line_idx, qty in received_quantities.items():
                if line_idx < len(order.lines):
                    order.lines[line_idx].received_quantity = qty
        else:
            # Full receive
            for line in order.lines:
                line.received_quantity = line.quantity

        if order.is_fully_received:
            order.status = OrderStatus.RECEIVED
        return order

    def cancel_order(self, order_id: str) -> PurchaseOrder:
        """Cancel purchase order."""
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Purchase order not found: {order_id}")
        if order.status in (OrderStatus.RECEIVED, OrderStatus.CANCELLED):
            raise ValueError(f"Cannot cancel order with status: {order.status}")
        order.status = OrderStatus.CANCELLED
        return order

    def list_orders(
        self,
        supplier_id: Optional[str] = None,
        status: Optional[OrderStatus] = None,
    ) -> List[PurchaseOrder]:
        """List purchase orders, optionally filtered."""
        orders = list(self._orders.values())
        if supplier_id:
            orders = [o for o in orders if o.supplier_id == supplier_id]
        if status:
            orders = [o for o in orders if o.status == status]
        return orders

    def get_pending_orders(self) -> List[PurchaseOrder]:
        """Get all pending (non-received, non-cancelled) orders."""
        return [
            o for o in self._orders.values()
            if o.status not in (OrderStatus.RECEIVED, OrderStatus.CANCELLED)
        ]
