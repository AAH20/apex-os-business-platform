"""Command definitions for the CQRS system."""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from apex_os_bp.cqrs.base import Command


@dataclass(frozen=True)
class CreateOrderCommand(Command):
    """Command to create a new order."""
    customer_id: UUID = UUID(int=0)
    items: List[dict] = None
    currency: str = "USD"
    notes: Optional[str] = None


@dataclass(frozen=True)
class UpdateOrderCommand(Command):
    """Command to update an existing order."""
    order_id: UUID = UUID(int=0)
    items: Optional[List[dict]] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class CancelOrderCommand(Command):
    """Command to cancel an order."""
    order_id: UUID = UUID(int=0)
    reason: str = ""


@dataclass(frozen=True)
class CreateCustomerCommand(Command):
    """Command to create a new customer."""
    name: str = ""
    email: str = ""
    phone: Optional[str] = None
    address: Optional[str] = None


@dataclass(frozen=True)
class UpdateCustomerCommand(Command):
    """Command to update an existing customer."""
    customer_id: UUID = UUID(int=0)
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


@dataclass(frozen=True)
class CreateProductCommand(Command):
    """Command to create a new product."""
    name: str = ""
    description: str = ""
    price: Decimal = Decimal("0.00")
    sku: str = ""
    category: Optional[str] = None


@dataclass(frozen=True)
class UpdateProductCommand(Command):
    """Command to update an existing product."""
    product_id: UUID = UUID(int=0)
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    category: Optional[str] = None
