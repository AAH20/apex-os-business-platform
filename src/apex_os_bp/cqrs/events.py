"""Event definitions for the CQRS system."""

from dataclasses import dataclass

from apex_os_bp.cqrs.base import Event


@dataclass(frozen=True)
class OrderCreatedEvent(Event):
    """Event emitted when an order is created."""
    event_type: str = "OrderCreated"


@dataclass(frozen=True)
class OrderUpdatedEvent(Event):
    """Event emitted when an order is updated."""
    event_type: str = "OrderUpdated"


@dataclass(frozen=True)
class OrderCancelledEvent(Event):
    """Event emitted when an order is cancelled."""
    event_type: str = "OrderCancelled"


@dataclass(frozen=True)
class CustomerCreatedEvent(Event):
    """Event emitted when a customer is created."""
    event_type: str = "CustomerCreated"


@dataclass(frozen=True)
class CustomerUpdatedEvent(Event):
    """Event emitted when a customer is updated."""
    event_type: str = "CustomerUpdated"


@dataclass(frozen=True)
class ProductCreatedEvent(Event):
    """Event emitted when a product is created."""
    event_type: str = "ProductCreated"


@dataclass(frozen=True)
class ProductUpdatedEvent(Event):
    """Event emitted when a product is updated."""
    event_type: str = "ProductUpdated"
