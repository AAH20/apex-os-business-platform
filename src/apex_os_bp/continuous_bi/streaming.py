"""Streaming ETL with windowing support."""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class WindowType(Enum):
    TUMBLING = "tumbling"
    SLIDING = "sliding"


@dataclass
class StreamEvent:
    timestamp: float
    data: dict[str, Any]


@dataclass
class Window:
    start: float
    end: float
    events: list[StreamEvent] = field(default_factory=list)


class WindowOperator:
    """Maintains a time-based window over a stream of events."""

    def __init__(
        self,
        window_type: WindowType,
        size_seconds: float,
        slide_seconds: Optional[float] = None,
    ):
        self.window_type = window_type
        self.size_seconds = size_seconds
        self.slide_seconds = slide_seconds or size_seconds
        self._events: deque[StreamEvent] = deque()
        self._lock = threading.Lock()

    def add_event(self, event: StreamEvent):
        with self._lock:
            self._events.append(event)
            cutoff = event.timestamp - self.size_seconds
            while self._events and self._events[0].timestamp < cutoff:
                self._events.popleft()

    def get_window(self) -> Window:
        with self._lock:
            now = time.time()
            start = now - self.size_seconds
            events = [e for e in self._events if e.timestamp >= start]
            return Window(start=start, end=now, events=events)

    def aggregate(self, agg_func: Callable[[list[StreamEvent]], Any]) -> Any:
        window = self.get_window()
        return agg_func(window.events)


class StreamingETL:
    """Coordinates multiple window operators and sinks."""

    def __init__(self):
        self._operators: dict[str, WindowOperator] = {}
        self._sinks: list[Callable] = []
        self._running = False

    def add_operator(self, name: str, operator: WindowOperator):
        self._operators[name] = operator

    def add_sink(self, sink: Callable):
        self._sinks.append(sink)

    def process_event(self, operator_name: str, event: StreamEvent):
        if operator_name in self._operators:
            self._operators[operator_name].add_event(event)

    def start(self):
        self._running = True

    def stop(self):
        self._running = False
