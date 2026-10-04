"""CQRS bus for dispatching commands, queries, and events."""

from typing import Any, Dict, List, Type

from apex_os_bp.cqrs.base import Command, CommandHandler, Event, EventHandler, Query, QueryHandler
from apex_os_bp.cqrs.exceptions import HandlerNotFoundError


class CQRSBus:
    """Central bus for dispatching commands, queries, and events."""

    def __init__(self):
        self._command_handlers: Dict[Type[Command], CommandHandler] = {}
        self._query_handlers: Dict[Type[Query], QueryHandler] = {}
        self._event_handlers: Dict[Type[Event], List[EventHandler]] = {}

    def register_command_handler(
        self, command_type: Type[Command], handler: CommandHandler
    ) -> None:
        """Register a command handler."""
        self._command_handlers[command_type] = handler

    def register_query_handler(
        self, query_type: Type[Query], handler: QueryHandler
    ) -> None:
        """Register a query handler."""
        self._query_handlers[query_type] = handler

    def register_event_handler(
        self, event_type: Type[Event], handler: EventHandler
    ) -> None:
        """Register an event handler."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def send(self, command: Command) -> List[Event]:
        """Send a command to its handler."""
        handler = self._command_handlers.get(type(command))
        if not handler:
            raise HandlerNotFoundError(
                f"No handler registered for {type(command).__name__}"
            )
        return await handler.handle(command)

    async def query(self, query: Query) -> Any:
        """Send a query to its handler."""
        handler = self._query_handlers.get(type(query))
        if not handler:
            raise HandlerNotFoundError(
                f"No handler registered for {type(query).__name__}"
            )
        return await handler.handle(query)

    async def publish(self, event: Event) -> None:
        """Publish an event to all registered handlers."""
        handlers = self._event_handlers.get(type(event), [])
        for handler in handlers:
            await handler.handle(event)

    async def publish_all(self, events: List[Event]) -> None:
        """Publish multiple events."""
        for event in events:
            await self.publish(event)
