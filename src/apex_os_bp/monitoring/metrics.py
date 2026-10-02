"""Metrics collection for APEX-OS.

Provides Counter, Gauge, Histogram, and Timer metric types with
label support, thread-safe operations, and a central registry.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class MetricValue:
    """A single metric data point."""

    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class Counter:
    """A monotonically increasing counter metric."""

    def __init__(self, name: str, description: str = "", labels: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self._labels = labels or []
        self._values: Dict[Tuple[str, ...], float] = defaultdict(float)
        self._lock = threading.Lock()

    def inc(self, value: float = 1.0, **label_values: str) -> None:
        """Increment the counter by the given value."""
        key = tuple(label_values.get(l, "") for l in self._labels)
        with self._lock:
            self._values[key] += value

    def get(self, **label_values: str) -> float:
        """Get the current counter value for the given labels."""
        key = tuple(label_values.get(l, "") for l in self._labels)
        with self._lock:
            return self._values[key]

    def reset(self) -> None:
        """Reset all counter values to zero."""
        with self._lock:
            self._values.clear()

    def collect(self) -> List[MetricValue]:
        """Collect all metric values as data points."""
        with self._lock:
            return [
                MetricValue(
                    name=self.name,
                    value=v,
                    labels=dict(zip(self._labels, k)),
                )
                for k, v in self._values.items()
            ]


class Gauge:
    """A gauge metric that can go up and down."""

    def __init__(self, name: str, description: str = "", labels: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self._labels = labels or []
        self._values: Dict[Tuple[str, ...], float] = defaultdict(float)
        self._lock = threading.Lock()

    def set(self, value: float, **label_values: str) -> None:
        """Set the gauge to the given value."""
        key = tuple(label_values.get(l, "") for l in self._labels)
        with self._lock:
            self._values[key] = value

    def inc(self, value: float = 1.0, **label_values: str) -> None:
        """Increment the gauge by the given value."""
        key = tuple(label_values.get(l, "") for l in self._labels)
        with self._lock:
            self._values[key] += value

    def dec(self, value: float = 1.0, **label_values: str) -> None:
        """Decrement the gauge by the given value."""
        key = tuple(label_values.get(l, "") for l in self._labels)
        with self._lock:
            self._values[key] -= value

    def get(self, **label_values: str) -> float:
        """Get the current gauge value for the given labels."""
        key = tuple(label_values.get(l, "") for l in self._labels)
        with self._lock:
            return self._values[key]

    def collect(self) -> List[MetricValue]:
        """Collect all metric values as data points."""
        with self._lock:
            return [
                MetricValue(
                    name=self.name,
                    value=v,
                    labels=dict(zip(self._labels, k)),
                )
                for k, v in self._values.items()
            ]


class Histogram:
    """A histogram metric for tracking value distributions."""

    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

    def __init__(
        self,
        name: str,
        description: str = "",
        buckets: Optional[List[float]] = None,
        labels: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self._buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        self._labels = labels or []
        self._values: Dict[Tuple[str, ...], List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def observe(self, value: float, **label_values: str) -> None:
        """Record an observation."""
        key = tuple(label_values.get(l, "") for l in self._labels)
        with self._lock:
            self._values[key].append(value)

    def get_stats(self, **label_values: str) -> Dict[str, float]:
        """Get statistics for the given labels."""
        key = tuple(label_values.get(l, "") for l in self._labels)
        with self._lock:
            values = sorted(self._values[key])
        if not values:
            return {"count": 0, "sum": 0.0, "min": 0.0, "max": 0.0, "avg": 0.0}
        return {
            "count": len(values),
            "sum": sum(values),
            "min": values[0],
            "max": values[-1],
            "avg": sum(values) / len(values),
        }

    def get_bucket_counts(self, **label_values: str) -> Dict[str, int]:
        """Get cumulative bucket counts for the given labels.

        Follows Prometheus semantics: each value increments all buckets
        where value <= bucket, and +Inf equals the total observation count.
        """
        key = tuple(label_values.get(l, "") for l in self._labels)
        with self._lock:
            values = self._values[key]
        counts: Dict[str, int] = {str(b): 0 for b in self._buckets}
        counts["+Inf"] = len(values)
        for v in values:
            for b in self._buckets:
                if v <= b:
                    counts[str(b)] += 1
        return counts

    def collect(self) -> List[MetricValue]:
        """Collect all metric values as data points."""
        with self._lock:
            results = []
            for k, values in self._values.items():
                labels = dict(zip(self._labels, k))
                stats = self.get_stats(**labels)
                for stat_name, stat_value in stats.items():
                    results.append(
                        MetricValue(
                            name=f"{self.name}_{stat_name}",
                            value=stat_value,
                            labels=labels,
                        )
                    )
            return results


class Timer:
    """A timer metric for tracking operation durations."""

    def __init__(self, name: str, description: str = "", labels: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self._labels = labels or []
        self._histogram = Histogram(name=f"{name}_seconds", description=description, labels=labels)
        self._lock = threading.Lock()

    def time(self, **label_values: str):
        """Context manager for timing a block of code."""
        return _TimerContext(self, label_values)

    def observe(self, value: float, **label_values: str) -> None:
        """Record a duration observation in seconds."""
        self._histogram.observe(value, **label_values)

    def get_stats(self, **label_values: str) -> Dict[str, float]:
        """Get statistics for the given labels."""
        return self._histogram.get_stats(**label_values)

    def collect(self) -> List[MetricValue]:
        """Collect all metric values as data points."""
        return self._histogram.collect()


class _TimerContext:
    """Context manager for Timer.time()."""

    def __init__(self, timer: Timer, label_values: Dict[str, str]):
        self._timer = timer
        self._label_values = label_values
        self._start: Optional[float] = None

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._start is not None:
            elapsed = time.perf_counter() - self._start
            self._timer.observe(elapsed, **self._label_values)
        return False


class MetricRegistry:
    """Central registry for all metrics."""

    def __init__(self):
        self._metrics: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def register(self, metric: Any) -> Any:
        """Register a metric. Returns the metric for chaining."""
        with self._lock:
            if metric.name in self._metrics:
                raise ValueError(f"Metric '{metric.name}' is already registered")
            self._metrics[metric.name] = metric
        return metric

    def get(self, name: str) -> Optional[Any]:
        """Get a metric by name."""
        with self._lock:
            return self._metrics.get(name)

    def unregister(self, name: str) -> None:
        """Unregister a metric by name."""
        with self._lock:
            self._metrics.pop(name, None)

    def collect_all(self) -> List[MetricValue]:
        """Collect all metrics from all registered collectors."""
        results: List[MetricValue] = []
        with self._lock:
            metrics = list(self._metrics.values())
        for metric in metrics:
            if hasattr(metric, "collect"):
                results.extend(metric.collect())
        return results

    def clear(self) -> None:
        """Remove all registered metrics."""
        with self._lock:
            self._metrics.clear()

    def names(self) -> List[str]:
        """Get all registered metric names."""
        with self._lock:
            return list(self._metrics.keys())
