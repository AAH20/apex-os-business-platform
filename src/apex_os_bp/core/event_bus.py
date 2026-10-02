"""Event bus for APEX-OS Business Platform."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Event data structure."""
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


EventHandler = Callable[[Event], None]


class EventBus:
    """In-process event bus with pub/sub pattern."""

    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._history: List[Event] = []
        self._max_history = 10000

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe handler to event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe handler from event type."""
        if event_type in self._handlers:
            self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]

    def publish(self, event: Event) -> None:
        """Publish event to all subscribers."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        handlers = []
        if event.type in self._handlers:
            handlers.extend(self._handlers[event.type])
        if "*" in self._handlers:
            handlers.extend(self._handlers["*"])

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error for {event.type}: {e}")

    def get_history(self, event_type: Optional[str] = None) -> List[Event]:
        """Get event history, optionally filtered by type."""
        if event_type:
            return [e for e in self._history if e.type == event_type]
        return list(self._history)

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()
