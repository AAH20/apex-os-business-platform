"""Logistics module.

Manages shipments, carriers, and tracking events for goods
in transit between suppliers, warehouses, and customers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ShipmentStatus(str, Enum):
    """Lifecycle status of a shipment."""

    PENDING = "pending"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    EXCEPTION = "exception"
    RETURNED = "returned"
    CANCELLED = "cancelled"


@dataclass
class Carrier:
    """Represents a shipping carrier.

    Attributes:
        name: Carrier name.
        code: Carrier code (e.g., "FDX", "UPS").
        tracking_url_template: URL template with {tracking_number} placeholder.
        contact_phone: Carrier contact phone.
        contact_email: Carrier contact email.
        is_active: Whether the carrier is active.
        id: Unique identifier.
    """

    name: str
    code: str = ""
    tracking_url_template: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    is_active: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Carrier name cannot be empty")

    def get_tracking_url(self, tracking_number: str) -> str:
        """Generate a tracking URL for a tracking number."""
        if self.tracking_url_template:
            return self.tracking_url_template.format(tracking_number=tracking_number)
        return ""

    def to_dict(self) -> dict:
        """Serialize carrier to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "tracking_url_template": self.tracking_url_template,
            "contact_phone": self.contact_phone,
            "contact_email": self.contact_email,
            "is_active": self.is_active,
        }


@dataclass
class TrackingEvent:
    """A single tracking event in the shipment lifecycle.

    Attributes:
        timestamp: When the event occurred.
        location: Where the event occurred.
        description: Human-readable description.
        status: Shipment status at this event.
    """

    timestamp: datetime
    location: str
    description: str
    status: ShipmentStatus = ShipmentStatus.PENDING

    def to_dict(self) -> dict:
        """Serialize tracking event to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "location": self.location,
            "description": self.description,
            "status": self.status.value,
        }


@dataclass
class Shipment:
    """Represents a shipment in the logistics network.

    Attributes:
        carrier_id: ID of the carrier.
        origin: Origin address.
        destination: Destination address.
        weight_kg: Weight in kilograms.
        dimensions_cm: Dimensions as (length, width, height) in cm.
        status: Current shipment status.
        tracking_number: Carrier tracking number.
        estimated_delivery: Estimated delivery date/time.
        actual_delivery: Actual delivery date/time.
        shipping_cost: Cost of shipping.
        currency: ISO 4217 currency code.
        notes: Free-form notes.
        events: Tracking events.
        id: Unique identifier.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    carrier_id: str
    origin: str
    destination: str
    weight_kg: float = 0.0
    dimensions_cm: tuple[float, float, float] = (0.0, 0.0, 0.0)
    status: ShipmentStatus = ShipmentStatus.PENDING
    tracking_number: str = ""
    estimated_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    shipping_cost: float = 0.0
    currency: str = "USD"
    notes: str = ""
    events: list[TrackingEvent] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.carrier_id:
            raise ValueError("Carrier ID cannot be empty")
        if not self.origin:
            raise ValueError("Origin cannot be empty")
        if not self.destination:
            raise ValueError("Destination cannot be empty")
        if self.weight_kg < 0:
            raise ValueError("Weight cannot be negative")
        if self.shipping_cost < 0:
            raise ValueError("Shipping cost cannot be negative")

    @property
    def volume_cm3(self) -> float:
        """Calculate volume in cubic centimeters."""
        l, w, h = self.dimensions_cm
        return l * w * h

    @property
    def is_delivered(self) -> bool:
        """Whether the shipment has been delivered."""
        return self.status == ShipmentStatus.DELIVERED

    @property
    def is_in_transit(self) -> bool:
        """Whether the shipment is currently in transit."""
        return self.status in (
            ShipmentStatus.PICKED_UP,
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.OUT_FOR_DELIVERY,
        )

    @property
    def transit_time_hours(self) -> Optional[float]:
        """Calculate transit time in hours if delivered."""
        if self.actual_delivery and self.created_at:
            delta = self.actual_delivery - self.created_at
            return delta.total_seconds() / 3600
        return None

    def add_event(
        self,
        location: str,
        description: str,
        status: Optional[ShipmentStatus] = None,
        timestamp: Optional[datetime] = None,
    ) -> TrackingEvent:
        """Add a tracking event."""
        event = TrackingEvent(
            timestamp=timestamp or datetime.utcnow(),
            location=location,
            description=description,
            status=status or self.status,
        )
        self.events.append(event)
        if status is not None:
            self.status = status
        self.updated_at = datetime.utcnow()
        return event

    def update_status(
        self, status: ShipmentStatus, location: str = "", description: str = ""
    ) -> None:
        """Update shipment status and add a tracking event."""
        self.status = status
        if status == ShipmentStatus.DELIVERED:
            self.actual_delivery = datetime.utcnow()
        self.add_event(
            location=location or self.destination,
            description=description or f"Status updated to {status.value}",
            status=status,
        )
        self.updated_at = datetime.utcnow()

    def cancel(self, reason: str = "") -> None:
        """Cancel the shipment."""
        if self.status in (ShipmentStatus.DELIVERED, ShipmentStatus.RETURNED):
            raise ValueError("Cannot cancel a delivered or returned shipment")
        self.status = ShipmentStatus.CANCELLED
        if reason:
            self.notes = f"{self.notes}\nCancelled: {reason}".strip()
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Serialize shipment to dictionary."""
        return {
            "id": self.id,
            "carrier_id": self.carrier_id,
            "origin": self.origin,
            "destination": self.destination,
            "weight_kg": self.weight_kg,
            "dimensions_cm": list(self.dimensions_cm),
            "volume_cm3": self.volume_cm3,
            "status": self.status.value,
            "tracking_number": self.tracking_number,
            "estimated_delivery": self.estimated_delivery.isoformat()
            if self.estimated_delivery
            else None,
            "actual_delivery": self.actual_delivery.isoformat()
            if self.actual_delivery
            else None,
            "shipping_cost": self.shipping_cost,
            "currency": self.currency,
            "is_delivered": self.is_delivered,
            "is_in_transit": self.is_in_transit,
            "transit_time_hours": self.transit_time_hours,
            "events": [e.to_dict() for e in self.events],
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class LogisticsManager:
    """Manages shipments and carriers."""

    def __init__(self) -> None:
        self._shipments: dict[str, Shipment] = {}
        self._carriers: dict[str, Carrier] = {}

    # ── Carrier management ──────────────────────────────────────────

    def add_carrier(self, carrier: Carrier) -> Carrier:
        """Register a new carrier."""
        if carrier.id in self._carriers:
            raise ValueError(f"Carrier with id {carrier.id} already exists")
        self._carriers[carrier.id] = carrier
        return carrier

    def get_carrier(self, carrier_id: str) -> Optional[Carrier]:
        """Retrieve a carrier by ID."""
        return self._carriers.get(carrier_id)

    def list_carriers(self, active_only: bool = False) -> list[Carrier]:
        """List carriers, optionally filtering to active only."""
        carriers = list(self._carriers.values())
        if active_only:
            carriers = [c for c in carriers if c.is_active]
        return carriers

    # ── Shipment management ─────────────────────────────────────────

    def create_shipment(
        self,
        carrier_id: str,
        origin: str,
        destination: str,
        weight_kg: float = 0.0,
        dimensions_cm: tuple[float, float, float] = (0.0, 0.0, 0.0),
        shipping_cost: float = 0.0,
        currency: str = "USD",
    ) -> Shipment:
        """Create a new shipment."""
        shipment = Shipment(
            carrier_id=carrier_id,
            origin=origin,
            destination=destination,
            weight_kg=weight_kg,
            dimensions_cm=dimensions_cm,
            shipping_cost=shipping_cost,
            currency=currency,
        )
        self._shipments[shipment.id] = shipment
        return shipment

    def get_shipment(self, shipment_id: str) -> Optional[Shipment]:
        """Retrieve a shipment by ID."""
        return self._shipments.get(shipment_id)

    def remove_shipment(self, shipment_id: str) -> bool:
        """Remove a shipment by ID. Returns True if removed."""
        if shipment_id in self._shipments:
            del self._shipments[shipment_id]
            return True
        return False

    def list_shipments(
        self,
        status: Optional[ShipmentStatus] = None,
        carrier_id: Optional[str] = None,
    ) -> list[Shipment]:
        """List shipments with optional filtering."""
        results = list(self._shipments.values())
        if status is not None:
            results = [s for s in results if s.status == status]
        if carrier_id is not None:
            results = [s for s in results if s.carrier_id == carrier_id]
        return results

    def get_active_shipments(self) -> list[Shipment]:
        """Get all shipments that are not delivered, returned, or cancelled."""
        return [
            s
            for s in self._shipments.values()
            if s.status
            not in (
                ShipmentStatus.DELIVERED,
                ShipmentStatus.RETURNED,
                ShipmentStatus.CANCELLED,
            )
        ]

    def get_shipments_by_carrier(self, carrier_id: str) -> list[Shipment]:
        """Get all shipments for a specific carrier."""
        return [s for s in self._shipments.values() if s.carrier_id == carrier_id]

    def get_total_shipping_cost(self) -> float:
        """Calculate total shipping cost across all shipments."""
        return sum(s.shipping_cost for s in self._shipments.values())

    def count_shipments(self) -> int:
        """Return total number of shipments."""
        return len(self._shipments)

    def count_carriers(self) -> int:
        """Return total number of carriers."""
        return len(self._carriers)

    def clear(self) -> None:
        """Remove all shipments and carriers."""
        self._shipments.clear()
        self._carriers.clear()
