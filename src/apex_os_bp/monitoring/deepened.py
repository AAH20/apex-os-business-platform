"""Deepened monitoring: health checks, metrics, logs, tracing, alerting."""
from __future__ import annotations

import json
import logging
import socket
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Health Checks
# ---------------------------------------------------------------------------

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ProbeResult:
    name: str
    status: HealthStatus
    latency_ms: float
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class Probe:
    def __init__(self, name: str, timeout: float = 5.0):
        self.name = name
        self.timeout = timeout

    def check(self) -> ProbeResult:
        raise NotImplementedError


class HTTPProbe(Probe):
    def __init__(self, name: str, url: str, expected_status: int = 200, timeout: float = 5.0):
        super().__init__(name, timeout)
        self.url = url
        self.expected_status = expected_status

    def check(self) -> ProbeResult:
        start = time.monotonic()
        try:
            resp = requests.get(self.url, timeout=self.timeout)
            latency = (time.monotonic() - start) * 1000
            status = HealthStatus.HEALTHY if resp.status_code == self.expected_status else HealthStatus.UNHEALTHY
            return ProbeResult(self.name, status, latency, f"HTTP {resp.status_code}")
        except Exception as exc:
            return ProbeResult(self.name, HealthStatus.UNHEALTHY, (time.monotonic() - start) * 1000, str(exc))


class TCPProbe(Probe):
    def __init__(self, name: str, host: str, port: int, timeout: float = 5.0):
        super().__init__(name, timeout)
        self.host = host
        self.port = port

    def check(self) -> ProbeResult:
        start = time.monotonic()
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout):
                return ProbeResult(self.name, HealthStatus.HEALTHY, (time.monotonic() - start) * 1000)
        except Exception as exc:
            return ProbeResult(self.name, HealthStatus.UNHEALTHY, (time.monotonic() - start) * 1000, str(exc))


class CustomProbe(Probe):
    def __init__(self, name: str, fn: Callable[[], bool], timeout: float = 5.0):
        super().__init__(name, timeout)
        self.fn = fn

    def check(self) -> ProbeResult:
        start = time.monotonic()
        try:
            ok = self.fn()
            return ProbeResult(self.name, HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY, (time.monotonic() - start) * 1000)
        except Exception as exc:
            return ProbeResult(self.name, HealthStatus.UNHEALTHY, (time.monotonic() - start) * 1000, str(exc))


class HealthChecker:
    def __init__(self):
        self.probes: List[Probe] = []

    def register(self, probe: Probe) -> None:
        self.probes.append(probe)

    def run_all(self) -> Dict[str, Any]:
        results = [p.check() for p in self.probes]
        overall = HealthStatus.HEALTHY
        if any(r.status == HealthStatus.UNHEALTHY for r in results):
            overall = HealthStatus.UNHEALTHY
        elif any(r.status == HealthStatus.DEGRADED for r in results):
            overall = HealthStatus.DEGRADED
        return {
            "status": overall.value,
            "timestamp": time.time(),
            "probes": [{"name": r.name, "status": r.status.value, "latency_ms": round(r.latency_ms, 2), "message": r.message, "metadata": r.metadata} for r in results],
        }


# ---------------------------------------------------------------------------
# Metrics (Prometheus)
# ---------------------------------------------------------------------------

class PrometheusMetrics:
    def __init__(self, namespace: str = "apex"):
        self.namespace = namespace
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}

    def counter(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None) -> None:
        self._counters[self._key(name, labels)] = self._counters.get(self._key(name, labels), 0) + value

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        self._gauges[self._key(name, labels)] = value

    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        self._histograms.setdefault(self._key(name, labels), []).append(value)

    def _key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        if not labels:
            return name
        return f"{name}{{{','.join(f'{k}=\"{v}\"' for k, v in sorted(labels.items()))}}}"

    def render(self) -> str:
        lines: List[str] = []
        for key, val in self._counters.items():
            lines += [f"# TYPE {key.split('{')[0]} counter", f"{key} {val}"]
        for key, val in self._gauges.items():
            lines += [f"# TYPE {key.split('{')[0]} gauge", f"{key} {val}"]
        for key, vals in self._histograms.items():
            base = key.split("{")[0]
            lines += [f"# TYPE {base} histogram", f"{key}_count {len(vals)}", f"{key}_sum {sum(vals)}"]
        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Log Aggregation (ELK)
# ---------------------------------------------------------------------------

class LogAggregator:
    def __init__(self, es_url: str, index: str = "apex-logs", batch_size: int = 100):
        self.es_url = es_url.rstrip("/")
        self.index = index
        self.batch_size = batch_size
        self._buffer: List[Dict[str, Any]] = []

    def log(self, level: str, message: str, **fields: Any) -> None:
        self._buffer.append({"@timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "level": level, "message": message, **fields})
        if len(self._buffer) >= self.batch_size:
            self.flush()

    def flush(self) -> bool:
        if not self._buffer:
            return True
        bulk = "".join(json.dumps({"index": {"_index": self.index}}) + \
                       "\n" + json.dumps(e) + "\n" for e in self._buffer)
        try:
            resp = requests.post(f"{self.es_url}/_bulk", data=bulk,
                                 headers={"Content-Type": "application/x-ndjson"}, timeout=10)
            ok = resp.status_code < 300
            if not ok:
                logger.warning("ELK bulk flush failed: %s", resp.text[:200])
            self._buffer.clear()
            return ok
        except Exception as exc:
            logger.error("ELK flush error: %s", exc)
            return False


# ---------------------------------------------------------------------------
# Tracing (Jaeger)
# ---------------------------------------------------------------------------

@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    operation: str
    start: float
    end: float = 0.0
    tags: Dict[str, str] = field(default_factory=dict)


class JaegerTracer:
    def __init__(self, jaeger_url: str, service_name: str):
        self.jaeger_url = jaeger_url.rstrip("/")
        self.service_name = service_name
        self._spans: List[Span] = []

    def start_span(self, operation: str, parent: Optional[Span] = None) -> Span:
        return Span(
            trace_id=parent.trace_id if parent else uuid.uuid4().hex,
            span_id=uuid.uuid4().hex[:16],
            parent_id=parent.span_id if parent else None,
            operation=operation,
            start=time.monotonic(),
        )

    def finish_span(self, span: Span, **tags: str) -> None:
        span.end = time.monotonic()
        span.tags.update(tags)
        self._spans.append(span)

    def export(self) -> bool:
        if not self._spans:
            return True
        data = [{"traceID": s.trace_id, "spanID": s.span_id, "parentSpanID": s.parent_id or "", "operationName": s.operation, "startTime": int(s.start * 1_000_000), "duration": int(
            (s.end - s.start) * 1_000_000), "tags": [{"key": k, "value": v} for k, v in s.tags.items()], "process": {"serviceName": self.service_name}} for s in self._spans]
        try:
            resp = requests.post(f"{self.jaeger_url}/api/traces", json={"data": data}, timeout=10)
            self._spans.clear()
            return resp.status_code < 300
        except Exception as exc:
            logger.error("Jaeger export error: %s", exc)
            return False


# ---------------------------------------------------------------------------
# Alerting (PagerDuty)
# ---------------------------------------------------------------------------

class PagerDutyAlerter:
    def __init__(self, routing_key: str, source: str = "apex-os"):
        self.routing_key = routing_key
        self.source = source

    def trigger(self, summary: str, severity: str = "critical", **details: Any) -> bool:
        payload = {"routing_key": self.routing_key, "event_action": "trigger", "payload": {
            "summary": summary, "source": self.source, "severity": severity, "custom_details": details}}
        try:
            resp = requests.post("https://events.pagerduty.com/v2/enqueue", json=payload, timeout=10)
            return resp.status_code == 202
        except Exception as exc:
            logger.error("PagerDuty alert failed: %s", exc)
            return False

    def resolve(self, dedup_key: str) -> bool:
        try:
            resp = requests.post("https://events.pagerduty.com/v2/enqueue",
                                 json={"routing_key": self.routing_key, "event_action": "resolve", "dedup_key": dedup_key}, timeout=10)
            return resp.status_code == 202
        except Exception as exc:
            logger.error("PagerDuty resolve failed: %s", exc)
            return False


# ---------------------------------------------------------------------------
# Unified facade
# ---------------------------------------------------------------------------

class MonitoringFacade:
    def __init__(self, es_url: str = "http://localhost:9200", jaeger_url: str = "http://localhost:14268", pd_routing_key: str = ""):
        self.health = HealthChecker()
        self.metrics = PrometheusMetrics()
        self.logs = LogAggregator(es_url)
        self.tracer = JaegerTracer(jaeger_url, "apex-os-bp")
        self.alerts = PagerDutyAlerter(pd_routing_key) if pd_routing_key else None

    def health_endpoint(self) -> Dict[str, Any]:
        result = self.health.run_all()
        if result["status"] == "unhealthy" and self.alerts:
            self.alerts.trigger("APEX-OS health check failed", severity="critical",
                                probes=[p["name"] for p in result["probes"] if p["status"] == "unhealthy"])
        return result

    def metrics_endpoint(self) -> str:
        return self.metrics.render()

    def shutdown(self) -> None:
        self.logs.flush()
        self.tracer.export()
