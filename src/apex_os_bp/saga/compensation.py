"""Compensation actions for saga steps."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class CompensationStatus(Enum):
    """Status of a compensation action."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CompensationResult:
    """Result of executing a compensation action."""
    step_name: str
    status: CompensationStatus
    result: Any = None
    error: Optional[str] = None
    attempts: int = 0
    duration: float = 0.0


# Type alias for compensation functions
CompensationFn = Callable[[Any, Dict[str, Any]], Any]


@dataclass
class CompensationAction:
    """A compensation action for a saga step."""
    step_name: str
    action: CompensationFn
    description: str = ""
    max_retries: int = 3
    retry_delay: float = 1.0
    # Context passed to the compensation function
    context: Dict[str, Any] = field(default_factory=dict)
    # Whether this compensation is idempotent (safe to retry)
    idempotent: bool = True
    # Whether to continue compensating other steps if this one fails
    continue_on_failure: bool = True

    def execute(self, step_result: Any) -> CompensationResult:
        """Execute the compensation action."""
        import time

        start = time.time()
        last_error: Optional[str] = None

        for attempt in range(self.max_retries + 1):
            try:
                result = self.action(step_result, self.context)
                return CompensationResult(
                    step_name=self.step_name,
                    status=CompensationStatus.SUCCEEDED,
                    result=result,
                    attempts=attempt + 1,
                    duration=time.time() - start,
                )
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "Compensation for step '%s' failed (attempt %d/%d): %s",
                    self.step_name,
                    attempt + 1,
                    self.max_retries + 1,
                    last_error,
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))

        return CompensationResult(
            step_name=self.step_name,
            status=CompensationStatus.FAILED,
            error=last_error,
            attempts=self.max_retries + 1,
            duration=time.time() - start,
        )


class CompensationRegistry:
    """Registry of compensation actions for saga steps."""

    def __init__(self) -> None:
        self._actions: Dict[str, CompensationAction] = {}

    def register(self, action: CompensationAction) -> None:
        """Register a compensation action for a step."""
        self._actions[action.step_name] = action

    def unregister(self, step_name: str) -> None:
        """Remove a compensation action."""
        self._actions.pop(step_name, None)

    def get(self, step_name: str) -> Optional[CompensationAction]:
        """Get the compensation action for a step."""
        return self._actions.get(step_name)

    def has_compensation(self, step_name: str) -> bool:
        """Check if a step has a registered compensation."""
        return step_name in self._actions

    def get_all(self) -> Dict[str, CompensationAction]:
        """Get all registered compensation actions."""
        return dict(self._actions)

    def clear(self) -> None:
        """Clear all registered compensations."""
        self._actions.clear()
