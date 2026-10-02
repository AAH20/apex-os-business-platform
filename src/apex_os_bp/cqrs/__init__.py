"""CQRS system for APEX-OS Business Platform.

This module provides a comprehensive CQRS (Command Query Responsibility Segregation)
implementation with:
- Command handlers for write operations
- Query handlers for read operations
- Read models for query-side data
- Write models (aggregate roots) for command-side data
- Event handlers for event-driven updates
- Event store for persistence
- Repository for aggregate root management
- CQRS bus for dispatching
"""

from apex_os_bp.cqrs.base import (
    Command,
    CommandHandler,
    Event,
    EventHandler,
    Query,
    QueryHandler,
    ReadModel,
    WriteModel,
)
from apex_os_bp.cqrs.bus import CQRSBus
from apex_os_bp.cqrs.commands import (
    CancelOrderCommand,
    CreateCustomerCommand,
    CreateOrderCommand,
    CreateProductCommand,
    UpdateCustomerCommand,
    UpdateOrderCommand,
    UpdateProductCommand,
)
from apex_os_bp.cqrs.event_handlers import (
    CustomerCreatedHandler,
    CustomerUpdatedHandler,
    OrderCancelledHandler,
    OrderCreatedHandler,
    OrderUpdatedHandler,
    ProductCreatedHandler,
    ProductUpdatedHandler,
)
from apex_os_bp.cqrs.event_store import InMemoryEventStore
from apex_os_bp.cqrs.events import (
    CustomerCreatedEvent,
    CustomerUpdatedEvent,
    OrderCancelledEvent,
    OrderCreatedEvent,
    OrderUpdatedEvent,
    ProductCreatedEvent,
    ProductUpdatedEvent,
)
from apex_os_bp.cqrs.exceptions import (
    AggregateNotFoundError,
    CommandValidationError,
    ConcurrencyError,
    CQRSException,
    EventStoreError,
    EventValidationError,
    HandlerNotFoundError,
    QueryValidationError,
)
from apex_os_bp.cqrs.query_handlers import (
    GetCustomerHandler,
    GetOrderHandler,
    GetProductHandler,
    ListCustomersHandler,
    ListOrdersHandler,
    ListProductsHandler,
)
from apex_os_bp.cqrs.queries import (
    GetCustomerQuery,
    GetOrderQuery,
    GetProductQuery,
    ListCustomersQuery,
    ListOrdersQuery,
    ListProductsQuery,
)
from apex_os_bp.cqrs.command_handlers import (
    CancelOrderHandler,
    CreateCustomerHandler,
    CreateOrderHandler,
    CreateProductHandler,
    UpdateCustomerHandler,
    UpdateOrderHandler,
    UpdateProductHandler,
)
from apex_os_bp.cqrs.query_handlers import (
    GetCustomerHandler,
    GetOrderHandler,
    GetProductHandler,
    ListCustomersHandler,
    ListOrdersHandler,
    ListProductsHandler,
)
from apex_os_bp.cqrs.read_models import (
    CustomerReadModel,
    OrderReadModel,
    ProductReadModel,
)
from apex_os_bp.cqrs.repository import Repository
from apex_os_bp.cqrs.write_models import (
    CustomerAggregate,
    OrderAggregate,
    ProductAggregate,
)

__all__ = [
    # Base
    "Command",
    "CommandHandler",
    "Event",
    "EventHandler",
    "Query",
    "QueryHandler",
    "ReadModel",
    "WriteModel",
    # Bus
    "CQRSBus",
    # Commands
    "CancelOrderCommand",
    "CreateCustomerCommand",
    "CreateOrderCommand",
    "CreateProductCommand",
    "UpdateCustomerCommand",
    "UpdateOrderCommand",
    "UpdateProductCommand",
    # Events
    "CustomerCreatedEvent",
    "CustomerUpdatedEvent",
    "OrderCancelledEvent",
    "OrderCreatedEvent",
    "OrderUpdatedEvent",
    "ProductCreatedEvent",
    "ProductUpdatedEvent",
    # Exceptions
    "AggregateNotFoundError",
    "CommandValidationError",
    "ConcurrencyError",
    "CQRSException",
    "EventStoreError",
    "EventValidationError",
    "HandlerNotFoundError",
    "QueryValidationError",
    # Queries
    "GetCustomerQuery",
    "GetOrderQuery",
    "GetProductQuery",
    "ListCustomersQuery",
    "ListOrdersQuery",
    "ListProductsQuery",
    # Command Handlers
    "CancelOrderHandler",
    "CreateCustomerHandler",
    "CreateOrderHandler",
    "CreateProductHandler",
    "UpdateCustomerHandler",
    "UpdateOrderHandler",
    "UpdateProductHandler",
    # Query Handlers
    "GetCustomerHandler",
    "GetOrderHandler",
    "GetProductHandler",
    "ListCustomersHandler",
    "ListOrdersHandler",
    "ListProductsHandler",
    # Read Models
    "OrderReadModel",
    "CustomerReadModel",
    "ProductReadModel",
    # Write Models
    "OrderAggregate",
    "CustomerAggregate",
    "ProductAggregate",
    # Event Handlers
    "OrderCreatedHandler",
    "OrderUpdatedHandler",
    "OrderCancelledHandler",
    "CustomerCreatedHandler",
    "CustomerUpdatedHandler",
    "ProductCreatedHandler",
    "ProductUpdatedHandler",
    # Event Store
    "InMemoryEventStore",
    # Repository
    "Repository",
]
