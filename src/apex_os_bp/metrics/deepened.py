"""Deepened metrics: Counter, Gauge, Histogram, Summary, Prometheus export."""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any, Dict, List, Tuple


class Counter:
    """Monotonically increasing counter with labels."""

    def __init__(self, name: str, description: str, labelnames: Tuple[str, ...] = ()):
        self._name = name
        self._description = description
        self._labelnames = labelnames
        self._values: Dict[Tuple[str, ...], float] = defaultdict(float)
        self._lock = threading.Lock()

    def labels(self, **kwargs: str) -> "Counter":
        return _BoundCounter(self, tuple(kwargs.get(ln, "") for ln in self._labelnames))

    def inc(self, value: float = 1.0, **kwargs: str) -> None:
        key = tuple(kwargs.get(ln, "") for ln in self._labelnames)
        with self._lock:
            self._values[key] += value

    def get(self, **kwargs: str) -> float:
        key = tuple(kwargs.get(ln, "") for ln in self._labelnames)
        with self._lock:
            return self._values[key]

    def collect(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{"labels": dict(zip(self._labelnames, k)), "value": v} for k, v in self._values.items()]


class _BoundCounter:
    def __init__(self, counter: Counter, key: Tuple[str, ...]):
        self._counter = counter
        self._key = key

    def inc(self, value: float = 1.0) -> None:
        with self._counter._lock:
            self._counter._values[self._key] += value


class Gauge:
    """Gauge with aggregation (sum, avg, min, max, count)."""

    def __init__(self, name: str, description: str, labelnames: Tuple[str, ...] = ()):
        self._name = name
        self._description = description
        self._labelnames = labelnames
        self._values: Dict[Tuple[str, ...], float] = defaultdict(float)
        self._lock = threading.Lock()

    def labels(self, **kwargs: str) -> "Gauge":
        return _BoundGauge(self, tuple(kwargs.get(ln, "") for ln in self._labelnames))

    def set(self, value: float, **kwargs: str) -> None:
        key = tuple(kwargs.get(ln, "") for ln in self._labelnames)
        with self._lock:
            self._values[key] = value

    def inc(self, value: float = 1.0, **kwargs: str) -> None:
        key = tuple(kwargs.get(ln, "") for ln in self._labelnames)
        with self._lock:
            self._values[key] += value

    def dec(self, value: float = 1.0, **kwargs: str) -> None:
        key = tuple(kwargs.get(ln, "") for ln in self._labelnames)
        with self._lock:
            self._values[key] -= value

    def get(self, **kwargs: str) -> float:
        key = tuple(kwargs.get(ln, "") for ln in self._labelnames)
        with self._lock:
            return self._values[key]

    def aggregate(self, agg: str = "sum") -> float:
        with self._lock:
            vals = list(self._values.values())
        if not vals:
            return 0.0
        if agg == "sum":
            return sum(vals)
        if agg == "avg":
            return sum(vals) / len(vals)
        if agg == "min":
            return min(vals)
        if agg == "max":
            return max(vals)
        if agg == "count":
            return float(len(vals))
        raise ValueError(f"Unknown aggregation: {agg}")

    def collect(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{"labels": dict(zip(self._labelnames, k)), "value": v} for k, v in self._values.items()]


class _BoundGauge:
    def __init__(self, gauge: Gauge, key: Tuple[str, ...]):
        self._gauge = gauge
        self._key = key

    def set(self, value: float) -> None:
        with self._gauge._lock:
            self._gauge._values[self._key] = value

    def inc(self, value: float = 1.0) -> None:
        with self._gauge._lock:
            self._gauge._values[self._key] += value

    def dec(self, value: float = 1.0) -> None:
        with self._gauge._lock:
            self._gauge._values[self._key] -= value


class Histogram:
    """Histogram with configurable buckets."""

    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(self, name: str, description: str, labelnames: Tuple[str, ...] = (),
                 buckets: Tuple[float, ...] = DEFAULT_BUCKETS):
        self._name = name
        self._description = description
        self._labelnames = labelnames
        self._buckets = tuple(sorted(buckets))
        self._values: Dict[Tuple[str, ...], List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def labels(self, **kwargs: str) -> "Histogram":
        return _BoundHistogram(self, tuple(kwargs.get(ln, "") for ln in self._labelnames))

    def observe(self, value: float, **kwargs: str) -> None:
        key = tuple(kwargs.get(ln, "") for ln in self._labelnames)
        with self._lock:
            self._values[key].append(value)

    def _bucket_counts(self, obs: List[float]) -> Dict[str, int]:
        counts = {f"le={b}": 0 for b in self._buckets}
        counts["le=+Inf"] = 0
        for v in obs:
            counts["le=+Inf"] += 1
            for b in self._buckets:
                if v <= b:
                    counts[f"le={b}"] += 1
        return counts

    def collect(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{"labels": dict(zip(self._labelnames, k)), "buckets": self._bucket_counts(v),
                     "sum": sum(v), "count": len(v)} for k, v in self._values.items()]


class _BoundHistogram:
    def __init__(self, histogram: Histogram, key: Tuple[str, ...]):
        self._histogram = histogram
        self._key = key

    def observe(self, value: float) -> None:
        with self._histogram._lock:
            self._histogram._values[self._key].append(value)


class Summary:
    """Summary with configurable quantiles."""

    DEFAULT_QUANTILES = (0.5, 0.9, 0.95, 0.99)

    def __init__(self, name: str, description: str, labelnames: Tuple[str, ...] = (),
                 quantiles: Tuple[float, ...] = DEFAULT_QUANTILES):
        self._name = name
        self._description = description
        self._labelnames = labelnames
        self._quantiles = tuple(sorted(quantiles))
        self._values: Dict[Tuple[str, ...], List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def labels(self, **kwargs: str) -> "Summary":
        return _BoundSummary(self, tuple(kwargs.get(ln, "") for ln in self._labelnames))

    def observe(self, value: float, **kwargs: str) -> None:
        key = tuple(kwargs.get(ln, "") for ln in self._labelnames)
        with self._lock:
            self._values[key].append(value)

    def _compute_quantiles(self, obs: List[float]) -> Dict[float, float]:
        if not obs:
            return {q: 0.0 for q in self._quantiles}
        s = sorted(obs)
        n = len(s)
        return {q: s[int(q * (n - 1))] for q in self._quantiles}

    def collect(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{"labels": dict(zip(self._labelnames, k)), "quantiles": self._compute_quantiles(v),
                     "sum": sum(v), "count": len(v)} for k, v in self._values.items()]


class _BoundSummary:
    def __init__(self, summary: Summary, key: Tuple[str, ...]):
        self._summary = summary
        self._key = key

    def observe(self, value: float) -> None:
        with self._summary._lock:
            self._summary._values[self._key].append(value)


class PrometheusExporter:
    """Export registered metrics in Prometheus text format."""

    def __init__(self):
        self._metrics: List[Any] = []
        self._lock = threading.Lock()

    def register(self, metric: Any) -> None:
        with self._lock:
            self._metrics.append(metric)

    def unregister(self, metric: Any) -> None:
        with self._lock:
            if metric in self._metrics:
                self._metrics.remove(metric)

    def _format_labels(self, labels: Dict[str, str]) -> str:
        if not labels:
            return ""
        return "{" + ",".join(f'{k}="{v}"' for k, v in sorted(labels.items())) + "}"

    def _escape(self, text: str) -> str:
        return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    def export(self) -> str:
        lines: List[str] = []
        with self._lock:
            metrics = list(self._metrics)
        for metric in metrics:
            name = metric._name
            lines.append(f"# HELP {name} {self._escape(metric._description)}")
            if isinstance(metric, Counter):
                lines.append(f"# TYPE {name} counter")
                for item in metric.collect():
                    lines.append(f"{name}{self._format_labels(item['labels'])} {item['value']}")
            elif isinstance(metric, Gauge):
                lines.append(f"# TYPE {name} gauge")
                for item in metric.collect():
                    lines.append(f"{name}{self._format_labels(item['labels'])} {item['value']}")
            elif isinstance(metric, Histogram):
                lines.append(f"# TYPE {name} histogram")
                for item in metric.collect():
                    labels = self._format_labels(item["labels"])
                    for le, count in item["buckets"].items():
                        lines.append(f'{name}_bucket{{le="{le}"}}{labels} {count}')
                    lines.append(f"{name}_sum{labels} {item['sum']}")
                    lines.append(f"{name}_count{labels} {item['count']}")
            elif isinstance(metric, Summary):
                lines.append(f"# TYPE {name} summary")
                for item in metric.collect():
                    labels = self._format_labels(item["labels"])
                    for q, val in item["quantiles"].items():
                        lines.append(f'{name}{{quantile="{q}"}}{labels} {val}')
                    lines.append(f"{name}_sum{labels} {item['sum']}")
                    lines.append(f"{name}_count{labels} {item['count']}")
        return "\n".join(lines) + "\n"


_registry: List[Any] = []
_registry_lock = threading.Lock()


def register(metric: Any) -> None:
    with _registry_lock:
        _registry.append(metric)


def get_exporter() -> PrometheusExporter:
    exporter = PrometheusExporter()
    with _registry_lock:
        for m in _registry:
            exporter.register(m)
    return exporter
