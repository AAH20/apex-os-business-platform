"""Query definitions for the CQRS system."""

from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

from apex_os_bp.cqrs.base import Query


@dataclass(frozen=True)
class GetOrderQuery(Query):
    """Query to get a single order by ID."""
    order_id: UUID = UUID(int=0)


@dataclass(frozen=True)
class ListOrdersQuery(Query):
    """Query to list orders with optional filtering."""
    customer_id: Optional[UUID] = None
    status: Optional[str] = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class GetCustomerQuery(Query):
    """Query to get a single customer by ID."""
    customer_id: UUID = UUID(int=0)


@dataclass(frozen=True)
class ListCustomersQuery(Query):
    """Query to list customers with optional filtering."""
    search: Optional[str] = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class GetProductQuery(Query):
    """Query to get a single product by ID."""
    product_id: UUID = UUID(int=0)


@dataclass(frozen=True)
class ListProductsQuery(Query):
    """Query to list products with optional filtering."""
    category: Optional[str] = None
    search: Optional[str] = None
    limit: int = 50
    offset: int = 0
