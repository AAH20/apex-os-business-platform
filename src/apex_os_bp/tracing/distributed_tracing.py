"""Distributed tracing for APEX-OS Business Platform.

Provides end-to-end trace context propagation across service boundaries.
The DistributedTracer manages span lifecycle and context injection/extraction
for cross-process communication.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from apex_os_bp.tracing.sampling import SamplingDecision, SamplingStrategy, AlwaysOnSampler
from apex_os_bp.tracing.span import Span, SpanContext, SpanKind, SpanStatus


@dataclass
class TraceContext:
    """Trace context for propagation across service boundaries."""
    trace_id: str
    span_id: str
    trace_flags: int = 1
    trace_state: Dict[str, str] = field(default_factory=dict)
    baggage: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "trace_flags": self.trace_flags,
            "trace_state": dict(self.trace_state),
            "baggage": dict(self.baggage),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TraceContext:
        return cls(
            trace_id=data["trace_id"],
            span_id=data["span_id"],
            trace_flags=data.get("trace_flags", 1),
            trace_state=data.get("trace_state", {}),
            baggage=data.get("baggage", {}),
        )


class DistributedTracer:
    """Manages distributed tracing across services.

    The tracer creates spans, manages context propagation, and
    coordinates sampling decisions. It supports:
    - Starting and ending spans
    - Context injection for outbound requests
    - Context extraction from inbound requests
    - Parent-child span relationships
    - Thread-local context management
    """

    def __init__(
        self,
        service_name: str = "unknown-service",
        sampling_strategy: Optional[SamplingStrategy] = None,
    ):
        self._service_name = service_name
        self._sampling_strategy = sampling_strategy or AlwaysOnSampler()
        self._active_spans: Dict[str, Span] = {}
        self._completed_spans: List[Span] = []
        self._max_completed = 10000
        self._lock = threading.Lock()
        self._context_local = threading.local()

    @property
    def service_name(self) -> str:
        return self._service_name

    @property
    def sampling_strategy(self) -> SamplingStrategy:
        return self._sampling_strategy

    @sampling_strategy.setter
    def sampling_strategy(self, strategy: SamplingStrategy) -> None:
        self._sampling_strategy = strategy

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        parent_context: Optional[TraceContext] = None,
    ) -> Span:
        """Start a new span.

        If parent_context is provided, the span becomes a child of that context.
        Otherwise, uses the current thread-local context if available.
        """
        # Determine parent
        parent_span_id = None
        trace_id = None
        trace_state = None

        if parent_context:
            parent_span_id = parent_context.span_id
            trace_id = parent_context.trace_id
            trace_state = parent_context.trace_state
        else:
            current = self._get_current_context()
            if current:
                parent_span_id = current.span_id
                trace_id = current.trace_id
                trace_state = current.trace_state

        # Sampling decision
        decision = self._sampling_strategy.should_sample(
            trace_id or "", name, attributes
        )

        span = Span(
            name=name,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            kind=kind,
            attributes={
                "service.name": self._service_name,
                "sampling.sampled": decision.sampled,
                **(decision.attributes or {}),
                **(attributes or {}),
            },
            trace_state=trace_state,
        )

        if decision.sampled:
            with self._lock:
                self._active_spans[span.span_id] = span

        return span

    def end_span(self, span: Span) -> None:
        """End a span and move it to completed spans."""
        span.end()
        with self._lock:
            self._active_spans.pop(span.span_id, None)
            self._completed_spans.append(span)
            if len(self._completed_spans) > self._max_completed:
                self._completed_spans = self._completed_spans[-self._max_completed:]

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Span]:
        """Context manager for span lifecycle."""
        span = self.start_span(name, kind, attributes)
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            raise
        finally:
            self.end_span(span)

    def inject_context(self, context: Optional[TraceContext] = None) -> Dict[str, str]:
        """Inject trace context into a carrier (e.g., HTTP headers).

        Returns a dictionary suitable for use as HTTP headers.
        """
        ctx = context or self._get_current_context()
        if ctx is None:
            return {}

        carrier = {
            "x-trace-id": ctx.trace_id,
            "x-span-id": ctx.span_id,
            "x-trace-flags": str(ctx.trace_flags),
        }
        if ctx.trace_state:
            carrier["x-trace-state"] = ",".join(f"{k}={v}" for k, v in ctx.trace_state.items())
        if ctx.baggage:
            carrier["x-baggage"] = ",".join(f"{k}={v}" for k, v in ctx.baggage.items())
        return carrier

    def extract_context(self, carrier: Dict[str, str]) -> Optional[TraceContext]:
        """Extract trace context from a carrier (e.g., HTTP headers).

        Returns None if no valid context is found.
        """
        trace_id = carrier.get("x-trace-id")
        span_id = carrier.get("x-span-id")

        if not trace_id or not span_id:
            return None

        trace_state = {}
        state_str = carrier.get("x-trace-state", "")
        if state_str:
            for pair in state_str.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    trace_state[k.strip()] = v.strip()

        baggage = {}
        baggage_str = carrier.get("x-baggage", "")
        if baggage_str:
            for pair in baggage_str.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    baggage[k.strip()] = v.strip()

        return TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=int(carrier.get("x-trace-flags", "1")),
            trace_state=trace_state,
            baggage=baggage,
        )

    def set_current_context(self, context: TraceContext) -> None:
        """Set the current thread-local trace context."""
        self._context_local.context = context

    def get_current_context(self) -> Optional[TraceContext]:
        """Get the current thread-local trace context."""
        return self._get_current_context()

    def clear_current_context(self) -> None:
        """Clear the current thread-local trace context."""
        self._context_local.context = None

    def get_active_spans(self) -> List[Span]:
        """Get all currently active (recording) spans."""
        with self._lock:
            return list(self._active_spans.values())

    def get_completed_spans(self, trace_id: Optional[str] = None) -> List[Span]:
        """Get completed spans, optionally filtered by trace ID."""
        with self._lock:
            if trace_id:
                return [s for s in self._completed_spans if s.trace_id == trace_id]
            return list(self._completed_spans)

    def get_trace(self, trace_id: str) -> List[Span]:
        """Get all spans for a given trace ID."""
        return self.get_completed_spans(trace_id)

    def clear_completed(self) -> None:
        """Clear all completed spans."""
        with self._lock:
            self._completed_spans.clear()

    def _get_current_context(self) -> Optional[TraceContext]:
        """Get thread-local context (internal)."""
        return getattr(self._context_local, "context", None)


def inject_context(context: Optional[TraceContext] = None) -> Dict[str, str]:
    """Module-level convenience function for context injection."""
    tracer = DistributedTracer()
    return tracer.inject_context(context)


def extract_context(carrier: Dict[str, str]) -> Optional[TraceContext]:
    """Module-level convenience function for context extraction."""
    tracer = DistributedTracer()
    return tracer.extract_context(carrier)
