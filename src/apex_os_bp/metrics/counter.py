"""Counter metric — monotonically increasing value."""

from threading import Lock
from typing import Dict, Optional


class Counter:
    """A monotonically increasing counter metric.

    Supports incrementing by arbitrary amounts, labels, and reset.
    Thread-safe.
    """

    def __init__(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None):
        self.name = name
        self.description = description
        self._labels = labels or {}
        self._value: float = 0.0
        self._lock = Lock()

    def inc(self, amount: float = 1.0) -> float:
        """Increment counter by amount (default 1). Returns new value."""
        with self._lock:
            self._value += amount
            return self._value

    def dec(self, amount: float = 1.0) -> float:
        """Decrement counter by amount (default 1). Returns new value."""
        with self._lock:
            self._value -= amount
            return self._value

    def set(self, value: float) -> None:
        """Set counter to an absolute value."""
        with self._lock:
            self._value = value

    def get(self) -> float:
        """Return current counter value."""
        with self._lock:
            return self._value

    def reset(self) -> None:
        """Reset counter to zero."""
        with self._lock:
            self._value = 0.0

    def labels(self) -> Dict[str, str]:
        """Return labels associated with this counter."""
        return dict(self._labels)

    def to_dict(self) -> dict:
        """Serialize counter to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "labels": dict(self._labels),
            "value": self.get(),
            "type": "counter",
        }
