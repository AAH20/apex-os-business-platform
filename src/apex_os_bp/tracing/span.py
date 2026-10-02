"""Span management for APEX-OS Business Platform tracing system.

Spans represent individual operations within a trace. Each span has:
- A unique span ID and trace ID
- Parent span ID for building trace trees
- Timing information (start, end, duration)
- Kind (client, server, internal, producer, consumer)
- Status (ok, error, unset)
- Attributes, events, and links
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SpanKind(Enum):
    """Type of span based on its role in the system."""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(Enum):
    """Status of a span execution."""
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanContext:
    """Immutable context identifying a span within a trace."""
    trace_id: str
    span_id: str
    trace_flags: int = 1
    trace_state: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "trace_flags": self.trace_flags,
            "trace_state": dict(self.trace_state),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SpanContext:
        return cls(
            trace_id=data["trace_id"],
            span_id=data["span_id"],
            trace_flags=data.get("trace_flags", 1),
            trace_state=data.get("trace_state", {}),
        )


@dataclass
class SpanEvent:
    """Timestamped event within a span."""
    name: str
    timestamp: float
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanLink:
    """Link to another span context."""
    context: SpanContext
    attributes: Dict[str, Any] = field(default_factory=dict)


class Span:
    """A single operation within a trace.

    Spans form a tree structure via parent_span_id. They record
    timing, metadata, and status for observability.
    """

    def __init__(
        self,
        name: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        trace_state: Optional[Dict[str, str]] = None,
    ):
        self._trace_id = trace_id or self._generate_id()
        self._span_id = span_id or self._generate_id()
        self._parent_span_id = parent_span_id
        self._name = name
        self._kind = kind
        self._attributes: Dict[str, Any] = dict(attributes) if attributes else {}
        self._events: List[SpanEvent] = []
        self._links: List[SpanLink] = []
        self._status = SpanStatus.UNSET
        self._status_message: Optional[str] = None
        self._start_time: float = time.time()
        self._end_time: Optional[float] = None
        self._trace_state: Dict[str, str] = dict(trace_state) if trace_state else {}

    @staticmethod
    def _generate_id() -> str:
        """Generate a unique 16-character hex ID."""
        return uuid.uuid4().hex[:16]

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def trace_id(self) -> str:
        return self._trace_id

    @property
    def span_id(self) -> str:
        return self._span_id

    @property
    def parent_span_id(self) -> Optional[str]:
        return self._parent_span_id

    @property
    def kind(self) -> SpanKind:
        return self._kind

    @property
    def status(self) -> SpanStatus:
        return self._status

    @property
    def status_message(self) -> Optional[str]:
        return self._status_message

    @property
    def attributes(self) -> Dict[str, Any]:
        return dict(self._attributes)

    @property
    def events(self) -> List[SpanEvent]:
        return list(self._events)

    @property
    def links(self) -> List[SpanLink]:
        return list(self._links)

    @property
    def start_time(self) -> float:
        return self._start_time

    @property
    def end_time(self) -> Optional[float]:
        return self._end_time

    @property
    def duration_ms(self) -> Optional[float]:
        """Duration in milliseconds. None if span not ended."""
        if self._end_time is None:
            return None
        return (self._end_time - self._start_time) * 1000.0

    @property
    def is_recording(self) -> bool:
        """Whether the span is still recording (not ended)."""
        return self._end_time is None

    @property
    def context(self) -> SpanContext:
        """Get the span context for propagation."""
        return SpanContext(
            trace_id=self._trace_id,
            span_id=self._span_id,
            trace_flags=1,
            trace_state=self._trace_state,
        )

    def set_attribute(self, key: str, value: Any) -> Span:
        """Set a single attribute on the span."""
        self._attributes[key] = value
        return self

    def set_attributes(self, attributes: Dict[str, Any]) -> Span:
        """Set multiple attributes on the span."""
        self._attributes.update(attributes)
        return self

    def add_event(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None,
    ) -> Span:
        """Add a timestamped event to the span."""
        self._events.append(
            SpanEvent(
                name=name,
                timestamp=timestamp or time.time(),
                attributes=dict(attributes) if attributes else {},
            )
        )
        return self

    def add_link(self, context: SpanContext, attributes: Optional[Dict[str, Any]] = None) -> Span:
        """Add a link to another span context."""
        self._links.append(
            SpanLink(
                context=context,
                attributes=dict(attributes) if attributes else {},
            )
        )
        return self

    def set_status(self, status: SpanStatus, message: Optional[str] = None) -> Span:
        """Set the status of the span."""
        self._status = status
        self._status_message = message
        return self

    def record_exception(self, exception: Exception) -> Span:
        """Record an exception as an event and set status to error."""
        self.add_event(
            "exception",
            attributes={
                "exception.type": type(exception).__name__,
                "exception.message": str(exception),
            },
        )
        self.set_status(SpanStatus.ERROR, str(exception))
        return self

    def end(self, timestamp: Optional[float] = None) -> Span:
        """End the span, recording the end timestamp."""
        if self._end_time is None:
            self._end_time = timestamp or time.time()
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Serialize span to dictionary."""
        return {
            "name": self._name,
            "trace_id": self._trace_id,
            "span_id": self._span_id,
            "parent_span_id": self._parent_span_id,
            "kind": self._kind.value,
            "attributes": dict(self._attributes),
            "events": [
                {
                    "name": e.name,
                    "timestamp": e.timestamp,
                    "attributes": dict(e.attributes),
                }
                for e in self._events
            ],
            "links": [
                {
                    "context": link.context.to_dict(),
                    "attributes": dict(link.attributes),
                }
                for link in self._links
            ],
            "status": self._status.value,
            "status_message": self._status_message,
            "start_time": self._start_time,
            "end_time": self._end_time,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Span:
        """Deserialize span from dictionary."""
        span = cls(
            name=data["name"],
            trace_id=data["trace_id"],
            span_id=data["span_id"],
            parent_span_id=data.get("parent_span_id"),
            kind=SpanKind(data.get("kind", "internal")),
            attributes=data.get("attributes", {}),
            trace_state=data.get("trace_state", {}),
        )
        span._status = SpanStatus(data.get("status", "unset"))
        span._status_message = data.get("status_message")
        span._start_time = data["start_time"]
        span._end_time = data.get("end_time")
        for event_data in data.get("events", []):
            span._events.append(
                SpanEvent(
                    name=event_data["name"],
                    timestamp=event_data["timestamp"],
                    attributes=event_data.get("attributes", {}),
                )
            )
        for link_data in data.get("links", []):
            span._links.append(
                SpanLink(
                    context=SpanContext.from_dict(link_data["context"]),
                    attributes=link_data.get("attributes", {}),
                )
            )
        return span

    def __repr__(self) -> str:
        return (
            f"Span(name={self._name!r}, trace_id={self._trace_id!r}, "
            f"span_id={self._span_id!r}, kind={self._kind.value!r})"
        )
