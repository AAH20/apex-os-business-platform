"""Metric aggregation — collect and aggregate multiple metrics."""

from threading import RLock
from typing import Any, Dict, List, Optional, Union

from .counter import Counter
from .gauge import Gauge
from .histogram import Histogram
from .timer import Timer


class MetricAggregation:
    """Aggregates multiple metrics and provides summary statistics.

    Supports registering metrics, querying by name/type, and computing
    aggregate statistics across all registered metrics. Thread-safe.
    """

    def __init__(self):
        self._metrics: Dict[str, Any] = {}
        self._lock = RLock()

    def register(self, metric: Union[Counter, Gauge, Histogram, Timer]) -> None:
        """Register a metric for aggregation."""
        with self._lock:
            self._metrics[metric.name] = metric

    def unregister(self, name: str) -> bool:
        """Remove a metric by name. Returns True if found and removed."""
        with self._lock:
            if name in self._metrics:
                del self._metrics[name]
                return True
            return False

    def get(self, name: str) -> Optional[Any]:
        """Get a metric by name."""
        with self._lock:
            return self._metrics.get(name)

    def get_all(self) -> Dict[str, Any]:
        """Return all registered metrics."""
        with self._lock:
            return dict(self._metrics)

    def get_by_type(self, metric_type: str) -> List[Any]:
        """Return all metrics of a given type ('counter', 'gauge', 'histogram', 'timer')."""
        with self._lock:
            return [m for m in self._metrics.values() if m.__class__.__name__.lower() == metric_type.lower()]

    def names(self) -> List[str]:
        """Return all registered metric names."""
        with self._lock:
            return list(self._metrics.keys())

    def count(self) -> int:
        """Return number of registered metrics."""
        with self._lock:
            return len(self._metrics)

    def summary(self) -> Dict[str, dict]:
        """Return a summary dict of all metrics serialized."""
        with self._lock:
            return {name: metric.to_dict() for name, metric in self._metrics.items()}

    def aggregate_sum(self, metric_type: Optional[str] = None) -> float:
        """Sum values across all metrics (or filtered by type).

        For Counter/Gauge: uses current value.
        For Histogram/Timer: uses sum of observations.
        """
        with self._lock:
            metrics = self._metrics.values()
            if metric_type:
                metrics = [m for m in metrics if m.__class__.__name__.lower() == metric_type.lower()]
            total = 0.0
            for m in metrics:
                if isinstance(m, (Counter, Gauge)):
                    total += m.get()
                elif isinstance(m, (Histogram, Timer)):
                    total += m.get_sum()
            return total

    def aggregate_mean(self, metric_type: Optional[str] = None) -> float:
        """Compute mean value across all metrics (or filtered by type)."""
        with self._lock:
            metrics = list(self._metrics.values())
            if metric_type:
                metrics = [m for m in metrics if m.__class__.__name__.lower() == metric_type.lower()]
            if not metrics:
                return 0.0
            return self.aggregate_sum(metric_type) / len(metrics)

    def aggregate_max(self, metric_type: Optional[str] = None) -> float:
        """Return maximum value across all metrics (or filtered by type)."""
        with self._lock:
            metrics = list(self._metrics.values())
            if metric_type:
                metrics = [m for m in metrics if m.__class__.__name__.lower() == metric_type.lower()]
            if not metrics:
                return 0.0
            values = []
            for m in metrics:
                if isinstance(m, (Counter, Gauge)):
                    values.append(m.get())
                elif isinstance(m, (Histogram, Timer)):
                    values.append(m.get_max())
            return max(values) if values else 0.0

    def aggregate_min(self, metric_type: Optional[str] = None) -> float:
        """Return minimum value across all metrics (or filtered by type)."""
        with self._lock:
            metrics = list(self._metrics.values())
            if metric_type:
                metrics = [m for m in metrics if m.__class__.__name__.lower() == metric_type.lower()]
            if not metrics:
                return 0.0
            values = []
            for m in metrics:
                if isinstance(m, (Counter, Gauge)):
                    values.append(m.get())
                elif isinstance(m, (Histogram, Timer)):
                    values.append(m.get_min())
            return min(values) if values else 0.0

    def filter_by_label(self, key: str, value: str) -> List[Any]:
        """Return all metrics that have a specific label key=value."""
        with self._lock:
            return [m for m in self._metrics.values() if m.labels().get(key) == value]

    def reset_all(self) -> None:
        """Reset all registered metrics."""
        with self._lock:
            for m in self._metrics.values():
                m.reset()

    def clear(self) -> None:
        """Remove all registered metrics."""
        with self._lock:
            self._metrics.clear()
