"""Histogram metric — distribution of observations into buckets."""

import bisect
import math
import time
from threading import Lock
from typing import Dict, List, Optional, Tuple


class Histogram:
    """A histogram metric that counts observations into configurable buckets.

    Tracks count, sum, min, max, and per-bucket counts. Thread-safe.
    """

    DEFAULT_BUCKETS: Tuple[float, ...] = (
        0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5,
        0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float("inf"),
    )

    def __init__(
        self,
        name: str,
        description: str = "",
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None,
    ):
        self.name = name
        self.description = description
        self._labels = labels or {}
        self._buckets: Tuple[float, ...] = tuple(sorted(buckets)) if buckets else self.DEFAULT_BUCKETS
        self._bucket_counts: List[int] = [0] * len(self._buckets)
        self._count: int = 0
        self._sum: float = 0.0
        self._min: float = float("inf")
        self._max: float = float("-inf")
        self._lock = Lock()

    def observe(self, value: float) -> None:
        """Record an observation."""
        with self._lock:
            self._count += 1
            self._sum += value
            if value < self._min:
                self._min = value
            if value > self._max:
                self._max = value
            idx = bisect.bisect_left(self._buckets, value)
            if idx < len(self._buckets):
                self._bucket_counts[idx] += 1

    def observe_many(self, values: List[float]) -> None:
        """Record multiple observations at once."""
        for v in values:
            self.observe(v)

    def get_count(self) -> int:
        """Return total number of observations."""
        with self._lock:
            return self._count

    def get_sum(self) -> float:
        """Return sum of all observed values."""
        with self._lock:
            return self._sum

    def get_min(self) -> float:
        """Return minimum observed value."""
        with self._lock:
            return self._min if self._count > 0 else 0.0

    def get_max(self) -> float:
        """Return maximum observed value."""
        with self._lock:
            return self._max if self._count > 0 else 0.0

    def get_mean(self) -> float:
        """Return mean of observed values."""
        with self._lock:
            return self._sum / self._count if self._count > 0 else 0.0

    def get_bucket_counts(self) -> Dict[float, int]:
        """Return mapping of bucket upper-bound to cumulative count."""
        with self._lock:
            cumulative = []
            running = 0
            for i, bound in enumerate(self._buckets):
                running += self._bucket_counts[i]
                cumulative.append((bound, running))
            return dict(cumulative)

    def get_percentile(self, p: float) -> float:
        """Estimate the p-th percentile (0 < p <= 100) from buckets."""
        if not 0 < p <= 100:
            raise ValueError("Percentile must be in (0, 100]")
        with self._lock:
            if self._count == 0:
                return 0.0
            target = (p / 100.0) * self._count
            for i, bound in enumerate(self._buckets):
                cumulative = sum(self._bucket_counts[: i + 1])
                if cumulative >= target:
                    return bound
            return self._buckets[-1]

    def get_buckets(self) -> Tuple[float, ...]:
        """Return the bucket boundaries."""
        return self._buckets

    def reset(self) -> None:
        """Reset all histogram state."""
        with self._lock:
            self._bucket_counts = [0] * len(self._buckets)
            self._count = 0
            self._sum = 0.0
            self._min = float("inf")
            self._max = float("-inf")

    def labels(self) -> Dict[str, str]:
        """Return labels associated with this histogram."""
        return dict(self._labels)

    def to_dict(self) -> dict:
        """Serialize histogram to dictionary."""
        with self._lock:
            cumulative = []
            running = 0
            for i, bound in enumerate(self._buckets):
                running += self._bucket_counts[i]
                cumulative.append((bound, running))
            return {
                "name": self.name,
                "description": self.description,
                "labels": dict(self._labels),
                "type": "histogram",
                "count": self._count,
                "sum": self._sum,
                "min": self._min if self._count > 0 else 0.0,
                "max": self._max if self._count > 0 else 0.0,
                "mean": self._sum / self._count if self._count > 0 else 0.0,
                "buckets": list(self._buckets),
                "bucket_counts": dict(cumulative),
            }
