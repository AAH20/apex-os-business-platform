"""Read models for the CQRS system."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from apex_os_bp.cqrs.base import Event, ReadModel


class OrderReadModel(ReadModel):
    """Read model for orders."""

    def __init__(self):
        self._orders: Dict[UUID, Dict[str, Any]] = {}

    def project(self, event: Event) -> None:
        if event.event_type == "OrderCreated":
            self._orders[event.aggregate_id] = {
                "order_id": str(event.aggregate_id),
                "customer_id": event.metadata.get("customer_id"),
                "items": event.metadata.get("items", []),
                "currency": event.metadata.get("currency", "USD"),
                "status": "pending",
                "notes": event.metadata.get("notes"),
                "created_at": event.timestamp.isoformat(),
                "updated_at": event.timestamp.isoformat(),
            }
        elif event.event_type == "OrderUpdated":
            if event.aggregate_id in self._orders:
                order = self._orders[event.aggregate_id]
                if event.metadata.get("items") is not None:
                    order["items"] = event.metadata["items"]
                if event.metadata.get("notes") is not None:
                    order["notes"] = event.metadata["notes"]
                order["updated_at"] = event.timestamp.isoformat()
        elif event.event_type == "OrderCancelled":
            if event.aggregate_id in self._orders:
                self._orders[event.aggregate_id]["status"] = "cancelled"
                self._orders[event.aggregate_id]["updated_at"] = event.timestamp.isoformat()

    def get(self, order_id: UUID) -> Optional[Dict[str, Any]]:
        return self._orders.get(order_id)

    def list(
        self,
        customer_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        results = list(self._orders.values())
        if customer_id:
            results = [o for o in results if o.get("customer_id") == str(customer_id)]
        if status:
            results = [o for o in results if o.get("status") == status]
        return results[offset : offset + limit]


class CustomerReadModel(ReadModel):
    """Read model for customers."""

    def __init__(self):
        self._customers: Dict[UUID, Dict[str, Any]] = {}

    def project(self, event: Event) -> None:
        if event.event_type == "CustomerCreated":
            self._customers[event.aggregate_id] = {
                "customer_id": str(event.aggregate_id),
                "name": event.metadata.get("name"),
                "email": event.metadata.get("email"),
                "phone": event.metadata.get("phone"),
                "address": event.metadata.get("address"),
                "created_at": event.timestamp.isoformat(),
                "updated_at": event.timestamp.isoformat(),
            }
        elif event.event_type == "CustomerUpdated":
            if event.aggregate_id in self._customers:
                customer = self._customers[event.aggregate_id]
                for field in ("name", "email", "phone", "address"):
                    if event.metadata.get(field) is not None:
                        customer[field] = event.metadata[field]
                customer["updated_at"] = event.timestamp.isoformat()

    def get(self, customer_id: UUID) -> Optional[Dict[str, Any]]:
        return self._customers.get(customer_id)

    def list(
        self,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        results = list(self._customers.values())
        if search:
            search_lower = search.lower()
            results = [
                c for c in results
                if search_lower in c.get("name", "").lower()
                or search_lower in c.get("email", "").lower()
            ]
        return results[offset : offset + limit]


class ProductReadModel(ReadModel):
    """Read model for products."""

    def __init__(self):
        self._products: Dict[UUID, Dict[str, Any]] = {}

    def project(self, event: Event) -> None:
        if event.event_type == "ProductCreated":
            self._products[event.aggregate_id] = {
                "product_id": str(event.aggregate_id),
                "name": event.metadata.get("name"),
                "description": event.metadata.get("description"),
                "price": event.metadata.get("price"),
                "sku": event.metadata.get("sku"),
                "category": event.metadata.get("category"),
                "created_at": event.timestamp.isoformat(),
                "updated_at": event.timestamp.isoformat(),
            }
        elif event.event_type == "ProductUpdated":
            if event.aggregate_id in self._products:
                product = self._products[event.aggregate_id]
                for field in ("name", "description", "price", "category"):
                    if event.metadata.get(field) is not None:
                        product[field] = event.metadata[field]
                product["updated_at"] = event.timestamp.isoformat()

    def get(self, product_id: UUID) -> Optional[Dict[str, Any]]:
        return self._products.get(product_id)

    def list(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        results = list(self._products.values())
        if category:
            results = [p for p in results if p.get("category") == category]
        if search:
            search_lower = search.lower()
            results = [
                p for p in results
                if search_lower in p.get("name", "").lower()
                or search_lower in p.get("description", "").lower()
            ]
        return results[offset : offset + limit]
