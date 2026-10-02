"""Gauge metric — arbitrary up/down value."""

from threading import Lock
from typing import Dict, Optional


class Gauge:
    """A gauge metric that can go up or down arbitrarily.

    Supports inc, dec, set operations. Thread-safe.
    """

    def __init__(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None):
        self.name = name
        self.description = description
        self._labels = labels or {}
        self._value: float = 0.0
        self._lock = Lock()

    def inc(self, amount: float = 1.0) -> float:
        """Increment gauge by amount. Returns new value."""
        with self._lock:
            self._value += amount
            return self._value

    def dec(self, amount: float = 1.0) -> float:
        """Decrement gauge by amount. Returns new value."""
        with self._lock:
            self._value -= amount
            return self._value

    def set(self, value: float) -> None:
        """Set gauge to an absolute value."""
        with self._lock:
            self._value = value

    def get(self) -> float:
        """Return current gauge value."""
        with self._lock:
            return self._value

    def reset(self) -> None:
        """Reset gauge to zero."""
        with self._lock:
            self._value = 0.0

    def labels(self) -> Dict[str, str]:
        """Return labels associated with this gauge."""
        return dict(self._labels)

    def to_dict(self) -> dict:
        """Serialize gauge to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "labels": dict(self._labels),
            "value": self.get(),
            "type": "gauge",
        }
