"""Command handlers for the CQRS system."""

from typing import List
from uuid import UUID

from apex_os_bp.cqrs.base import CommandHandler, Event
from apex_os_bp.cqrs.commands import (
    CancelOrderCommand,
    CreateCustomerCommand,
    CreateOrderCommand,
    CreateProductCommand,
    UpdateCustomerCommand,
    UpdateOrderCommand,
    UpdateProductCommand,
)
from apex_os_bp.cqrs.events import (
    CustomerCreatedEvent,
    CustomerUpdatedEvent,
    OrderCancelledEvent,
    OrderCreatedEvent,
    OrderUpdatedEvent,
    ProductCreatedEvent,
    ProductUpdatedEvent,
)
from apex_os_bp.cqrs.exceptions import CommandValidationError


class CreateOrderHandler(CommandHandler[CreateOrderCommand]):
    """Handler for CreateOrderCommand."""

    async def handle(self, command: CreateOrderCommand) -> List[Event]:
        if command.customer_id == UUID(int=0):
            raise CommandValidationError("customer_id is required")
        if not command.items:
            raise CommandValidationError("items are required")
        if not command.currency:
            raise CommandValidationError("currency is required")

        return [
            OrderCreatedEvent(
                aggregate_id=command.command_id,
                event_type="OrderCreated",
                metadata={
                    "customer_id": str(command.customer_id),
                    "items": command.items,
                    "currency": command.currency,
                    "notes": command.notes,
                },
            )
        ]


class UpdateOrderHandler(CommandHandler[UpdateOrderCommand]):
    """Handler for UpdateOrderCommand."""

    async def handle(self, command: UpdateOrderCommand) -> List[Event]:
        if command.order_id == UUID(int=0):
            raise CommandValidationError("order_id is required")

        return [
            OrderUpdatedEvent(
                aggregate_id=command.order_id,
                event_type="OrderUpdated",
                metadata={
                    "items": command.items,
                    "notes": command.notes,
                },
            )
        ]


class CancelOrderHandler(CommandHandler[CancelOrderCommand]):
    """Handler for CancelOrderCommand."""

    async def handle(self, command: CancelOrderCommand) -> List[Event]:
        if command.order_id == UUID(int=0):
            raise CommandValidationError("order_id is required")
        if not command.reason:
            raise CommandValidationError("reason is required")

        return [
            OrderCancelledEvent(
                aggregate_id=command.order_id,
                event_type="OrderCancelled",
                metadata={"reason": command.reason},
            )
        ]


class CreateCustomerHandler(CommandHandler[CreateCustomerCommand]):
    """Handler for CreateCustomerCommand."""

    async def handle(self, command: CreateCustomerCommand) -> List[Event]:
        if not command.name:
            raise CommandValidationError("name is required")
        if not command.email:
            raise CommandValidationError("email is required")

        return [
            CustomerCreatedEvent(
                aggregate_id=command.command_id,
                event_type="CustomerCreated",
                metadata={
                    "name": command.name,
                    "email": command.email,
                    "phone": command.phone,
                    "address": command.address,
                },
            )
        ]


class UpdateCustomerHandler(CommandHandler[UpdateCustomerCommand]):
    """Handler for UpdateCustomerCommand."""

    async def handle(self, command: UpdateCustomerCommand) -> List[Event]:
        if command.customer_id == UUID(int=0):
            raise CommandValidationError("customer_id is required")

        return [
            CustomerUpdatedEvent(
                aggregate_id=command.customer_id,
                event_type="CustomerUpdated",
                metadata={
                    "name": command.name,
                    "email": command.email,
                    "phone": command.phone,
                    "address": command.address,
                },
            )
        ]


class CreateProductHandler(CommandHandler[CreateProductCommand]):
    """Handler for CreateProductCommand."""

    async def handle(self, command: CreateProductCommand) -> List[Event]:
        if not command.name:
            raise CommandValidationError("name is required")
        if not command.sku:
            raise CommandValidationError("sku is required")
        if command.price < 0:
            raise CommandValidationError("price must be non-negative")

        return [
            ProductCreatedEvent(
                aggregate_id=command.command_id,
                event_type="ProductCreated",
                metadata={
                    "name": command.name,
                    "description": command.description,
                    "price": str(command.price),
                    "sku": command.sku,
                    "category": command.category,
                },
            )
        ]


class UpdateProductHandler(CommandHandler[UpdateProductCommand]):
    """Handler for UpdateProductCommand."""

    async def handle(self, command: UpdateProductCommand) -> List[Event]:
        if command.product_id == UUID(int=0):
            raise CommandValidationError("product_id is required")

        return [
            ProductUpdatedEvent(
                aggregate_id=command.product_id,
                event_type="ProductUpdated",
                metadata={
                    "name": command.name,
                    "description": command.description,
                    "price": str(command.price) if command.price else None,
                    "category": command.category,
                },
            )
        ]
