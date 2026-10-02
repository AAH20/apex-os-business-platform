"""Planning Module.

Provides task decomposition, step planning with dependency management,
and plan execution tracking.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class PlanStatus(str, Enum):
    """Status of a plan or plan step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """A single step in a plan."""

    description: str
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: PlanStatus = PlanStatus.PENDING
    dependencies: list[str] = field(default_factory=list)
    result: Any = None
    error: Optional[str] = None
    started_at: float = 0.0
    completed_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    assigned_agent: Optional[str] = None

    @property
    def duration(self) -> float:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return 0.0

    @property
    def is_ready(self) -> bool:
        """Check if step is ready to execute (no pending dependencies)."""
        return self.status == PlanStatus.PENDING

    def start(self) -> None:
        """Mark step as started."""
        self.status = PlanStatus.IN_PROGRESS
        self.started_at = time.time()

    def complete(self, result: Any = None) -> None:
        """Mark step as completed."""
        self.status = PlanStatus.COMPLETED
        self.result = result
        self.completed_at = time.time()

    def fail(self, error: str) -> None:
        """Mark step as failed."""
        self.status = PlanStatus.FAILED
        self.error = error
        self.completed_at = time.time()

    def block(self) -> None:
        """Mark step as blocked."""
        self.status = PlanStatus.BLOCKED

    def skip(self) -> None:
        """Mark step as skipped."""
        self.status = PlanStatus.SKIPPED


@dataclass
class Plan:
    """A plan consisting of multiple steps."""

    goal: str
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    steps: list[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        """Fraction of completed steps."""
        if not self.steps:
            return 0.0
        completed = sum(
            1 for s in self.steps if s.status == PlanStatus.COMPLETED
        )
        return completed / len(self.steps)

    @property
    def is_complete(self) -> bool:
        return all(
            s.status in (PlanStatus.COMPLETED, PlanStatus.SKIPPED)
            for s in self.steps
        )

    @property
    def has_failures(self) -> bool:
        return any(s.status == PlanStatus.FAILED for s in self.steps)

    def get_ready_steps(self) -> list[PlanStep]:
        """Get steps that are ready to execute."""
        completed_ids = {
            s.step_id
            for s in self.steps
            if s.status == PlanStatus.COMPLETED
        }
        ready = []
        for step in self.steps:
            if step.status != PlanStatus.PENDING:
                continue
            if all(dep in completed_ids for dep in step.dependencies):
                ready.append(step)
        return ready

    def get_step(self, step_id: str) -> Optional[PlanStep]:
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def add_step(self, step: PlanStep) -> None:
        self.steps.append(step)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "status": self.status.value,
            "progress": self.progress,
            "is_complete": self.is_complete,
            "steps": [
                {
                    "step_id": s.step_id,
                    "description": s.description,
                    "status": s.status.value,
                    "dependencies": s.dependencies,
                    "result": s.result,
                    "error": s.error,
                    "duration": s.duration,
                }
                for s in self.steps
            ],
        }


class Planner:
    """Creates and manages execution plans.

    Decomposes goals into steps, manages dependencies,
    and tracks plan execution.
    """

    def __init__(self) -> None:
        self._plans: dict[str, Plan] = {}

    def create_plan(
        self,
        goal: str,
        steps: list[PlanStep] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Plan:
        """Create a new plan."""
        plan = Plan(
            goal=goal,
            steps=steps or [],
            metadata=metadata or {},
        )
        self._plans[plan.plan_id] = plan
        return plan

    def decompose(
        self,
        goal: str,
        sub_tasks: list[str],
        dependencies: dict[int, list[int]] | None = None,
    ) -> Plan:
        """Decompose a goal into a plan with steps and dependencies.

        Args:
            goal: The overall goal.
            sub_tasks: List of sub-task descriptions.
            dependencies: Mapping from step index to list of dependency indices.
        """
        steps: list[PlanStep] = []
        for i, desc in enumerate(sub_tasks):
            deps: list[str] = []
            if dependencies and i in dependencies:
                for dep_idx in dependencies[i]:
                    if dep_idx < len(steps):
                        deps.append(steps[dep_idx].step_id)
            steps.append(PlanStep(description=desc, dependencies=deps))

        return self.create_plan(goal=goal, steps=steps)

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        return self._plans.get(plan_id)

    def list_plans(self) -> list[Plan]:
        return list(self._plans.values())

    def get_execution_order(self, plan_id: str) -> list[PlanStep]:
        """Get steps in topological execution order."""
        plan = self._plans.get(plan_id)
        if not plan:
            return []

        ordered: list[PlanStep] = []
        remaining = list(plan.steps)
        completed: set[str] = set()

        while remaining:
            progress = False
            for step in list(remaining):
                if all(dep in completed for dep in step.dependencies):
                    ordered.append(step)
                    completed.add(step.step_id)
                    remaining.remove(step)
                    progress = True
            if not progress:
                # Circular dependency — append remaining as-is
                ordered.extend(remaining)
                break

        return ordered

    def execute_plan(
        self,
        plan_id: str,
        step_executor: Any,
    ) -> Plan:
        """Execute a plan step by step.

        Args:
            plan_id: The plan to execute.
            step_executor: A callable that takes a PlanStep and returns a result.
        """
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan '{plan_id}' not found")

        plan.status = PlanStatus.IN_PROGRESS
        order = self.get_execution_order(plan_id)

        for step in order:
            if step.status != PlanStatus.PENDING:
                continue
            step.start()
            try:
                result = step_executor(step)
                step.complete(result)
            except Exception as exc:
                step.fail(str(exc))

        if plan.is_complete:
            plan.status = PlanStatus.COMPLETED
        elif plan.has_failures:
            plan.status = PlanStatus.FAILED
        plan.completed_at = time.time()
        return plan

    def cancel_plan(self, plan_id: str) -> bool:
        """Cancel a plan and all its pending steps."""
        plan = self._plans.get(plan_id)
        if not plan:
            return False
        plan.status = PlanStatus.FAILED
        for step in plan.steps:
            if step.status == PlanStatus.PENDING:
                step.status = PlanStatus.SKIPPED
        return True

    def clear(self) -> None:
        self._plans.clear()
