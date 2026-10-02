"""Order management: tracking, status updates, and history."""

from __future__ import annotations

from typing import Optional

from .models import Order, OrderItem, OrderStatus


class OrderManager:
    """Manages order lifecycle and retrieval."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def create_order(self, order: Order) -> Order:
        self._orders[order.id] = order
        return order

    def get_order(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    def update_status(self, order_id: str, status: OrderStatus) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        order.update_status(status)
        return order

    def cancel_order(self, order_id: str) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            raise ValueError(f"Cannot cancel order in {order.status} status")
        order.update_status(OrderStatus.CANCELLED)
        return order

    def get_orders_by_customer(self, customer_id: str) -> list[Order]:
        return [o for o in self._orders.values() if o.customer_id == customer_id]

    def get_orders_by_status(self, status: OrderStatus) -> list[Order]:
        return [o for o in self._orders.values() if o.status == status]

    def list_orders(self) -> list[Order]:
        return list(self._orders.values())

    def add_note(self, order_id: str, note: str) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found")
        if order.notes:
            order.notes += f"\n{note}"
        else:
            order.notes = note
        return order

    def count(self) -> int:
        return len(self._orders)

    def clear(self) -> None:
        self._orders.clear()
