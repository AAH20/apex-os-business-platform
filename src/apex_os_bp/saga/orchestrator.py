"""Saga orchestrator for APEX-OS Business Platform."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from apex_os_bp.saga.compensation import (
    CompensationAction,
    CompensationRegistry,
    CompensationResult,
    CompensationStatus,
)
from apex_os_bp.saga.retry import RetryExecutor, RetryPolicy
from apex_os_bp.saga.state_machine import SagaState, SagaStateMachine, SagaStepState
from apex_os_bp.saga.timeout import TimeoutAction, TimeoutConfig, TimeoutManager

logger = logging.getLogger(__name__)


class SagaStepStatus(Enum):
    """High-level status of a saga step."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    COMPENSATED = "compensated"
    SKIPPED = "skipped"


@dataclass
class SagaStep:
    """A single step in a saga."""
    name: str
    action: Callable[..., Any]
    compensation: Optional[CompensationAction] = None
    retry_policy: Optional[RetryPolicy] = None
    timeout: Optional[float] = None  # override default timeout
    # Whether to skip this step if a previous step failed
    skip_on_failure: bool = True
    # Dependencies: step names that must complete before this one
    depends_on: Optional[List[str]] = None
    # Context passed to the action
    context: Dict[str, Any] = field(default_factory=dict)
    # Runtime state
    result: Any = None
    error: Optional[str] = None
    status: SagaStepStatus = SagaStepStatus.PENDING
    attempts: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    compensation_result: Optional[CompensationResult] = None


@dataclass
class SagaResult:
    """Result of a saga execution."""
    saga_name: str
    state: SagaState
    steps: Dict[str, SagaStepStatus]
    step_results: Dict[str, Any]
    errors: Dict[str, str]
    compensation_results: Dict[str, CompensationResult]
    start_time: float
    end_time: float
    duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.state == SagaState.COMPLETED

    @property
    def compensated(self) -> bool:
        return self.state in {SagaState.COMPENSATED, SagaState.PARTIALLY_COMPENSATED}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "saga_name": self.saga_name,
            "state": self.state.value,
            "steps": {k: v.value for k, v in self.steps.items()},
            "step_results": self.step_results,
            "errors": self.errors,
            "compensation_results": {
                k: {
                    "step_name": v.step_name,
                    "status": v.status.value,
                    "error": v.error,
                    "attempts": v.attempts,
                    "duration": v.duration,
                }
                for k, v in self.compensation_results.items()
            },
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "metadata": self.metadata,
        }


class SagaOrchestrator:
    """Orchestrates the execution of a saga with compensation, retry, and timeout support."""

    def __init__(
        self,
        name: str,
        steps: List[SagaStep],
        timeout_config: Optional[TimeoutConfig] = None,
        compensation_registry: Optional[CompensationRegistry] = None,
        continue_on_compensation_failure: bool = False,
        parallel: bool = False,
        max_parallel: int = 4,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.name = name
        self.steps = steps
        self.step_map: Dict[str, SagaStep] = {s.name: s for s in steps}
        self.timeout_manager = TimeoutManager(timeout_config)
        self.compensation_registry = compensation_registry or CompensationRegistry()
        self.continue_on_compensation_failure = continue_on_compensation_failure
        self.parallel = parallel
        self.max_parallel = max_parallel
        self.metadata = metadata or {}
        self.state_machine = SagaStateMachine()
        self._lock = threading.RLock()
        self._stop_event = threading.Event()

        # Register compensations from steps
        for step in steps:
            if step.compensation:
                self.compensation_registry.register(step.compensation)

    def stop(self) -> None:
        """Signal the orchestrator to stop."""
        self._stop_event.set()

    def execute(self) -> SagaResult:
        """Execute the saga."""
        start_time = time.time()
        self.timeout_manager.start_saga()

        # Transition to RUNNING
        self.state_machine.transition_saga(SagaState.RUNNING, reason="Saga started")

        errors: Dict[str, str] = {}
        step_results: Dict[str, Any] = {}
        compensation_results: Dict[str, CompensationResult] = {}

        try:
            if self.parallel:
                self._execute_parallel(start_time, errors, step_results)
            else:
                self._execute_sequential(start_time, errors, step_results)
        except Exception as e:
            logger.exception("Saga '%s' encountered an unexpected error", self.name)
            errors["__orchestrator__"] = str(e)

        # Determine final state
        final_state = self.state_machine.saga_state

        # If we need to compensate
        if final_state == SagaState.COMPENSATING:
            comp_results = self._compensate(errors)
            compensation_results.update(comp_results)

            # Determine compensation outcome
            all_compensated = all(
                r.status == CompensationStatus.SUCCEEDED for r in comp_results.values()
            )
            any_failed = any(
                r.status == CompensationStatus.FAILED for r in comp_results.values()
            )

            if all_compensated:
                self.state_machine.transition_saga(
                    SagaState.COMPENSATED, reason="All compensations succeeded"
                )
            elif any_failed:
                self.state_machine.transition_saga(
                    SagaState.PARTIALLY_COMPENSATED,
                    reason="Some compensations failed",
                )
            else:
                self.state_machine.transition_saga(
                    SagaState.COMPENSATED, reason="No compensations needed"
                )

        end_time = time.time()

        # Build step status map
        step_statuses: Dict[str, SagaStepStatus] = {}
        for step in self.steps:
            step_statuses[step.name] = step.status

        return SagaResult(
            saga_name=self.name,
            state=self.state_machine.saga_state,
            steps=step_statuses,
            step_results=step_results,
            errors=errors,
            compensation_results=compensation_results,
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            metadata=self.metadata,
        )

    def _execute_sequential(
        self,
        start_time: float,
        errors: Dict[str, str],
        step_results: Dict[str, Any],
    ) -> None:
        """Execute steps sequentially."""
        for step in self.steps:
            if self._stop_event.is_set():
                logger.info("Saga '%s' stopped by request", self.name)
                self.state_machine.transition_saga(SagaState.FAILED, reason="Stopped by request")
                return

            # Check saga timeout
            timeout_record = self.timeout_manager.check_saga_timeout()
            if timeout_record:
                logger.warning("Saga '%s' timed out", self.name)
                self.state_machine.transition_saga(SagaState.TIMED_OUT, reason="Saga timeout")
                self._handle_timeout()
                return

            # Check dependencies
            if step.depends_on:
                deps_satisfied = all(
                    self.step_map[dep].status == SagaStepStatus.SUCCEEDED
                    for dep in step.depends_on
                    if dep in self.step_map
                )
                if not deps_satisfied:
                    step.status = SagaStepStatus.SKIPPED
                    self.state_machine.transition_step(
                        step.name, SagaStepState.SKIPPED, reason="Dependencies not met"
                    )
                    continue

            # Execute the step
            success = self._execute_step(step, errors, step_results)

            if not success:
                step.status = SagaStepStatus.FAILED
                self.state_machine.transition_step(
                    step.name, SagaStepState.FAILED, reason=step.error or "Step failed"
                )

                # Mark remaining steps as skipped
                for remaining_step in self.steps:
                    if remaining_step.status == SagaStepStatus.PENDING:
                        remaining_step.status = SagaStepStatus.SKIPPED

                # Check if there are any succeeded steps to compensate
                has_compensations = any(
                    s.status == SagaStepStatus.SUCCEEDED for s in self.steps
                )

                if has_compensations:
                    # Start compensation
                    self.state_machine.transition_saga(
                        SagaState.COMPENSATING,
                        reason=f"Step '{step.name}' failed, starting compensation",
                    )
                else:
                    # No compensations needed, go directly to FAILED
                    self.state_machine.transition_saga(
                        SagaState.FAILED,
                        reason=f"Step '{step.name}' failed",
                    )
                return

            # Check if stop event is set after step completes
            if self._stop_event.is_set():
                logger.info("Saga '%s' stopped by request", self.name)
                self.state_machine.transition_saga(SagaState.FAILED, reason="Stopped by request")
                return
            else:
                step.status = SagaStepStatus.SUCCEEDED
                self.state_machine.transition_step(
                    step.name, SagaStepState.SUCCEEDED, reason="Step completed"
                )

        # All steps succeeded
        self.state_machine.transition_saga(SagaState.COMPLETED, reason="All steps completed")

    def _execute_parallel(
        self,
        start_time: float,
        errors: Dict[str, str],
        step_results: Dict[str, Any],
    ) -> None:
        """Execute steps in parallel."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            futures = {}
            for step in self.steps:
                if self._stop_event.is_set():
                    break
                future = executor.submit(self._execute_step_safe, step, errors, step_results)
                futures[future] = step

            for future in as_completed(futures):
                step = futures[future]
                try:
                    success = future.result()
                    if success:
                        step.status = SagaStepStatus.SUCCEEDED
                        self.state_machine.transition_step(
                            step.name, SagaStepState.SUCCEEDED
                        )
                    else:
                        step.status = SagaStepStatus.FAILED
                        self.state_machine.transition_step(
                            step.name, SagaStepState.FAILED
                        )
                except Exception as e:
                    step.status = SagaStepStatus.FAILED
                    step.error = str(e)
                    errors[step.name] = str(e)
                    self.state_machine.transition_step(
                        step.name, SagaStepState.FAILED, reason=str(e)
                    )

        # Check if any step failed
        any_failed = any(s.status == SagaStepStatus.FAILED for s in self.steps)
        if any_failed:
            self.state_machine.transition_saga(
                SagaState.COMPENSATING, reason="Some parallel steps failed"
            )
        else:
            self.state_machine.transition_saga(
                SagaState.COMPLETED, reason="All parallel steps completed"
            )

    def _execute_step_safe(
        self,
        step: SagaStep,
        errors: Dict[str, str],
        step_results: Dict[str, Any],
    ) -> bool:
        """Thread-safe wrapper for _execute_step."""
        with self._lock:
            return self._execute_step(step, errors, step_results)

    def _execute_step(
        self,
        step: SagaStep,
        errors: Dict[str, str],
        step_results: Dict[str, Any],
    ) -> bool:
        """Execute a single step with retry and timeout support."""
        step.start_time = time.time()
        step.status = SagaStepStatus.RUNNING
        self.state_machine.transition_step(
            step.name, SagaStepState.RUNNING, reason="Step started"
        )
        self.timeout_manager.start_step(step.name)

        # Build retry policy
        retry_policy = step.retry_policy or RetryPolicy(max_retries=0)
        retry_executor = RetryExecutor(retry_policy)

        # Determine timeout
        step_timeout = step.timeout or self.timeout_manager.config.step_timeout

        # Execute with retry and timeout
        success, result, error = retry_executor.execute_with_timeout(
            step.action, step_timeout, **step.context
        )

        step.end_time = time.time()
        step.attempts = retry_policy.max_retries + 1  # simplified

        if success:
            step.result = result
            step_results[step.name] = result
            return True
        else:
            step.error = str(error) if error else "Unknown error"
            errors[step.name] = step.error

            # Check if this was a timeout
            if error and "TimeoutError" in type(error).__name__:
                self.state_machine.transition_step(
                    step.name, SagaStepState.TIMED_OUT, reason="Step timed out"
                )
                # Check if we should retry on timeout
                if self.timeout_manager.config.on_timeout == TimeoutAction.RETRY:
                    return self._execute_step(step, errors, step_results)

            return False

    def _handle_timeout(self) -> None:
        """Handle saga timeout."""
        action = self.timeout_manager.config.on_timeout
        if action == TimeoutAction.COMPENSATE:
            self.state_machine.transition_saga(
                SagaState.COMPENSATING, reason="Timeout triggered compensation"
            )
        elif action == TimeoutAction.FAIL:
            self.state_machine.transition_saga(
                SagaState.FAILED, reason="Timeout triggered failure"
            )

    def _compensate(
        self, errors: Dict[str, str]
    ) -> Dict[str, CompensationResult]:
        """Run compensation for all succeeded steps in reverse order."""
        results: Dict[str, CompensationResult] = {}

        # Get succeeded steps in reverse order
        succeeded_steps = [
            s for s in reversed(self.steps) if s.status == SagaStepStatus.SUCCEEDED
        ]

        for step in succeeded_steps:
            comp_action = self.compensation_registry.get(step.name)
            if not comp_action:
                # Try the step's own compensation
                if step.compensation:
                    comp_action = step.compensation
                else:
                    logger.debug("No compensation for step '%s', skipping", step.name)
                    continue

            step.status = SagaStepStatus.COMPENSATED
            self.state_machine.transition_step(
                step.name, SagaStepState.COMPENSATING, reason="Starting compensation"
            )

            result = comp_action.execute(step.result)
            step.compensation_result = result
            results[step.name] = result

            if result.status == CompensationStatus.SUCCEEDED:
                self.state_machine.transition_step(
                    step.name,
                    SagaStepState.COMPENSATED,
                    reason="Compensation succeeded",
                )
            else:
                self.state_machine.transition_step(
                    step.name,
                    SagaStepState.COMPENSATION_FAILED,
                    reason=f"Compensation failed: {result.error}",
                )
                if not self.continue_on_compensation_failure:
                    logger.error(
                        "Compensation for step '%s' failed and continue_on_compensation_failure is False",
                        step.name,
                    )
                    break

        return results


def create_saga(
    name: str,
    steps: List[SagaStep],
    **kwargs: Any,
) -> SagaOrchestrator:
    """Factory function to create a saga orchestrator."""
    return SagaOrchestrator(name=name, steps=steps, **kwargs)
