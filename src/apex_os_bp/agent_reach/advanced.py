"""Agent-Reach advanced features: circuit breaker, retry, rate limiting, health checks, metrics."""

from __future__ import annotations

import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    _state: CircuitState = CircuitState.CLOSED
    _failures: int = 0
    _opened_at: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            if self._state is CircuitState.OPEN:
                if time.monotonic() - self._opened_at >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                else:
                    raise RuntimeError("Circuit breaker is OPEN")
        try:
            result = fn(*args, **kwargs)
        except Exception:
            with self._lock:
                self._failures += 1
                if self._failures >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    self._opened_at = time.monotonic()
            raise
        with self._lock:
            self._failures = 0
            self._state = CircuitState.CLOSED
        return result

    @property
    def state(self) -> CircuitState:
        return self._state


def retry(
    fn: Callable[..., Any],
    *args: Any,
    max_attempts: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
    **kwargs: Any,
) -> Any:
    delay = base_delay
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt == max_attempts:
                raise
            time.sleep(delay)
            delay = min(delay * 2, max_delay)


@dataclass
class RateLimiter:
    max_calls: int = 10
    period: float = 1.0
    _calls: deque[float] = field(default_factory=deque)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def acquire(self) -> bool:
        now = time.monotonic()
        with self._lock:
            while self._calls and self._calls[0] <= now - self.period:
                self._calls.popleft()
            if len(self._calls) >= self.max_calls:
                return False
            self._calls.append(now)
            return True

    def __call__(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not self.acquire():
                raise RuntimeError("Rate limit exceeded")
            return fn(*args, **kwargs)

        return wrapper


@dataclass
class HealthCheck:
    name: str
    check_fn: Callable[[], bool]
    interval: float = 60.0
    _last_result: bool = True
    _last_run: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def run(self) -> bool:
        with self._lock:
            if time.monotonic() - self._last_run < self.interval:
                return self._last_result
            try:
                self._last_result = self.check_fn()
            except Exception:
                self._last_result = False
            self._last_run = time.monotonic()
            return self._last_result

    @property
    def healthy(self) -> bool:
        return self._last_result


@dataclass
class MetricsCollector:
    _counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _latencies: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += value

    def record_latency(self, name: str, seconds: float) -> None:
        with self._lock:
            self._latencies[name].append(seconds)

    def measure(self, name: str) -> Callable[..., Any]:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.monotonic()
                try:
                    return fn(*args, **kwargs)
                finally:
                    self.record_latency(name, time.monotonic() - start)

            return wrapper

        return decorator

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "latencies": {
                    k: {"count": len(v), "avg": sum(v) / len(v) if v else 0.0}
                    for k, v in self._latencies.items()
                },
            }
