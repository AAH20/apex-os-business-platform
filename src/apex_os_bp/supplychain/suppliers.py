"""Supplier management module.

Handles supplier onboarding, qualification, performance tracking,
and tier classification.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class SupplierStatus(str, Enum):
    """Lifecycle status of a supplier."""

    PROSPECT = "prospect"
    APPROVED = "approved"
    PREFERRED = "preferred"
    SUSPENDED = "suspended"
    BLACKLISTED = "blacklisted"


class SupplierTier(str, Enum):
    """Performance tier assigned to a supplier."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


@dataclass
class Supplier:
    """Represents a supplier in the supply chain.

    Attributes:
        name: Legal name of the supplier.
        contact_email: Primary contact email.
        contact_phone: Primary contact phone.
        address: Physical address.
        country_code: ISO 3166-1 alpha-2 country code.
        status: Current lifecycle status.
        tier: Performance tier.
        rating: Quality rating from 0.0 to 5.0.
        lead_time_days: Average lead time in days.
        payment_terms: Payment terms (e.g., "Net 30").
        notes: Free-form notes.
        id: Unique identifier.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    name: str
    contact_email: str
    contact_phone: str = ""
    address: str = ""
    country_code: str = ""
    status: SupplierStatus = SupplierStatus.PROSPECT
    tier: SupplierTier = SupplierTier.BRONZE
    rating: float = 0.0
    lead_time_days: int = 0
    payment_terms: str = "Net 30"
    notes: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Supplier name cannot be empty")
        if not self.contact_email or "@" not in self.contact_email:
            raise ValueError("Supplier contact email must be valid")
        if not 0.0 <= self.rating <= 5.0:
            raise ValueError("Rating must be between 0.0 and 5.0")
        if self.lead_time_days < 0:
            raise ValueError("Lead time days cannot be negative")

    def approve(self) -> None:
        """Transition supplier to APPROVED status."""
        if self.status == SupplierStatus.BLACKLISTED:
            raise ValueError("Cannot approve a blacklisted supplier")
        self.status = SupplierStatus.APPROVED
        self.updated_at = datetime.utcnow()

    def suspend(self, reason: str = "") -> None:
        """Suspend the supplier."""
        if self.status == SupplierStatus.BLACKLISTED:
            raise ValueError("Cannot suspend a blacklisted supplier")
        self.status = SupplierStatus.SUSPENDED
        if reason:
            self.notes = f"{self.notes}\nSuspended: {reason}".strip()
        self.updated_at = datetime.utcnow()

    def blacklist(self, reason: str = "") -> None:
        """Blacklist the supplier permanently."""
        self.status = SupplierStatus.BLACKLISTED
        if reason:
            self.notes = f"{self.notes}\nBlacklisted: {reason}".strip()
        self.updated_at = datetime.utcnow()

    def update_rating(self, new_rating: float) -> None:
        """Update the supplier quality rating."""
        if not 0.0 <= new_rating <= 5.0:
            raise ValueError("Rating must be between 0.0 and 5.0")
        self.rating = new_rating
        self.updated_at = datetime.utcnow()
        # Auto-promote tier based on rating
        if new_rating >= 4.5:
            self.tier = SupplierTier.PLATINUM
        elif new_rating >= 4.0:
            self.tier = SupplierTier.GOLD
        elif new_rating >= 3.0:
            self.tier = SupplierTier.SILVER
        else:
            self.tier = SupplierTier.BRONZE

    def update_lead_time(self, days: int) -> None:
        """Update the average lead time."""
        if days < 0:
            raise ValueError("Lead time days cannot be negative")
        self.lead_time_days = days
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Serialize supplier to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "address": self.address,
            "country_code": self.country_code,
            "status": self.status.value,
            "tier": self.tier.value,
            "rating": self.rating,
            "lead_time_days": self.lead_time_days,
            "payment_terms": self.payment_terms,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class SupplierManager:
    """Manages a collection of suppliers."""

    def __init__(self) -> None:
        self._suppliers: dict[str, Supplier] = {}

    def add_supplier(self, supplier: Supplier) -> Supplier:
        """Register a new supplier."""
        if supplier.id in self._suppliers:
            raise ValueError(f"Supplier with id {supplier.id} already exists")
        self._suppliers[supplier.id] = supplier
        return supplier

    def get_supplier(self, supplier_id: str) -> Optional[Supplier]:
        """Retrieve a supplier by ID."""
        return self._suppliers.get(supplier_id)

    def get_supplier_by_email(self, email: str) -> Optional[Supplier]:
        """Find a supplier by contact email."""
        for supplier in self._suppliers.values():
            if supplier.contact_email == email:
                return supplier
        return None

    def remove_supplier(self, supplier_id: str) -> bool:
        """Remove a supplier by ID. Returns True if removed."""
        if supplier_id in self._suppliers:
            del self._suppliers[supplier_id]
            return True
        return False

    def list_suppliers(
        self,
        status: Optional[SupplierStatus] = None,
        tier: Optional[SupplierTier] = None,
        country_code: Optional[str] = None,
    ) -> list[Supplier]:
        """List suppliers with optional filtering."""
        results = list(self._suppliers.values())
        if status is not None:
            results = [s for s in results if s.status == status]
        if tier is not None:
            results = [s for s in results if s.tier == tier]
        if country_code is not None:
            results = [s for s in results if s.country_code == country_code]
        return results

    def get_approved_suppliers(self) -> list[Supplier]:
        """Get all approved or preferred suppliers."""
        return [
            s
            for s in self._suppliers.values()
            if s.status in (SupplierStatus.APPROVED, SupplierStatus.PREFERRED)
        ]

    def get_top_rated(self, limit: int = 5) -> list[Supplier]:
        """Get top-rated suppliers sorted by rating descending."""
        sorted_suppliers = sorted(
            self._suppliers.values(), key=lambda s: s.rating, reverse=True
        )
        return sorted_suppliers[:limit]

    def count(self) -> int:
        """Return total number of suppliers."""
        return len(self._suppliers)

    def clear(self) -> None:
        """Remove all suppliers."""
        self._suppliers.clear()
