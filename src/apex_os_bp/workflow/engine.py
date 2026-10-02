"""Workflow engine for APEX-OS Business Platform."""
from __future__ import annotations

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class WorkflowStatus(Enum):
    """Workflow status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_FOR_APPROVAL = "waiting_for_approval"


@dataclass
class WorkflowStep:
    """Workflow step."""
    name: str
    action: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    config: Dict = field(default_factory=dict)
    # Parallel execution
    parallel_group: Optional[str] = None
    # Conditional branching
    condition: Optional[Callable] = None
    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    # Error handling
    max_retries: int = 0
    retry_delay: float = 0.0
    # Human-in-the-loop
    requires_approval: bool = False
    # Results
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class Workflow:
    """Workflow definition."""
    name: str
    steps: List[WorkflowStep] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    version: str = "1.0.0"

    def add_step(self, step: WorkflowStep) -> None:
        """Add step to workflow."""
        self.steps.append(step)

    def get_step(self, name: str) -> Optional[WorkflowStep]:
        """Get step by name."""
        for step in self.steps:
            if step.name == name:
                return step
        return None


class WorkflowEngine:
    """Workflow execution engine."""

    def __init__(self, approval_callback: Optional[Callable] = None):
        self._workflows: Dict[str, Workflow] = {}
        self._versions: Dict[str, List[str]] = {}
        self._approval_callback = approval_callback

    def create_workflow(self, name: str, version: str = "1.0.0", **kwargs) -> Workflow:
        """Create a new workflow."""
        workflow = Workflow(name=name, version=version, **kwargs)
        key = f"{name}@{version}"
        self._workflows[key] = workflow
        if name not in self._versions:
            self._versions[name] = []
        if version not in self._versions[name]:
            self._versions[name].append(version)
        return workflow

    def get_workflow(self, name: str, version: Optional[str] = None) -> Optional[Workflow]:
        """Get workflow by name and optional version."""
        if version:
            return self._workflows.get(f"{name}@{version}")
        if name in self._versions and self._versions[name]:
            latest = self._versions[name][-1]
            return self._workflows.get(f"{name}@{latest}")
        return None

    def list_versions(self, name: str) -> List[str]:
        """List all versions of a workflow."""
        return self._versions.get(name, []).copy()

    def execute(self, name: str, version: Optional[str] = None, context: Optional[Dict] = None) -> Dict:
        """Execute workflow."""
        workflow = self.get_workflow(name, version)
        if not workflow:
            raise ValueError(f"Workflow not found: {name}")

        ctx = context or {}
        results = []
        executed: Set[str] = set()

        # Check conditions and group steps
        parallel_groups: Dict[str, List[WorkflowStep]] = {}
        for step in workflow.steps:
            if step.name in executed:
                continue

            if step.condition and not step.condition(ctx):
                step.status = WorkflowStatus.SKIPPED
                results.append(self._step_result(step))
                executed.add(step.name)
                continue

            if step.parallel_group:
                if step.parallel_group not in parallel_groups:
                    parallel_groups[step.parallel_group] = []
                parallel_groups[step.parallel_group].append(step)

        # Execute steps
        for step in workflow.steps:
            if step.name in executed:
                continue

            if step.parallel_group and step.parallel_group in parallel_groups:
                group = parallel_groups[step.parallel_group]
                group_results = self._execute_parallel(group, ctx)
                results.extend(group_results)
                for s in group:
                    executed.add(s.name)
                continue

            result = self._execute_step(step, ctx)
            results.append(result)
            executed.add(step.name)

            # Handle branching
            if step.status == WorkflowStatus.FAILED and step.on_failure:
                next_step = workflow.get_step(step.on_failure)
                if next_step and next_step.name not in executed:
                    result = self._execute_step(next_step, ctx)
                    results.append(result)
                    executed.add(next_step.name)
            elif step.status == WorkflowStatus.COMPLETED and step.on_success:
                next_step = workflow.get_step(step.on_success)
                if next_step and next_step.name not in executed:
                    result = self._execute_step(next_step, ctx)
                    results.append(result)
                    executed.add(next_step.name)

        # Determine overall status
        failed = any(r["status"] == "failed" for r in results)
        status = "failed" if failed else "completed"

        return {
            "workflow": name,
            "version": workflow.version,
            "status": status,
            "steps": results,
        }

    def _execute_step(self, step: WorkflowStep, ctx: Dict) -> Dict:
        """Execute a single step."""
        step.status = WorkflowStatus.RUNNING

        # Human-in-the-loop
        if step.requires_approval:
            step.status = WorkflowStatus.WAITING_FOR_APPROVAL
            if self._approval_callback:
                approved = self._approval_callback(step, ctx)
            else:
                approved = True
            if not approved:
                step.status = WorkflowStatus.SKIPPED
                return self._step_result(step)

        # Execute with retries
        for attempt in range(step.max_retries + 1):
            try:
                step.retry_count = attempt
                step.result = self._run_action(step, ctx)
                step.status = WorkflowStatus.COMPLETED
                step.error = None
                break
            except Exception as e:
                step.error = str(e)
                if attempt < step.max_retries:
                    time.sleep(step.retry_delay)
                else:
                    step.status = WorkflowStatus.FAILED

        return self._step_result(step)

    def _execute_parallel(self, steps: List[WorkflowStep], ctx: Dict) -> List[Dict]:
        """Execute steps in parallel."""
        results = []
        with ThreadPoolExecutor(max_workers=len(steps)) as executor:
            futures = {executor.submit(self._execute_step, step, ctx): step for step in steps}
            for future in as_completed(futures):
                results.append(future.result())
        return results

    def _run_action(self, step: WorkflowStep, ctx: Dict) -> Any:
        """Run an action."""
        fail_count = step.config.get("fail_count", 0)
        if fail_count > 0:
            step.config["fail_count"] = fail_count - 1
            raise RuntimeError(f"Action {step.action} failed (simulated)")
        return f"executed:{step.action}"

    def _step_result(self, step: WorkflowStep) -> Dict:
        """Get step result."""
        return {
            "step": step.name,
            "action": step.action,
            "status": step.status.value,
            "result": step.result,
            "error": step.error,
            "retry_count": step.retry_count,
        }
