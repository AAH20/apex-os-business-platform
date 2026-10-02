"""Distributed tracing system for APEX-OS Business Platform.

Provides end-to-end observability across services with:
- Distributed tracing with context propagation
- Span management with parent-child relationships
- Configurable trace sampling strategies
- Trace analytics and metrics aggregation
- Text-based trace visualization
"""
from __future__ import annotations

from apex_os_bp.tracing.analytics import TraceAnalytics, TraceSummary
from apex_os_bp.tracing.distributed_tracing import (
    DistributedTracer,
    TraceContext,
    inject_context,
    extract_context,
)
from apex_os_bp.tracing.sampling import (
    SamplingDecision,
    SamplingStrategy,
    AlwaysOffSampler,
    AlwaysOnSampler,
    RateBasedSampler,
    ProbabilisticSampler,
    TailBasedSampler,
)
from apex_os_bp.tracing.span import Span, SpanKind, SpanStatus, SpanContext
from apex_os_bp.tracing.visualization import TraceVisualizer, TraceTree

__all__ = [
    "DistributedTracer",
    "TraceContext",
    "inject_context",
    "extract_context",
    "TraceAnalytics",
    "TraceSummary",
    "SamplingDecision",
    "SamplingStrategy",
    "AlwaysOffSampler",
    "AlwaysOnSampler",
    "RateBasedSampler",
    "ProbabilisticSampler",
    "TailBasedSampler",
    "Span",
    "SpanKind",
    "SpanStatus",
    "SpanContext",
    "TraceVisualizer",
    "TraceTree",
]
