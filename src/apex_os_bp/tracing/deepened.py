"""Deepened tracing: OpenTelemetry, spans, analytics, correlation, export."""
from __future__ import annotations
import json, logging, time, random, urllib.request
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False; trace = None

logger = logging.getLogger(__name__)
SERVICE_NAME = "apex-os-bp"


def init_otel(service_name: str = SERVICE_NAME, endpoint: Optional[str] = None) -> Any:
    """Initialise OpenTelemetry tracer provider with optional OTLP endpoint."""
    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry not installed; tracing disabled"); return None
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    if endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    return provider


def get_tracer(name: str = SERVICE_NAME) -> Any:
    """Return an OpenTelemetry tracer (no-op if unavailable)."""
    return trace.get_tracer(name) if OTEL_AVAILABLE else _NoopTracer()


class _NoopTracer:
    def start_as_current_span(self, *a, **kw): return _NoopSpan()
    def start_span(self, *a, **kw): return _NoopSpan()


class _NoopSpan:
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def set_attribute(self, *a, **kw): pass
    def add_event(self, *a, **kw): pass
    def record_exception(self, *a, **kw): pass
    def set_status(self, *a, **kw): pass


# --- Span management with sampling ---
@dataclass
class SamplingConfig:
    rate: float = 1.0; max_per_second: int = 1000
    adaptive: bool = True; error_boost: float = 2.0


class Sampler:
    """Head-based sampler with rate limiting and adaptive error boosting."""
    def __init__(self, config: SamplingConfig = None):
        self.config = config or SamplingConfig()
        self._counters: Dict[str, int] = defaultdict(int)
        self._last_reset = time.monotonic()

    def should_sample(self, span_name: str, is_error: bool = False) -> bool:
        now = time.monotonic()
        if now - self._last_reset >= 1.0:
            self._counters.clear(); self._last_reset = now
        if self._counters[span_name] >= self.config.max_per_second: return False
        rate = self.config.rate
        if is_error and self.config.adaptive: rate = min(1.0, rate * self.config.error_boost)
        if random.random() > rate: return False
        self._counters[span_name] += 1; return True


class SpanManager:
    """Manage span lifecycle, attributes, and events."""
    def __init__(self, sampler: Sampler = None):
        self.sampler = sampler or Sampler(); self._active: Dict[str, Any] = {}

    def start_span(self, name: str, attributes: Dict[str, Any] = None,
                   is_error: bool = False) -> Optional[Any]:
        if not self.sampler.should_sample(name, is_error): return None
        span = get_tracer().start_span(name)
        for k, v in (attributes or {}).items(): span.set_attribute(k, v)
        self._active[name] = span; return span

    def end_span(self, span: Any, status: str = "OK"):
        if span is None: return
        try:
            from opentelemetry.trace import Status, StatusCode
            span.set_status(Status(StatusCode.OK if status == "OK" else StatusCode.ERROR))
        except Exception: pass
        span.end()

    def record_exception(self, span: Any, exc: Exception):
        if span is not None: span.record_exception(exc)


# --- Trace analytics with latency histograms ---
class LatencyHistogram:
    """Fixed-bucket latency histogram for span durations."""
    DEFAULT_BOUNDS = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

    def __init__(self, bounds: List[float] = None):
        self.bounds = bounds or self.DEFAULT_BOUNDS
        self._counts = [0] * len(self.bounds)
        self._sum = 0.0; self._count = 0
        self._min = float("inf"); self._max = 0.0

    def observe(self, d: float):
        self._sum += d; self._count += 1
        self._min = min(self._min, d); self._max = max(self._max, d)
        for i, b in enumerate(self.bounds):
            if d <= b: self._counts[i] += 1

    def percentile(self, p: float) -> float:
        if not self._count: return 0.0
        target = p * self._count; cumulative = 0
        for i, c in enumerate(self._counts):
            cumulative += c
            if cumulative >= target: return self.bounds[i]
        return self.bounds[-1]

    def summary(self) -> Dict[str, Any]:
        return {"count": self._count, "sum_ms": round(self._sum * 1000, 3),
                "min_ms": round(self._min * 1000, 3) if self._count else 0,
                "max_ms": round(self._max * 1000, 3),
                "p50_ms": round(self.percentile(0.50) * 1000, 3),
                "p95_ms": round(self.percentile(0.95) * 1000, 3),
                "p99_ms": round(self.percentile(0.99) * 1000, 3)}


class TraceAnalytics:
    """Aggregate latency histograms per operation."""
    def __init__(self): self._histograms: Dict[str, LatencyHistogram] = defaultdict(LatencyHistogram)
    def record(self, operation: str, duration_seconds: float): self._histograms[operation].observe(duration_seconds)
    def get_summary(self, operation: str = None) -> Dict[str, Any]:
        if operation: return {operation: self._histograms[operation].summary()}
        return {op: h.summary() for op, h in self._histograms.items()}


# --- Trace correlation with logs ---
class TraceLogCorrelator:
    """Inject trace/span IDs into log records and vice versa."""
    def __init__(self): self._trace_logs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def inject_context(self, carrier: Dict[str, str], span: Any = None) -> Dict[str, str]:
        if span is None: return carrier
        try:
            ctx = trace.set_span_in_context(span)
            TraceContextTextMapPropagator().inject(carrier, context=ctx)
        except Exception: pass
        return carrier

    def extract_context(self, carrier: Dict[str, str]) -> Any:
        try: return TraceContextTextMapPropagator().extract(carrier)
        except Exception: return None

    def log_with_trace(self, trace_id: str, level: str, message: str, extra: Dict[str, Any] = None):
        self._trace_logs[trace_id].append({"timestamp": time.time(), "level": level, "message": message, **(extra or {})})
        getattr(logger, level.lower(), logger.info)(f"[{trace_id}] {message}")

    def get_trace_logs(self, trace_id: str) -> List[Dict[str, Any]]: return list(self._trace_logs.get(trace_id, []))

    def format_log_with_context(self, record: Any, span: Any = None) -> str:
        parts = [record.getMessage()]
        if span is not None:
            try:
                ctx = span.get_span_context()
                parts.append(f"trace_id={ctx.trace_id:032x} span_id={ctx.span_id:016x}")
            except Exception: pass
        return " | ".join(parts)


# --- Trace export with Jaeger / Zipkin ---
class TraceExporter:
    """Export spans to Jaeger or Zipkin backends."""
    def __init__(self, backend: str = "jaeger", endpoint: str = "http://localhost:14268/api/traces"):
        self.backend = backend; self.endpoint = endpoint; self._spans: List[Dict[str, Any]] = []

    def export(self, span: Any):
        if span is None: return
        try:
            ctx = span.get_span_context()
            self._spans.append({"trace_id": f"{ctx.trace_id:032x}", "span_id": f"{ctx.span_id:016x}",
                                "name": getattr(span, "name", "unknown"),
                                "start_time_unix_nano": getattr(span, "start_time", 0),
                                "end_time_unix_nano": getattr(span, "end_time", 0),
                                "attributes": dict(getattr(span, "attributes", {}) or {})})
        except Exception as exc: logger.debug("Failed to export span: %s", exc)

    def flush(self) -> int:
        if not self._spans: return 0
        count = len(self._spans)
        if self.backend == "jaeger": self._flush_jaeger(self._spans)
        elif self.backend == "zipkin": self._flush_zipkin(self._spans)
        else: logger.warning("Unknown backend: %s", self.backend)
        self._spans.clear(); return count

    def _flush_jaeger(self, spans: List[Dict[str, Any]]):
        payload = json.dumps({"data": spans}).encode()
        req = urllib.request.Request(self.endpoint, data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        try: urllib.request.urlopen(req, timeout=5)
        except Exception as exc: logger.warning("Jaeger export failed: %s", exc)

    def _flush_zipkin(self, spans: List[Dict[str, Any]]):
        zipkin_spans = [{"traceId": s["trace_id"], "id": s["span_id"], "name": s["name"],
                         "timestamp": s.get("start_time_unix_nano", 0) // 1000,
                         "duration": max(1, (s.get("end_time_unix_nano", 0) - s.get("start_time_unix_nano", 0)) // 1000),
                         "tags": s.get("attributes", {})} for s in spans]
        payload = json.dumps(zipkin_spans).encode()
        req = urllib.request.Request(self.endpoint, data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        try: urllib.request.urlopen(req, timeout=5)
        except Exception as exc: logger.warning("Zipkin export failed: %s", exc)


# --- Convenience facade ---
class TracingFacade:
    """Unified entry point combining all tracing capabilities."""
    def __init__(self, service_name: str = SERVICE_NAME, sample_rate: float = 1.0,
                 export_backend: str = "jaeger", export_endpoint: str = "http://localhost:14268/api/traces"):
        self.service_name = service_name; self.provider = init_otel(service_name)
        self.sampler = Sampler(SamplingConfig(rate=sample_rate))
        self.span_manager = SpanManager(self.sampler)
        self.analytics = TraceAnalytics(); self.correlator = TraceLogCorrelator()
        self.exporter = TraceExporter(backend=export_backend, endpoint=export_endpoint)

    def start_span(self, name: str, attributes: Dict[str, Any] = None) -> Any:
        return self.span_manager.start_span(name, attributes)

    def end_span(self, span: Any, status: str = "OK", operation: str = None):
        if span is None: return
        try:
            duration = (time.time_ns() - span.start_time) / 1e9
            if operation: self.analytics.record(operation, duration)
        except Exception: pass
        self.exporter.export(span); self.span_manager.end_span(span, status)

    def trace(self, operation: str, attributes: Dict[str, Any] = None):
        """Decorator for tracing a function."""
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                span = self.start_span(operation, attributes)
                try:
                    result = func(*args, **kwargs); self.end_span(span, "OK", operation); return result
                except Exception as exc:
                    self.span_manager.record_exception(span, exc); self.end_span(span, "ERROR", operation); raise
            return wrapper
        return decorator

    def get_analytics(self) -> Dict[str, Any]: return self.analytics.get_summary()
    def flush_exports(self) -> int: return self.exporter.flush()
