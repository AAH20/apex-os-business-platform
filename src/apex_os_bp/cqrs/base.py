"""Base classes for the CQRS system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Generic, List, TypeVar
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Command:
    """Base class for all commands."""
    command_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Query:
    """Base class for all queries."""
    query_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class Event:
    """Base class for all events."""
    event_id: UUID = field(default_factory=uuid4)
    aggregate_id: UUID = field(default_factory=uuid4)
    event_type: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


TCommand = TypeVar("TCommand", bound=Command)
TQuery = TypeVar("TQuery", bound=Query)
TResult = TypeVar("TResult")
TEvent = TypeVar("TEvent", bound=Event)


class CommandHandler(ABC, Generic[TCommand]):
    """Base class for command handlers."""

    @abstractmethod
    async def handle(self, command: TCommand) -> List[Event]:
        """Handle a command and return a list of events."""


class QueryHandler(ABC, Generic[TQuery, TResult]):
    """Base class for query handlers."""

    @abstractmethod
    async def handle(self, query: TQuery) -> TResult:
        """Handle a query and return a result."""


class EventHandler(ABC, Generic[TEvent]):
    """Base class for event handlers."""

    @abstractmethod
    async def handle(self, event: TEvent) -> None:
        """Handle an event."""


class ReadModel(ABC):
    """Base class for read models."""

    @abstractmethod
    def project(self, event: Event) -> None:
        """Project an event into the read model."""


class WriteModel(ABC):
    """Base class for write models (aggregate roots)."""

    @abstractmethod
    def apply(self, event: Event) -> None:
        """Apply an event to the write model."""

    @abstractmethod
    def uncommitted_events(self) -> List[Event]:
        """Return uncommitted events."""

    @abstractmethod
    def mark_committed(self) -> None:
        """Mark all uncommitted events as committed."""
