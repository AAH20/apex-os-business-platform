"""
Deepened workflow module for APEX-OS Business Platform.

Adds: parallel execution (fork/join), conditional branching,
sub-workflow composition, versioning with rollback, and analytics
with bottleneck detection.
"""

from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ── Core types ──────────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class WorkflowContext:
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.variables[key] = value


# ── 1. Parallel task execution (fork/join) ──────────────────────────────────

class ParallelTask:
    """Fork N tasks concurrently, join on completion."""

    def __init__(self, name: str, tasks: List[Callable], max_workers: int = 4):
        self.name = name
        self.tasks = tasks
        self.max_workers = max_workers

    def execute(self, ctx: WorkflowContext) -> List[TaskResult]:
        results: List[TaskResult] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(self._run, f"{self.name}-{i}", fn, ctx): i
                for i, fn in enumerate(self.tasks)
            }
            for future in as_completed(futures):
                results.append(future.result())
        results.sort(key=lambda r: r.task_id)
        return results

    @staticmethod
    def _run(tid: str, fn: Callable, ctx: WorkflowContext) -> TaskResult:
        t0 = time.monotonic()
        try:
            out = fn(ctx)
            return TaskResult(tid, TaskStatus.COMPLETED, output=out, duration_ms=(time.monotonic() - t0) * 1000)
        except Exception as exc:
            return TaskResult(tid, TaskStatus.FAILED, error=str(exc), duration_ms=(time.monotonic() - t0) * 1000)


# ── 2. Conditional branching with expressions ──────────────────────────────

class ConditionalBranch:
    """Pick a branch by evaluating boolean expressions against context."""

    def __init__(self, name: str, conditions: List[Tuple[str, Callable]], default: Optional[Callable] = None):
        self.name = name
        self.conditions = conditions
        self.default = default

    def execute(self, ctx: WorkflowContext) -> TaskResult:
        t0 = time.monotonic()
        for expr, fn in self.conditions:
            if self._eval(expr, ctx):
                return self._invoke(fn, ctx, t0)
        if self.default:
            return self._invoke(self.default, ctx, t0)
        return TaskResult(self.name, TaskStatus.SKIPPED, duration_ms=(time.monotonic() - t0) * 1000)

    def _invoke(self, fn: Callable, ctx: WorkflowContext, t0: float) -> TaskResult:
        try:
            out = fn(ctx)
            return TaskResult(self.name, TaskStatus.COMPLETED, output=out, duration_ms=(time.monotonic() - t0) * 1000)
        except Exception as exc:
            return TaskResult(self.name, TaskStatus.FAILED, error=str(exc), duration_ms=(time.monotonic() - t0) * 1000)

    @staticmethod
    def _eval(expr: str, ctx: WorkflowContext) -> bool:
        try:
            return bool(eval(expr, {"__builtins__": {}}, dict(ctx.variables)))
        except Exception:
            return False


# ── 3. Sub-workflow composition ─────────────────────────────────────────────

class SubWorkflow:
    """Execute a nested sequence of steps as a child workflow."""

    def __init__(self, name: str, steps: List[Callable]):
        self.name = name
        self.steps = steps

    def execute(self, ctx: WorkflowContext) -> TaskResult:
        t0 = time.monotonic()
        sub = WorkflowContext(variables=dict(ctx.variables), metadata={"parent": ctx.execution_id})
        outputs: List[Any] = []
        for step in self.steps:
            res = step(sub)
            outputs.append(res)
            if isinstance(res, TaskResult) and res.status == TaskStatus.FAILED:
                return TaskResult(self.name, TaskStatus.FAILED, output=outputs, error=res.error, duration_ms=(time.monotonic() - t0) * 1000)
        ctx.variables.update(sub.variables)
        return TaskResult(self.name, TaskStatus.COMPLETED, output=outputs, duration_ms=(time.monotonic() - t0) * 1000)


# ── 4. Workflow versioning with rollback ────────────────────────────────────

@dataclass
class WorkflowSnapshot:
    version: int
    state: Dict[str, Any]
    timestamp: float
    label: str = ""


class VersionedWorkflow:
    """Snapshot-based versioning with rollback and diff."""

    def __init__(self, name: str):
        self.name = name
        self._versions: List[WorkflowSnapshot] = []
        self._current: int = 0

    def snapshot(self, state: Dict[str, Any], label: str = "") -> int:
        self._current += 1
        self._versions.append(WorkflowSnapshot(self._current, dict(state), time.time(), label))
        return self._current

    def rollback(self, version: int) -> Optional[Dict[str, Any]]:
        for snap in self._versions:
            if snap.version == version:
                self._current = version
                return dict(snap.state)
        return None

    def diff(self, v1: int, v2: int) -> Dict[str, Any]:
        s1 = next((s for s in self._versions if s.version == v1), None)
        s2 = next((s for s in self._versions if s.version == v2), None)
        if not s1 or not s2:
            return {}
        keys = set(s1.state) | set(s2.state)
        return {k: {"old": s1.state.get(k), "new": s2.state.get(k)} for k in keys if s1.state.get(k) != s2.state.get(k)}

    @property
    def current_version(self) -> int:
        return self._current

    @property
    def version_count(self) -> int:
        return len(self._versions)


# ── 5. Workflow analytics with bottleneck detection ─────────────────────────

@dataclass
class StepMetric:
    step_name: str
    duration_ms: float
    status: TaskStatus
    timestamp: float = field(default_factory=time.time)


class WorkflowAnalytics:
    """Track per-step metrics; flag bottlenecks and slowest steps."""

    def __init__(self, bottleneck_threshold_ms: float = 1000.0):
        self.threshold = bottleneck_threshold_ms
        self._metrics: List[StepMetric] = []

    def record(self, step_name: str, duration_ms: float, status: TaskStatus = TaskStatus.COMPLETED) -> None:
        self._metrics.append(StepMetric(step_name, duration_ms, status))

    def record_result(self, result: TaskResult) -> None:
        self._metrics.append(StepMetric(result.task_id, result.duration_ms, result.status))

    def bottlenecks(self) -> List[StepMetric]:
        return [m for m in self._metrics if m.duration_ms >= self.threshold]

    def slowest(self, n: int = 5) -> List[StepMetric]:
        return sorted(self._metrics, key=lambda m: m.duration_ms, reverse=True)[:n]

    def avg_duration(self) -> float:
        return sum(m.duration_ms for m in self._metrics) / len(self._metrics) if self._metrics else 0.0

    def failure_rate(self) -> float:
        if not self._metrics:
            return 0.0
        return sum(1 for m in self._metrics if m.status == TaskStatus.FAILED) / len(self._metrics)

    def summary(self) -> Dict[str, Any]:
        return {
            "total_steps": len(self._metrics),
            "avg_duration_ms": self.avg_duration(),
            "failure_rate": self.failure_rate(),
            "bottlenecks": [{"step": m.step_name, "ms": m.duration_ms} for m in self.bottlenecks()],
            "slowest": [{"step": m.step_name, "ms": m.duration_ms} for m in self.slowest()],
        }

    def reset(self) -> None:
        self._metrics.clear()
