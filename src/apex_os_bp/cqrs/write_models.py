"""Write models (aggregate roots) for the CQRS system."""

from typing import List
from uuid import UUID

from apex_os_bp.cqrs.base import Event, WriteModel


class OrderAggregate(WriteModel):
    """Aggregate root for orders."""

    def __init__(self, order_id: UUID):
        self._id = order_id
        self._customer_id: UUID = UUID(int=0)
        self._items: List[dict] = []
        self._currency: str = "USD"
        self._status: str = "pending"
        self._notes: str = ""
        self._version: int = 0
        self._uncommitted: List[Event] = []

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def version(self) -> int:
        return self._version

    def apply(self, event: Event) -> None:
        if event.event_type == "OrderCreated":
            self._customer_id = UUID(event.metadata.get("customer_id", str(UUID(int=0))))
            self._items = event.metadata.get("items", [])
            self._currency = event.metadata.get("currency", "USD")
            self._notes = event.metadata.get("notes", "")
            self._status = "pending"
        elif event.event_type == "OrderUpdated":
            if event.metadata.get("items") is not None:
                self._items = event.metadata["items"]
            if event.metadata.get("notes") is not None:
                self._notes = event.metadata["notes"]
        elif event.event_type == "OrderCancelled":
            self._status = "cancelled"
        self._version += 1

    def uncommitted_events(self) -> List[Event]:
        return list(self._uncommitted)

    def mark_committed(self) -> None:
        self._uncommitted.clear()

    def create(self, customer_id: UUID, items: List[dict], currency: str, notes: str = "") -> None:
        from apex_os_bp.cqrs.events import OrderCreatedEvent
        event = OrderCreatedEvent(
            aggregate_id=self._id,
            event_type="OrderCreated",
            metadata={
                "customer_id": str(customer_id),
                "items": items,
                "currency": currency,
                "notes": notes,
            },
        )
        self.apply(event)
        self._uncommitted.append(event)

    def update(self, items: List[dict] = None, notes: str = None) -> None:
        from apex_os_bp.cqrs.events import OrderUpdatedEvent
        event = OrderUpdatedEvent(
            aggregate_id=self._id,
            event_type="OrderUpdated",
            metadata={"items": items, "notes": notes},
        )
        self.apply(event)
        self._uncommitted.append(event)

    def cancel(self, reason: str) -> None:
        from apex_os_bp.cqrs.events import OrderCancelledEvent
        event = OrderCancelledEvent(
            aggregate_id=self._id,
            event_type="OrderCancelled",
            metadata={"reason": reason},
        )
        self.apply(event)
        self._uncommitted.append(event)


class CustomerAggregate(WriteModel):
    """Aggregate root for customers."""

    def __init__(self, customer_id: UUID):
        self._id = customer_id
        self._name: str = ""
        self._email: str = ""
        self._phone: str = ""
        self._address: str = ""
        self._version: int = 0
        self._uncommitted: List[Event] = []

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def version(self) -> int:
        return self._version

    def apply(self, event: Event) -> None:
        if event.event_type == "CustomerCreated":
            self._name = event.metadata.get("name", "")
            self._email = event.metadata.get("email", "")
            self._phone = event.metadata.get("phone", "")
            self._address = event.metadata.get("address", "")
        elif event.event_type == "CustomerUpdated":
            for field in ("name", "email", "phone", "address"):
                if event.metadata.get(field) is not None:
                    setattr(self, f"_{field}", event.metadata[field])
        self._version += 1

    def uncommitted_events(self) -> List[Event]:
        return list(self._uncommitted)

    def mark_committed(self) -> None:
        self._uncommitted.clear()

    def create(self, name: str, email: str, phone: str = "", address: str = "") -> None:
        from apex_os_bp.cqrs.events import CustomerCreatedEvent
        event = CustomerCreatedEvent(
            aggregate_id=self._id,
            event_type="CustomerCreated",
            metadata={"name": name, "email": email, "phone": phone, "address": address},
        )
        self.apply(event)
        self._uncommitted.append(event)

    def update(self, name: str = None, email: str = None, phone: str = None, address: str = None) -> None:
        from apex_os_bp.cqrs.events import CustomerUpdatedEvent
        event = CustomerUpdatedEvent(
            aggregate_id=self._id,
            event_type="CustomerUpdated",
            metadata={"name": name, "email": email, "phone": phone, "address": address},
        )
        self.apply(event)
        self._uncommitted.append(event)


class ProductAggregate(WriteModel):
    """Aggregate root for products."""

    def __init__(self, product_id: UUID):
        self._id = product_id
        self._name: str = ""
        self._description: str = ""
        self._price: str = "0.00"
        self._sku: str = ""
        self._category: str = ""
        self._version: int = 0
        self._uncommitted: List[Event] = []

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def version(self) -> int:
        return self._version

    def apply(self, event: Event) -> None:
        if event.event_type == "ProductCreated":
            self._name = event.metadata.get("name", "")
            self._description = event.metadata.get("description", "")
            self._price = event.metadata.get("price", "0.00")
            self._sku = event.metadata.get("sku", "")
            self._category = event.metadata.get("category", "")
        elif event.event_type == "ProductUpdated":
            for field in ("name", "description", "price", "category"):
                if event.metadata.get(field) is not None:
                    setattr(self, f"_{field}", event.metadata[field])
        self._version += 1

    def uncommitted_events(self) -> List[Event]:
        return list(self._uncommitted)

    def mark_committed(self) -> None:
        self._uncommitted.clear()

    def create(self, name: str, description: str, price: str, sku: str, category: str = "") -> None:
        from apex_os_bp.cqrs.events import ProductCreatedEvent
        event = ProductCreatedEvent(
            aggregate_id=self._id,
            event_type="ProductCreated",
            metadata={
                "name": name,
                "description": description,
                "price": price,
                "sku": sku,
                "category": category,
            },
        )
        self.apply(event)
        self._uncommitted.append(event)

    def update(self, name: str = None, description: str = None, price: str = None, category: str = None) -> None:
        from apex_os_bp.cqrs.events import ProductUpdatedEvent
        event = ProductUpdatedEvent(
            aggregate_id=self._id,
            event_type="ProductUpdated",
            metadata={"name": name, "description": description, "price": price, "category": category},
        )
        self.apply(event)
        self._uncommitted.append(event)
