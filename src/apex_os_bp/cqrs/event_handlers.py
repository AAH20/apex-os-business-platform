"""Event handlers for the CQRS system."""

from typing import Any, Dict

from apex_os_bp.cqrs.base import EventHandler
from apex_os_bp.cqrs.events import (
    CustomerCreatedEvent,
    CustomerUpdatedEvent,
    OrderCancelledEvent,
    OrderCreatedEvent,
    OrderUpdatedEvent,
    ProductCreatedEvent,
    ProductUpdatedEvent,
)


class OrderCreatedHandler(EventHandler[OrderCreatedEvent]):
    """Handler for OrderCreatedEvent."""

    def __init__(self, read_model: Dict[str, Any]):
        self._read_model = read_model

    async def handle(self, event: OrderCreatedEvent) -> None:
        self._read_model[event.aggregate_id] = {
            "order_id": str(event.aggregate_id),
            "customer_id": event.metadata.get("customer_id"),
            "items": event.metadata.get("items", []),
            "currency": event.metadata.get("currency", "USD"),
            "status": "pending",
            "notes": event.metadata.get("notes"),
            "created_at": event.timestamp.isoformat(),
            "updated_at": event.timestamp.isoformat(),
        }


class OrderUpdatedHandler(EventHandler[OrderUpdatedEvent]):
    """Handler for OrderUpdatedEvent."""

    def __init__(self, read_model: Dict[str, Any]):
        self._read_model = read_model

    async def handle(self, event: OrderUpdatedEvent) -> None:
        if event.aggregate_id in self._read_model:
            order = self._read_model[event.aggregate_id]
            if event.metadata.get("items") is not None:
                order["items"] = event.metadata["items"]
            if event.metadata.get("notes") is not None:
                order["notes"] = event.metadata["notes"]
            order["updated_at"] = event.timestamp.isoformat()


class OrderCancelledHandler(EventHandler[OrderCancelledEvent]):
    """Handler for OrderCancelledEvent."""

    def __init__(self, read_model: Dict[str, Any]):
        self._read_model = read_model

    async def handle(self, event: OrderCancelledEvent) -> None:
        if event.aggregate_id in self._read_model:
            self._read_model[event.aggregate_id]["status"] = "cancelled"
            self._read_model[event.aggregate_id]["updated_at"] = event.timestamp.isoformat()


class CustomerCreatedHandler(EventHandler[CustomerCreatedEvent]):
    """Handler for CustomerCreatedEvent."""

    def __init__(self, read_model: Dict[str, Any]):
        self._read_model = read_model

    async def handle(self, event: CustomerCreatedEvent) -> None:
        self._read_model[event.aggregate_id] = {
            "customer_id": str(event.aggregate_id),
            "name": event.metadata.get("name"),
            "email": event.metadata.get("email"),
            "phone": event.metadata.get("phone"),
            "address": event.metadata.get("address"),
            "created_at": event.timestamp.isoformat(),
            "updated_at": event.timestamp.isoformat(),
        }


class CustomerUpdatedHandler(EventHandler[CustomerUpdatedEvent]):
    """Handler for CustomerUpdatedEvent."""

    def __init__(self, read_model: Dict[str, Any]):
        self._read_model = read_model

    async def handle(self, event: CustomerUpdatedEvent) -> None:
        if event.aggregate_id in self._read_model:
            customer = self._read_model[event.aggregate_id]
            for field in ("name", "email", "phone", "address"):
                if event.metadata.get(field) is not None:
                    customer[field] = event.metadata[field]
            customer["updated_at"] = event.timestamp.isoformat()


class ProductCreatedHandler(EventHandler[ProductCreatedEvent]):
    """Handler for ProductCreatedEvent."""

    def __init__(self, read_model: Dict[str, Any]):
        self._read_model = read_model

    async def handle(self, event: ProductCreatedEvent) -> None:
        self._read_model[event.aggregate_id] = {
            "product_id": str(event.aggregate_id),
            "name": event.metadata.get("name"),
            "description": event.metadata.get("description"),
            "price": event.metadata.get("price"),
            "sku": event.metadata.get("sku"),
            "category": event.metadata.get("category"),
            "created_at": event.timestamp.isoformat(),
            "updated_at": event.timestamp.isoformat(),
        }


class ProductUpdatedHandler(EventHandler[ProductUpdatedEvent]):
    """Handler for ProductUpdatedEvent."""

    def __init__(self, read_model: Dict[str, Any]):
        self._read_model = read_model

    async def handle(self, event: ProductUpdatedEvent) -> None:
        if event.aggregate_id in self._read_model:
            product = self._read_model[event.aggregate_id]
            for field in ("name", "description", "price", "category"):
                if event.metadata.get(field) is not None:
                    product[field] = event.metadata[field]
            product["updated_at"] = event.timestamp.isoformat()
