"""Event Routing — route events to handlers based on type, filters, and priority."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Optional


class EventPriority(int, Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class EventStatus(str, Enum):
    PENDING = "pending"
    ROUTED = "routed"
    HANDLED = "handled"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


@dataclass
class Event:
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = "unknown"
    priority: EventPriority = EventPriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    routing_history: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "priority": self.priority.name,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "payload": self.payload,
            "metadata": self.metadata,
        }


@dataclass
class Route:
    name: str
    event_type: str
    handler: Callable[[Event], Awaitable[Any]]
    filter_fn: Optional[Callable[[Event], bool]] = None
    priority: int = 0
    enabled: bool = True
    timeout: float = 30.0
    description: str = ""

    def matches(self, event: Event) -> bool:
        if not self.enabled:
            return False
        if self.event_type != "*" and self.event_type != event.event_type:
            return False
        if self.filter_fn and not self.filter_fn(event):
            return False
        return True


@dataclass
class RouteResult:
    route_name: str
    event_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)


class EventRouter:
    """Route events to registered handlers with filtering and priority."""

    def __init__(self, name: str = "default"):
        self.name = name
        self._routes: dict[str, Route] = {}
        self._middleware: list[Callable[[Event], Awaitable[Event]]] = []
        self._history: list[RouteResult] = []
        self._max_history: int = 1000
        self._dead_letter: list[Event] = []

    def register_route(self, route: Route) -> None:
        self._routes[route.name] = route

    def unregister_route(self, name: str) -> None:
        self._routes.pop(name, None)

    def get_route(self, name: str) -> Optional[Route]:
        return self._routes.get(name)

    @property
    def routes(self) -> dict[str, Route]:
        return dict(self._routes)

    def add_middleware(self, fn: Callable[[Event], Awaitable[Event]]) -> None:
        self._middleware.append(fn)

    def remove_middleware(self, fn: Callable[[Event], Awaitable[Event]]) -> None:
        if fn in self._middleware:
            self._middleware.remove(fn)

    def _get_matching_routes(self, event: Event) -> list[Route]:
        matching = [r for r in self._routes.values() if r.matches(event)]
        return sorted(matching, key=lambda r: r.priority, reverse=True)

    async def _apply_middleware(self, event: Event) -> Event:
        for mw in self._middleware:
            event = await mw(event)
        return event

    async def _execute_route(self, route: Route, event: Event) -> RouteResult:
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(route.handler(event), timeout=route.timeout)
            return RouteResult(
                route_name=route.name,
                event_id=event.event_id,
                success=True,
                result=result,
                duration=time.monotonic() - start,
            )
        except asyncio.TimeoutError:
            return RouteResult(
                route_name=route.name,
                event_id=event.event_id,
                success=False,
                error=f"Timeout after {route.timeout}s",
                duration=time.monotonic() - start,
            )
        except Exception as exc:
            return RouteResult(
                route_name=route.name,
                event_id=event.event_id,
                success=False,
                error=str(exc),
                duration=time.monotonic() - start,
            )

    async def route(self, event: Event) -> list[RouteResult]:
        """Route an event to all matching handlers."""
        event = await self._apply_middleware(event)
        matching = self._get_matching_routes(event)

        if not matching:
            event.status = EventStatus.DEAD_LETTER
            self._dead_letter.append(event)
            return []

        results: list[RouteResult] = []
        for route in matching:
            event.routing_history.append(route.name)
            result = await self._execute_route(route, event)
            results.append(result)

            if result.success:
                event.status = EventStatus.HANDLED
            else:
                event.retry_count += 1
                if event.retry_count >= event.max_retries:
                    event.status = EventStatus.DEAD_LETTER
                    self._dead_letter.append(event)
                else:
                    event.status = EventStatus.RETRYING

        self._history.extend(results)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return results

    async def emit(self, event_type: str, payload: dict[str, Any], **kwargs) -> list[RouteResult]:
        """Create and route a new event."""
        event = Event(event_type=event_type, payload=payload, **kwargs)
        return await self.route(event)

    def get_history(self, limit: int = 100) -> list[RouteResult]:
        return self._history[-limit:]

    def get_dead_letter(self) -> list[Event]:
        return list(self._dead_letter)

    def clear_dead_letter(self) -> None:
        self._dead_letter.clear()

    def clear_history(self) -> None:
        self._history.clear()

    def get_route_stats(self) -> dict[str, dict]:
        """Get statistics for each route."""
        stats: dict[str, dict] = {}
        for result in self._history:
            name = result.route_name
            if name not in stats:
                stats[name] = {"total": 0, "success": 0, "failed": 0, "avg_duration": 0.0}
            stats[name]["total"] += 1
            if result.success:
                stats[name]["success"] += 1
            else:
                stats[name]["failed"] += 1
            stats[name]["avg_duration"] = (
                (stats[name]["avg_duration"] * (stats[name]["total"] - 1) + result.duration)
                / stats[name]["total"]
            )
        return stats
