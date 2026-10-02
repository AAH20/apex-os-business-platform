"""Sales order management."""
from __future__ import annotations

from typing import Dict, List, Optional

from apex_os_bp.inventory.models import (
    OrderStatus,
    SalesOrder,
    SalesOrderLine,
)


class SalesOrderManager:
    """Sales order management."""

    def __init__(self):
        self._orders: Dict[str, SalesOrder] = {}

    def create_order(
        self,
        customer_id: str,
        lines: Optional[List[SalesOrderLine]] = None,
        **kwargs,
    ) -> SalesOrder:
        """Create a new sales order."""
        order = SalesOrder.create(
            customer_id=customer_id,
            lines=lines or [],
            **kwargs,
        )
        self._orders[order.id] = order
        return order

    def get_order(self, order_id: str) -> Optional[SalesOrder]:
        """Get sales order by ID."""
        return self._orders.get(order_id)

    def add_line(
        self,
        order_id: str,
        product_id: str,
        quantity: int,
        unit_price: float,
    ) -> SalesOrderLine:
        """Add a line item to a sales order."""
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Sales order not found: {order_id}")
        if order.status != OrderStatus.DRAFT:
            raise ValueError(f"Cannot modify order with status: {order.status}")
        line = SalesOrderLine(
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
        )
        order.lines.append(line)
        return line

    def update_line(
        self,
        order_id: str,
        line_index: int,
        **kwargs,
    ) -> SalesOrderLine:
        """Update a line item."""
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Sales order not found: {order_id}")
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
            raise ValueError(f"Sales order not found: {order_id}")
        if line_index >= len(order.lines):
            raise ValueError(f"Line index out of range: {line_index}")
        order.lines.pop(line_index)

    def submit_order(self, order_id: str) -> SalesOrder:
        """Submit sales order for processing."""
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Sales order not found: {order_id}")
        if order.status != OrderStatus.DRAFT:
            raise ValueError(f"Cannot submit order with status: {order.status}")
        order.status = OrderStatus.PENDING
        return order

    def confirm_order(self, order_id: str) -> SalesOrder:
        """Confirm sales order."""
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Sales order not found: {order_id}")
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Cannot confirm order with status: {order.status}")
        order.status = OrderStatus.CONFIRMED
        return order

    def fulfill_order(
        self,
        order_id: str,
        fulfilled_quantities: Optional[Dict[int, int]] = None,
    ) -> SalesOrder:
        """Fulfill sales order (fully or partially)."""
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Sales order not found: {order_id}")
        if order.status not in (OrderStatus.CONFIRMED, OrderStatus.PENDING):
            raise ValueError(f"Cannot fulfill order with status: {order.status}")

        if fulfilled_quantities:
            for line_idx, qty in fulfilled_quantities.items():
                if line_idx < len(order.lines):
                    order.lines[line_idx].fulfilled_quantity = qty
        else:
            # Full fulfill
            for line in order.lines:
                line.fulfilled_quantity = line.quantity

        if order.is_fully_fulfilled:
            order.status = OrderStatus.SHIPPED
        return order

    def cancel_order(self, order_id: str) -> SalesOrder:
        """Cancel sales order."""
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"Sales order not found: {order_id}")
        if order.status in (OrderStatus.SHIPPED, OrderStatus.CANCELLED):
            raise ValueError(f"Cannot cancel order with status: {order.status}")
        order.status = OrderStatus.CANCELLED
        return order

    def list_orders(
        self,
        customer_id: Optional[str] = None,
        status: Optional[OrderStatus] = None,
    ) -> List[SalesOrder]:
        """List sales orders, optionally filtered."""
        orders = list(self._orders.values())
        if customer_id:
            orders = [o for o in orders if o.customer_id == customer_id]
        if status:
            orders = [o for o in orders if o.status == status]
        return orders

    def get_open_orders(self) -> List[SalesOrder]:
        """Get all open (non-shipped, non-cancelled) orders."""
        return [
            o for o in self._orders.values()
            if o.status not in (OrderStatus.SHIPPED, OrderStatus.CANCELLED)
        ]
