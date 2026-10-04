"""Trace analytics for APEX-OS Business Platform.

Provides metrics aggregation and analysis over collected traces:
- Trace duration statistics
- Error rate calculation
- Service dependency analysis
- Span count aggregations
- Throughput metrics
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Tuple

from apex_os_bp.tracing.span import Span, SpanStatus


@dataclass
class TraceSummary:
    """Summary statistics for a single trace."""
    trace_id: str
    span_count: int
    root_service: str
    duration_ms: float
    has_error: bool
    services: Set[str] = field(default_factory=set)
    span_kinds: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_count": self.span_count,
            "root_service": self.root_service,
            "duration_ms": self.duration_ms,
            "has_error": self.has_error,
            "services": sorted(self.services),
            "span_kinds": dict(self.span_kinds),
        }


@dataclass
class ServiceMetrics:
    """Aggregated metrics for a service."""
    service_name: str
    total_spans: int = 0
    error_count: int = 0
    durations_ms: List[float] = field(default_factory=list)

    @property
    def error_rate(self) -> float:
        if self.total_spans == 0:
            return 0.0
        return self.error_count / self.total_spans

    @property
    def avg_duration_ms(self) -> float:
        if not self.durations_ms:
            return 0.0
        return statistics.mean(self.durations_ms)

    @property
    def p50_duration_ms(self) -> float:
        if not self.durations_ms:
            return 0.0
        return statistics.median(self.durations_ms)

    @property
    def p95_duration_ms(self) -> float:
        if not self.durations_ms:
            return 0.0
        sorted_d = sorted(self.durations_ms)
        idx = int(len(sorted_d) * 0.95)
        idx = min(idx, len(sorted_d) - 1)
        return sorted_d[idx]

    @property
    def p99_duration_ms(self) -> float:
        if not self.durations_ms:
            return 0.0
        sorted_d = sorted(self.durations_ms)
        idx = int(len(sorted_d) * 0.99)
        idx = min(idx, len(sorted_d) - 1)
        return sorted_d[idx]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "total_spans": self.total_spans,
            "error_count": self.error_count,
            "error_rate": self.error_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "p50_duration_ms": self.p50_duration_ms,
            "p95_duration_ms": self.p95_duration_ms,
            "p99_duration_ms": self.p99_duration_ms,
        }


class TraceAnalytics:
    """Analytics engine for trace data.

    Aggregates spans into trace summaries and service metrics,
    providing insights into system behavior.
    """

    def __init__(self):
        self._spans: List[Span] = []

    def add_span(self, span: Span) -> None:
        """Add a span for analysis."""
        self._spans.append(span)

    def add_spans(self, spans: List[Span]) -> None:
        """Add multiple spans for analysis."""
        self._spans.extend(spans)

    def clear(self) -> None:
        """Clear all collected spans."""
        self._spans.clear()

    def get_trace_summaries(self) -> List[TraceSummary]:
        """Generate summaries for all traces."""
        traces = self._group_by_trace()
        summaries = []
        for trace_id, spans in traces.items():
            summaries.append(self._summarize_trace(trace_id, spans))
        return summaries

    def get_service_metrics(self) -> Dict[str, ServiceMetrics]:
        """Get aggregated metrics per service."""
        metrics: Dict[str, ServiceMetrics] = {}
        for span in self._spans:
            service = span.attributes.get("service.name", "unknown")
            if service not in metrics:
                metrics[service] = ServiceMetrics(service_name=service)
            sm = metrics[service]
            sm.total_spans += 1
            if span.status == SpanStatus.ERROR:
                sm.error_count += 1
            duration = span.duration_ms
            if duration is not None:
                sm.durations_ms.append(duration)
        return metrics

    def get_error_traces(self) -> List[str]:
        """Get trace IDs that contain at least one error span."""
        error_traces = set()
        for span in self._spans:
            if span.status == SpanStatus.ERROR:
                error_traces.add(span.trace_id)
        return sorted(error_traces)

    def get_slow_traces(self, threshold_ms: float = 1000.0) -> List[Tuple[str, float]]:
        """Get traces with duration exceeding threshold.

        Returns list of (trace_id, duration_ms) tuples sorted by duration desc.
        """
        traces = self._group_by_trace()
        slow = []
        for trace_id, spans in traces.items():
            duration = self._compute_trace_duration(spans)
            if duration >= threshold_ms:
                slow.append((trace_id, duration))
        slow.sort(key=lambda x: x[1], reverse=True)
        return slow

    def get_service_dependencies(self) -> Dict[str, Set[str]]:
        """Analyze service dependencies from span parent-child relationships.

        Returns a dict mapping service name to set of downstream services.
        """
        span_map = {s.span_id: s for s in self._spans}
        dependencies: Dict[str, Set[str]] = defaultdict(set)

        for span in self._spans:
            if span.parent_span_id and span.parent_span_id in span_map:
                parent = span_map[span.parent_span_id]
                parent_service = parent.attributes.get("service.name", "unknown")
                child_service = span.attributes.get("service.name", "unknown")
                if parent_service != child_service:
                    dependencies[parent_service].add(child_service)

        return dict(dependencies)

    def get_span_kind_distribution(self) -> Dict[str, int]:
        """Get distribution of span kinds across all spans."""
        dist: Dict[str, int] = defaultdict(int)
        for span in self._spans:
            dist[span.kind.value] += 1
        return dict(dist)

    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall statistics across all traces."""
        if not self._spans:
            return {
                "total_spans": 0,
                "total_traces": 0,
                "error_count": 0,
                "error_rate": 0.0,
                "avg_duration_ms": 0.0,
                "services": [],
            }

        traces = self._group_by_trace()
        error_count = sum(1 for s in self._spans if s.status == SpanStatus.ERROR)
        durations = [s.duration_ms for s in self._spans if s.duration_ms is not None]
        services = set()
        for s in self._spans:
            svc = s.attributes.get("service.name")
            if svc:
                services.add(svc)

        return {
            "total_spans": len(self._spans),
            "total_traces": len(traces),
            "error_count": error_count,
            "error_rate": error_count / len(self._spans),
            "avg_duration_ms": statistics.mean(durations) if durations else 0.0,
            "services": sorted(services),
        }

    def _group_by_trace(self) -> Dict[str, List[Span]]:
        """Group spans by their trace ID."""
        traces: Dict[str, List[Span]] = defaultdict(list)
        for span in self._spans:
            traces[span.trace_id].append(span)
        return dict(traces)

    def _summarize_trace(self, trace_id: str, spans: List[Span]) -> TraceSummary:
        """Create a summary for a single trace."""
        services = set()
        span_kinds: Dict[str, int] = defaultdict(int)
        has_error = False
        root_service = "unknown"

        for span in spans:
            svc = span.attributes.get("service.name")
            if svc:
                services.add(svc)
            span_kinds[span.kind.value] += 1
            if span.status == SpanStatus.ERROR:
                has_error = True

        # Find root span (no parent)
        root_spans = [s for s in spans if s.parent_span_id is None]
        if root_spans:
            root_service = root_spans[0].attributes.get("service.name", "unknown")

        duration = self._compute_trace_duration(spans)

        return TraceSummary(
            trace_id=trace_id,
            span_count=len(spans),
            root_service=root_service,
            duration_ms=duration,
            has_error=has_error,
            services=services,
            span_kinds=dict(span_kinds),
        )

    def _compute_trace_duration(self, spans: List[Span]) -> float:
        """Compute the total duration of a trace in milliseconds."""
        if not spans:
            return 0.0
        start_times = [s.start_time for s in spans]
        end_times = [s.end_time for s in spans if s.end_time is not None]
        if not end_times:
            return 0.0
        return (max(end_times) - min(start_times)) * 1000.0
