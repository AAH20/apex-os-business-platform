"""Deepened CQRS module: commands, queries, event bus, materialized views, metrics."""

from __future__ import annotations

import time
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

# ---------------------------------------------------------------------------
# 1. Command Handling with Validation
# ---------------------------------------------------------------------------

TCommand = TypeVar("TCommand", bound="Command")


class ValidationError(Exception):
    """Raised when command validation fails."""


@dataclass
class Command(ABC):
    """Base class for all commands."""

    command_id: str = ""
    timestamp: float = field(default_factory=time.time)

    @abstractmethod
    def validate(self) -> None:
        """Validate command invariants. Raise ValidationError on failure."""


@dataclass
class Result:
    """Result of command execution."""

    success: bool
    command_id: str
    data: Any = None
    errors: List[str] = field(default_factory=list)


class CommandHandler(ABC, Generic[TCommand]):
    """Abstract command handler."""

    @abstractmethod
    def handle(self, command: TCommand) -> Result:
        ...


class CommandBus:
    """Routes commands to their registered handlers with validation."""

    def __init__(self) -> None:
        self._handlers: Dict[type, CommandHandler] = {}
        self._middleware: List[Callable[[Command], None]] = []

    def register(self, command_type: type, handler: CommandHandler) -> None:
        self._handlers[command_type] = handler

    def add_middleware(self, mw: Callable[[Command], None]) -> None:
        self._middleware.append(mw)

    def dispatch(self, command: Command) -> Result:
        for mw in self._middleware:
            mw(command)
        try:
            command.validate()
        except ValidationError as e:
            return Result(False, command.command_id, errors=[str(e)])
        handler = self._handlers.get(type(command))
        if handler is None:
            return Result(False, command.command_id, errors=["No handler registered"])
        return handler.handle(command)


# ---------------------------------------------------------------------------
# 2. Query Handling with Read Models
# ---------------------------------------------------------------------------

TQuery = TypeVar("TQuery", bound="Query")
TResult = TypeVar("TResult")


@dataclass
class Query(ABC):
    """Base class for all queries."""

    query_id: str = ""


class QueryHandler(ABC, Generic[TQuery, TResult]):
    """Abstract query handler backed by a read model."""

    @abstractmethod
    def handle(self, query: TQuery) -> TResult:
        ...


class QueryBus:
    """Routes queries to their registered handlers."""

    def __init__(self) -> None:
        self._handlers: Dict[type, QueryHandler] = {}

    def register(self, query_type: type, handler: QueryHandler) -> None:
        self._handlers[query_type] = handler

    def execute(self, query: Query) -> Any:
        handler = self._handlers.get(type(query))
        if handler is None:
            raise RuntimeError(f"No handler for {type(query).__name__}")
        return handler.handle(query)


# ---------------------------------------------------------------------------
# 3. Event Bus with Pub/Sub
# ---------------------------------------------------------------------------

@dataclass
class DomainEvent:
    """Base domain event."""

    event_id: str = ""
    event_type: str = ""
    aggregate_id: str = ""
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)


EventHandler = Callable[[DomainEvent], None]


class EventBus:
    """In-memory pub/sub event bus."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        with self._lock:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        with self._lock:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)

    def publish(self, event: DomainEvent) -> None:
        with self._lock:
            handlers = list(self._subscribers.get(event.event_type, []))
        for h in handlers:
            h(event)

    def publish_all(self, events: List[DomainEvent]) -> None:
        for e in events:
            self.publish(e)


# ---------------------------------------------------------------------------
# 4. Materialized Views with Refresh
# ---------------------------------------------------------------------------

class MaterializedView(ABC):
    """Base class for materialized views."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._data: Dict[str, Any] = {}
        self._last_refresh: float = 0.0
        self._version: int = 0

    @property
    def last_refresh(self) -> float:
        return self._last_refresh

    @property
    def version(self) -> int:
        return self._version

    @abstractmethod
    def refresh(self, events: List[DomainEvent]) -> None:
        """Rebuild view state from events."""

    def get(self, key: str) -> Any:
        return self._data.get(key)

    def all(self) -> Dict[str, Any]:
        return dict(self._data)


class MaterializedViewRegistry:
    """Registry managing multiple materialized views."""

    def __init__(self) -> None:
        self._views: Dict[str, MaterializedView] = {}

    def register(self, view: MaterializedView) -> None:
        self._views[view.name] = view

    def get(self, name: str) -> Optional[MaterializedView]:
        return self._views.get(name)

    def refresh_all(self, events: List[DomainEvent]) -> None:
        for view in self._views.values():
            view.refresh(events)

    def refresh_one(self, name: str, events: List[DomainEvent]) -> None:
        view = self._views.get(name)
        if view:
            view.refresh(events)


# ---------------------------------------------------------------------------
# 5. CQRS Metrics with Monitoring
# ---------------------------------------------------------------------------

class MetricsCollector:
    """Collects and exposes CQRS pipeline metrics."""

    def __init__(self) -> None:
        self._command_count: int = 0
        self._command_errors: int = 0
        self._query_count: int = 0
        self._query_errors: int = 0
        self._event_count: int = 0
        self._view_refreshes: int = 0
        self._latencies: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def record_command(self, latency: float, success: bool) -> None:
        with self._lock:
            self._command_count += 1
            if not success:
                self._command_errors += 1
            self._latencies["command"].append(latency)

    def record_query(self, latency: float, success: bool) -> None:
        with self._lock:
            self._query_count += 1
            if not success:
                self._query_errors += 1
            self._latencies["query"].append(latency)

    def record_event(self) -> None:
        with self._lock:
            self._event_count += 1

    def record_view_refresh(self) -> None:
        with self._lock:
            self._view_refreshes += 1

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            lat = self._latencies
            return {
                "commands_total": self._command_count,
                "commands_failed": self._command_errors,
                "queries_total": self._query_count,
                "queries_failed": self._query_errors,
                "events_published": self._event_count,
                "view_refreshes": self._view_refreshes,
                "avg_command_latency_ms": (
                    sum(lat["command"]) / len(lat["command"]) * 1000
                    if lat["command"] else 0.0
                ),
                "avg_query_latency_ms": (
                    sum(lat["query"]) / len(lat["query"]) * 1000
                    if lat["query"] else 0.0
                ),
            }


# ---------------------------------------------------------------------------
# Integration: CQRS Runtime
# ---------------------------------------------------------------------------

class CQRSRuntime:
    """Wires command bus, query bus, event bus, views, and metrics together."""

    def __init__(self) -> None:
        self.commands = CommandBus()
        self.queries = QueryBus()
        self.events = EventBus()
        self.views = MaterializedViewRegistry()
        self.metrics = MetricsCollector()

    def dispatch(self, command: Command) -> Result:
        start = time.monotonic()
        result = self.commands.dispatch(command)
        elapsed = time.monotonic() - start
        self.metrics.record_command(elapsed, result.success)
        return result

    def execute(self, query: Query) -> Any:
        start = time.monotonic()
        try:
            result = self.queries.execute(query)
            self.metrics.record_query(time.monotonic() - start, True)
            return result
        except Exception:
            self.metrics.record_query(time.monotonic() - start, False)
            raise

    def publish(self, event: DomainEvent) -> None:
        self.events.publish(event)
        self.metrics.record_event()

    def refresh_views(self, events: List[DomainEvent]) -> None:
        self.views.refresh_all(events)
        self.metrics.record_view_refresh()
