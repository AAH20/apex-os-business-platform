"""API Orchestration — coordinate multi-step API calls with dependency resolution."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Optional


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class OrchestrationStep:
    name: str
    handler: Callable[..., Awaitable[Any]]
    depends_on: list[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    timeout: float = 30.0
    retries: int = 0
    max_retries: int = 3

    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


@dataclass
class OrchestrationResult:
    success: bool
    steps: dict[str, OrchestrationStep]
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    total_duration: float = 0.0

    @property
    def failed_steps(self) -> list[str]:
        return [name for name, s in self.steps.items() if s.status == StepStatus.FAILED]

    @property
    def completed_steps(self) -> list[str]:
        return [name for name, s in self.steps.items() if s.status == StepStatus.SUCCESS]


class APIOrchestrator:
    """Orchestrate multi-step API calls with dependency-aware execution."""

    def __init__(self, name: str = "default"):
        self.name = name
        self._steps: dict[str, OrchestrationStep] = {}
        self._results: dict[str, Any] = {}

    def add_step(self, step: OrchestrationStep) -> None:
        self._steps[step.name] = step

    def remove_step(self, name: str) -> None:
        self._steps.pop(name, None)

    def get_step(self, name: str) -> Optional[OrchestrationStep]:
        return self._steps.get(name)

    @property
    def steps(self) -> dict[str, OrchestrationStep]:
        return dict(self._steps)

    def _resolve_dependencies(self, step: OrchestrationStep) -> bool:
        """Check if all dependencies completed successfully."""
        for dep in step.depends_on:
            dep_step = self._steps.get(dep)
            if dep_step is None or dep_step.status != StepStatus.SUCCESS:
                return False
        return True

    def _get_execution_order(self) -> list[list[str]]:
        """Topological sort into parallel-executable layers."""
        resolved: set[str] = set()
        remaining = set(self._steps.keys())
        layers: list[list[str]] = []

        while remaining:
            layer = []
            for name in remaining:
                step = self._steps[name]
                if all(dep in resolved for dep in step.depends_on):
                    layer.append(name)
            if not layer:
                # Circular dependency — put all remaining in same layer
                layer = sorted(remaining)
            layers.append(layer)
            resolved.update(layer)
            remaining -= set(layer)

        return layers

    async def _execute_step(self, step: OrchestrationStep) -> None:
        step.status = StepStatus.RUNNING
        step.started_at = time.monotonic()

        for attempt in range(step.max_retries + 1):
            try:
                step.retries = attempt
                result = await asyncio.wait_for(
                    step.handler(self._results),
                    timeout=step.timeout,
                )
                step.result = result
                step.status = StepStatus.SUCCESS
                step.completed_at = time.monotonic()
                self._results[step.name] = result
                return
            except asyncio.TimeoutError:
                step.error = f"Timeout after {step.timeout}s (attempt {attempt + 1})"
            except Exception as exc:
                step.error = str(exc)

            if attempt < step.max_retries:
                await asyncio.sleep(0.1 * (2 ** attempt))

        step.status = StepStatus.FAILED
        step.completed_at = time.monotonic()

    async def execute(self) -> OrchestrationResult:
        """Execute all steps respecting dependencies."""
        start = time.monotonic()
        errors: list[str] = []

        for layer in self._get_execution_order():
            tasks = []
            for name in layer:
                step = self._steps[name]
                if not self._resolve_dependencies(step):
                    step.status = StepStatus.SKIPPED
                    errors.append(f"Step '{name}' skipped: dependencies not met")
                    continue
                tasks.append(self._execute_step(step))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        total_duration = time.monotonic() - start
        failed = [n for n, s in self._steps.items() if s.status == StepStatus.FAILED]
        errors.extend(f"Step '{n}' failed: {self._steps[n].error}" for n in failed)

        return OrchestrationResult(
            success=len(failed) == 0,
            steps=dict(self._steps),
            data=dict(self._results),
            errors=errors,
            total_duration=total_duration,
        )

    def reset(self) -> None:
        """Reset all steps to pending state."""
        for step in self._steps.values():
            step.status = StepStatus.PENDING
            step.result = None
            step.error = None
            step.started_at = None
            step.completed_at = None
            step.retries = 0
        self._results.clear()
