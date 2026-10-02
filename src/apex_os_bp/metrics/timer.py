"""Timer metric — measures elapsed time and records to histogram."""

import time
from contextlib import contextmanager
from threading import Lock
from typing import Dict, Optional

from .histogram import Histogram


class Timer:
    """A timer metric that measures elapsed time.

    Records observations into an internal histogram. Can be used as a
    context manager or with explicit start/stop. Thread-safe.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        buckets: Optional[list] = None,
        labels: Optional[Dict[str, str]] = None,
    ):
        self.name = name
        self.description = description
        self._labels = labels or {}
        self._histogram = Histogram(
            name=f"{name}_seconds",
            description=description,
            buckets=buckets,
            labels=labels,
        )
        self._lock = Lock()
        self._start_times: Dict[str, float] = {}

    def start(self, tag: str = "default") -> str:
        """Start a timer with an optional tag. Returns the tag."""
        with self._lock:
            self._start_times[tag] = time.perf_counter()
        return tag

    def stop(self, tag: str = "default") -> float:
        """Stop the timer for the given tag and record elapsed seconds.

        Returns elapsed time in seconds.
        """
        with self._lock:
            if tag not in self._start_times:
                raise KeyError(f"No active timer for tag '{tag}'")
            start = self._start_times.pop(tag)
        elapsed = time.perf_counter() - start
        self._histogram.observe(elapsed)
        return elapsed

    def observe(self, elapsed_seconds: float) -> None:
        """Manually record an elapsed time observation."""
        self._histogram.observe(elapsed_seconds)

    @contextmanager
    def time(self, tag: str = "default"):
        """Context manager that measures elapsed time.

        Usage:
            with timer.time():
                do_work()
        """
        self.start(tag)
        try:
            yield self
        finally:
            self.stop(tag)

    def get_histogram(self) -> Histogram:
        """Return the underlying histogram."""
        return self._histogram

    def get_count(self) -> int:
        """Return number of observations recorded."""
        return self._histogram.get_count()

    def get_sum(self) -> float:
        """Return total elapsed seconds recorded."""
        return self._histogram.get_sum()

    def get_mean(self) -> float:
        """Return mean elapsed seconds."""
        return self._histogram.get_mean()

    def get_min(self) -> float:
        """Return minimum elapsed seconds."""
        return self._histogram.get_min()

    def get_max(self) -> float:
        """Return maximum elapsed seconds."""
        return self._histogram.get_max()

    def get_percentile(self, p: float) -> float:
        """Return estimated p-th percentile of elapsed times."""
        return self._histogram.get_percentile(p)

    def reset(self) -> None:
        """Reset timer and underlying histogram."""
        with self._lock:
            self._start_times.clear()
        self._histogram.reset()

    def labels(self) -> Dict[str, str]:
        """Return labels associated with this timer."""
        return dict(self._labels)

    def to_dict(self) -> dict:
        """Serialize timer to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "labels": dict(self._labels),
            "type": "timer",
            "count": self.get_count(),
            "sum": self.get_sum(),
            "mean": self.get_mean(),
            "min": self.get_min(),
            "max": self.get_max(),
        }
