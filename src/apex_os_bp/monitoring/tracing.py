"""Distributed tracing for APEX-OS.

Provides span creation, trace context propagation, and span
export for distributed tracing across services.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class SpanKind(Enum):
    """The kind of a span."""

    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class TraceStatus(Enum):
    """The status of a span."""

    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanContext:
    """Context for propagating trace state across service boundaries."""

    trace_id: str
    span_id: str
    trace_flags: int = 1
    trace_state: Dict[str, str] = field(default_factory=dict)

    def to_headers(self) -> Dict[str, str]:
        """Convert context to HTTP headers for propagation."""
        return {
            "X-Trace-ID": self.trace_id,
            "X-Span-ID": self.span_id,
            "X-Trace-Flags": str(self.trace_flags),
        }

    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> Optional["SpanContext"]:
        """Create context from HTTP headers."""
        trace_id = headers.get("X-Trace-ID")
        span_id = headers.get("X-Span-ID")
        if not trace_id or not span_id:
            return None
        return cls(
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=int(headers.get("X-Trace-Flags", "1")),
        )


@dataclass
class SpanEvent:
    """An event within a span."""

    name: str
    timestamp: float
    attributes: Dict[str, Any] = field(default_factory=dict)


class Span:
    """A single operation within a trace."""

    def __init__(
        self,
        name: str,
        trace_id: str,
        span_id: str,
        parent_span_id: Optional[str] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.kind = kind
        self.attributes: Dict[str, Any] = attributes or {}
        self.events: List[SpanEvent] = []
        self.status = TraceStatus.UNSET
        self.start_time = time.perf_counter()
        self.end_time: Optional[float] = None
        self._lock = threading.RLock()

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the span."""
        with self._lock:
            self.attributes[key] = value

    def set_attributes(self, attributes: Dict[str, Any]) -> None:
        """Set multiple attributes on the span."""
        with self._lock:
            self.attributes.update(attributes)

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the span."""
        with self._lock:
            self.events.append(
                SpanEvent(
                    name=name,
                    timestamp=time.perf_counter(),
                    attributes=attributes or {},
                )
            )

    def set_status(self, status: TraceStatus, description: str = "") -> None:
        """Set the status of the span."""
        with self._lock:
            self.status = status
            if description:
                self.attributes["status.description"] = description

    def record_exception(self, exception: Exception) -> None:
        """Record an exception on the span."""
        with self._lock:
            self.set_status(TraceStatus.ERROR, str(exception))
            self.add_event(
                "exception",
                {
                    "exception.type": type(exception).__name__,
                    "exception.message": str(exception),
                },
            )

    def end(self) -> None:
        """End the span."""
        with self._lock:
            if self.end_time is None:
                self.end_time = time.perf_counter()

    @property
    def duration(self) -> Optional[float]:
        """Get the span duration in seconds."""
        if self.end_time is not None:
            return self.end_time - self.start_time
        return None

    @property
    def duration_ms(self) -> Optional[float]:
        """Get the span duration in milliseconds."""
        d = self.duration
        return d * 1000.0 if d is not None else None

    def get_context(self) -> SpanContext:
        """Get the span context for propagation."""
        return SpanContext(trace_id=self.trace_id, span_id=self.span_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "kind": self.kind.value,
            "attributes": dict(self.attributes),
            "events": [
                {
                    "name": e.name,
                    "timestamp": e.timestamp,
                    "attributes": e.attributes,
                }
                for e in self.events
            ],
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.record_exception(exc_val)
        self.end()
        return False


class Tracer:
    """Creates and manages spans for distributed tracing."""

    def __init__(self, service_name: str = "apex-os"):
        self.service_name = service_name
        self._spans: Dict[str, List[Span]] = {}
        self._exporters: List[Callable[[Span], None]] = []
        self._lock = threading.Lock()
        self._active_spans: Dict[int, Span] = {}

    def start_span(
        self,
        name: str,
        parent_context: Optional[SpanContext] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Start a new span."""
        if parent_context:
            trace_id = parent_context.trace_id
            parent_span_id = parent_context.span_id
        else:
            trace_id = self._generate_trace_id()
            parent_span_id = None

        span = Span(
            name=name,
            trace_id=trace_id,
            span_id=self._generate_span_id(),
            parent_span_id=parent_span_id,
            kind=kind,
            attributes=attributes,
        )
        span.set_attribute("service.name", self.service_name)

        with self._lock:
            if trace_id not in self._spans:
                self._spans[trace_id] = []
            self._spans[trace_id].append(span)

        return span

    def start_as_current_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Start a span and set it as the current active span."""
        span = self.start_span(name, kind=kind, attributes=attributes)
        thread_id = threading.get_ident()
        self._active_spans[thread_id] = span
        return span

    def end_span(self, span: Span) -> None:
        """End a span and export it."""
        span.end()
        thread_id = threading.get_ident()
        if thread_id in self._active_spans and self._active_spans[thread_id] is span:
            del self._active_spans[thread_id]
        for exporter in self._exporters:
            try:
                exporter(span)
            except Exception:
                pass

    def get_current_span(self) -> Optional[Span]:
        """Get the current active span for this thread."""
        return self._active_spans.get(threading.get_ident())

    def get_trace(self, trace_id: str) -> List[Span]:
        """Get all spans for a given trace ID."""
        with self._lock:
            return list(self._spans.get(trace_id, []))

    def get_traces(self) -> Dict[str, List[Span]]:
        """Get all traces."""
        with self._lock:
            return {k: list(v) for k, v in self._spans.items()}

    def add_exporter(self, exporter: Callable[[Span], None]) -> None:
        """Add a span exporter."""
        self._exporters.append(exporter)

    def remove_exporter(self, exporter: Callable[[Span], None]) -> None:
        """Remove a span exporter."""
        if exporter in self._exporters:
            self._exporters.remove(exporter)

    def inject_context(self, context: SpanContext, headers: Dict[str, str]) -> None:
        """Inject trace context into HTTP headers."""
        headers.update(context.to_headers())

    def extract_context(self, headers: Dict[str, str]) -> Optional[SpanContext]:
        """Extract trace context from HTTP headers."""
        return SpanContext.from_headers(headers)

    def clear(self) -> None:
        """Clear all traces."""
        with self._lock:
            self._spans.clear()
            self._active_spans.clear()

    @staticmethod
    def _generate_trace_id() -> str:
        """Generate a unique trace ID."""
        return uuid.uuid4().hex

    @staticmethod
    def _generate_span_id() -> str:
        """Generate a unique span ID."""
        return uuid.uuid4().hex[:16]
