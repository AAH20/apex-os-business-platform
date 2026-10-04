"""Timeout handling for saga steps."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class TimeoutAction(Enum):
    """Action to take when a step times out."""
    FAIL = "fail"
    RETRY = "retry"
    COMPENSATE = "compensate"
    SKIP = "skip"


@dataclass
class TimeoutConfig:
    """Configuration for step timeouts."""
    step_timeout: float = 30.0  # per-step timeout in seconds
    saga_timeout: float = 300.0  # total saga timeout in seconds
    on_timeout: TimeoutAction = TimeoutAction.FAIL
    timeout_retries: int = 0  # additional retries on timeout


@dataclass
class TimeoutRecord:
    """Record of a timeout event."""
    step_name: str
    timeout_type: str  # "step" or "saga"
    duration: float
    action_taken: TimeoutAction
    timestamp: float = field(default_factory=lambda: __import__("time").time())


class TimeoutManager:
    """Manages timeouts for saga execution."""

    def __init__(self, config: Optional[TimeoutConfig] = None) -> None:
        self.config = config or TimeoutConfig()
        self._records: List[TimeoutRecord] = []
        self._step_start_times: Dict[str, float] = {}
        self._saga_start_time: Optional[float] = None
        self._lock = threading.Lock()

    def start_saga(self) -> None:
        """Mark the start of saga execution."""
        self._saga_start_time = __import__("time").time()

    def start_step(self, step_name: str) -> None:
        """Mark the start of a step."""
        self._step_start_times[step_name] = __import__("time").time()

    def check_step_timeout(self, step_name: str) -> Optional[TimeoutRecord]:
        """Check if the current step has exceeded its timeout."""
        start = self._step_start_times.get(step_name)
        if start is None:
            return None
        elapsed = __import__("time").time() - start
        if elapsed > self.config.step_timeout:
            record = TimeoutRecord(
                step_name=step_name,
                timeout_type="step",
                duration=elapsed,
                action_taken=self.config.on_timeout,
            )
            with self._lock:
                self._records.append(record)
            return record
        return None

    def check_saga_timeout(self) -> Optional[TimeoutRecord]:
        """Check if the overall saga has exceeded its timeout."""
        if self._saga_start_time is None:
            return None
        elapsed = __import__("time").time() - self._saga_start_time
        if elapsed > self.config.saga_timeout:
            record = TimeoutRecord(
                step_name="__saga__",
                timeout_type="saga",
                duration=elapsed,
                action_taken=self.config.on_timeout,
            )
            with self._lock:
                self._records.append(record)
            return record
        return None

    def get_step_elapsed(self, step_name: str) -> float:
        """Get elapsed time for a step."""
        start = self._step_start_times.get(step_name)
        if start is None:
            return 0.0
        return __import__("time").time() - start

    def get_saga_elapsed(self) -> float:
        """Get total elapsed time for the saga."""
        if self._saga_start_time is None:
            return 0.0
        return __import__("time").time() - self._saga_start_time

    def get_records(self) -> List[TimeoutRecord]:
        """Get all timeout records."""
        with self._lock:
            return list(self._records)

    def clear(self) -> None:
        """Clear all timeout state."""
        with self._lock:
            self._records.clear()
            self._step_start_times.clear()
            self._saga_start_time = None
