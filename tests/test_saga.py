"""Tests for the saga pattern system."""
from __future__ import annotations

import time
import threading
import pytest

from apex_os_bp.saga import (
    BackoffStrategy,
    CompensationAction,
    CompensationRegistry,
    CompensationStatus,
    RetryExecutor,
    RetryPolicy,
    SagaOrchestrator,
    SagaResult,
    SagaState,
    SagaStateMachine,
    SagaStep,
    SagaStepState,
    SagaStepStatus,
    TimeoutAction,
    TimeoutConfig,
    TimeoutManager,
    create_saga,
)


# ============================================================================
# State Machine Tests
# ============================================================================


class TestSagaStateMachine:
    """Tests for the saga state machine."""

    def test_initial_state(self):
        sm = SagaStateMachine()
        assert sm.saga_state == SagaState.PENDING

    def test_valid_saga_transitions(self):
        sm = SagaStateMachine()
        assert sm.transition_saga(SagaState.RUNNING, "start")
        assert sm.saga_state == SagaState.RUNNING
        assert sm.transition_saga(SagaState.COMPLETED, "done")
        assert sm.saga_state == SagaState.COMPLETED

    def test_invalid_saga_transition(self):
        sm = SagaStateMachine()
        # Cannot go from PENDING to COMPLETED directly
        assert not sm.transition_saga(SagaState.COMPLETED)
        assert sm.saga_state == SagaState.PENDING

    def test_terminal_state_no_transitions(self):
        sm = SagaStateMachine()
        sm.transition_saga(SagaState.RUNNING)
        sm.transition_saga(SagaState.COMPLETED)
        # COMPLETED is terminal - no further transitions
        assert not sm.transition_saga(SagaState.RUNNING)
        assert sm.saga_state == SagaState.COMPLETED

    def test_step_transitions(self):
        sm = SagaStateMachine()
        assert sm.transition_step("step1", SagaStepState.RUNNING)
        assert sm.get_step_state("step1") == SagaStepState.RUNNING
        assert sm.transition_step("step1", SagaStepState.SUCCEEDED)
        assert sm.get_step_state("step1") == SagaStepState.SUCCEEDED

    def test_invalid_step_transition(self):
        sm = SagaStateMachine()
        # Cannot go from PENDING to SUCCEEDED directly
        assert not sm.transition_step("step1", SagaStepState.SUCCEEDED)
        assert sm.get_step_state("step1") == SagaStepState.PENDING

    def test_transition_history(self):
        sm = SagaStateMachine()
        sm.transition_saga(SagaState.RUNNING, "start")
        sm.transition_step("s1", SagaStepState.RUNNING)
        sm.transition_step("s1", SagaStepState.SUCCEEDED)
        sm.transition_saga(SagaState.COMPLETED, "done")

        history = sm.get_saga_history()
        assert len(history) == 4
        assert history[0]["from"] == "pending"
        assert history[0]["to"] == "running"
        assert history[3]["to"] == "completed"

    def test_is_saga_terminal(self):
        sm = SagaStateMachine()
        assert not sm.is_saga_terminal()
        sm.transition_saga(SagaState.RUNNING)
        assert not sm.is_saga_terminal()
        sm.transition_saga(SagaState.COMPLETED)
        assert sm.is_saga_terminal()

    def test_is_step_terminal(self):
        sm = SagaStateMachine()
        assert not sm.is_step_terminal("s1")
        sm.transition_step("s1", SagaStepState.RUNNING)
        assert not sm.is_step_terminal("s1")
        sm.transition_step("s1", SagaStepState.SUCCEEDED)
        assert not sm.is_step_terminal("s1")
        sm.transition_step("s1", SagaStepState.COMPENSATING)
        sm.transition_step("s1", SagaStepState.COMPENSATED)
        assert sm.is_step_terminal("s1")

    def test_compensating_transition(self):
        sm = SagaStateMachine()
        sm.transition_saga(SagaState.RUNNING)
        assert sm.transition_saga(SagaState.COMPENSATING, "failure")
        assert sm.saga_state == SagaState.COMPENSATING
        assert sm.transition_saga(SagaState.COMPENSATED, "compensated")
        assert sm.saga_state == SagaState.COMPENSATED

    def test_partially_compensated(self):
        sm = SagaStateMachine()
        sm.transition_saga(SagaState.RUNNING)
        sm.transition_saga(SagaState.COMPENSATING)
        assert sm.transition_saga(SagaState.PARTIALLY_COMPENSATED)
        assert sm.saga_state == SagaState.PARTIALLY_COMPENSATED

    def test_timed_out_state(self):
        sm = SagaStateMachine()
        sm.transition_saga(SagaState.RUNNING)
        assert sm.transition_saga(SagaState.TIMED_OUT, "timeout")
        assert sm.saga_state == SagaState.TIMED_OUT
        # Can still compensate after timeout
        assert sm.transition_saga(SagaState.COMPENSATING)
        assert sm.saga_state == SagaState.COMPENSATING


# ============================================================================
# Retry Policy Tests
# ============================================================================


class TestRetryPolicy:
    """Tests for retry policies."""

    def test_fixed_backoff(self):
        policy = RetryPolicy(
            max_retries=3,
            initial_delay=2.0,
            backoff_strategy=BackoffStrategy.FIXED,
        )
        assert policy.get_delay(0) == 2.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 2.0

    def test_linear_backoff(self):
        policy = RetryPolicy(
            max_retries=3,
            initial_delay=1.0,
            backoff_strategy=BackoffStrategy.LINEAR,
        )
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 3.0

    def test_exponential_backoff(self):
        policy = RetryPolicy(
            max_retries=3,
            initial_delay=1.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            multiplier=2.0,
        )
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0

    def test_exponential_with_jitter(self):
        policy = RetryPolicy(
            max_retries=3,
            initial_delay=1.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL_WITH_JITTER,
            multiplier=2.0,
            jitter_factor=0.1,
        )
        # Jitter should keep delay close to base
        for i in range(10):
            delay = policy.get_delay(0)
            assert 0.9 <= delay <= 1.1

    def test_max_delay_cap(self):
        policy = RetryPolicy(
            max_retries=10,
            initial_delay=1.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            multiplier=2.0,
            max_delay=5.0,
        )
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0
        assert policy.get_delay(3) == 5.0  # capped
        assert policy.get_delay(10) == 5.0  # capped

    def test_should_retry_within_limit(self):
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry(0, Exception("fail"))
        assert policy.should_retry(1, Exception("fail"))
        assert policy.should_retry(2, Exception("fail"))
        assert not policy.should_retry(3, Exception("fail"))

    def test_non_retryable_exceptions(self):
        policy = RetryPolicy(
            max_retries=3,
            non_retryable_exceptions={ValueError},
        )
        assert not policy.should_retry(0, ValueError("bad"))
        assert policy.should_retry(0, RuntimeError("bad"))

    def test_retryable_exceptions_whitelist(self):
        policy = RetryPolicy(
            max_retries=3,
            retryable_exceptions={ConnectionError, TimeoutError},
        )
        assert policy.should_retry(0, ConnectionError("fail"))
        assert policy.should_retry(0, TimeoutError("fail"))
        assert not policy.should_retry(0, ValueError("fail"))


class TestRetryExecutor:
    """Tests for the retry executor."""

    def test_successful_execution(self):
        executor = RetryExecutor(RetryPolicy(max_retries=3))
        success, result, error = executor.execute(lambda: 42)
        assert success
        assert result == 42
        assert error is None

    def test_retry_then_success(self):
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("temporary")
            return "ok"

        policy = RetryPolicy(max_retries=3, initial_delay=0.01)
        executor = RetryExecutor(policy)
        success, result, error = executor.execute(flaky)
        assert success
        assert result == "ok"
        assert call_count == 3

    def test_retry_exhausted(self):
        call_count = 0

        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("permanent")

        policy = RetryPolicy(max_retries=2, initial_delay=0.01)
        executor = RetryExecutor(policy)
        success, result, error = executor.execute(always_fails)
        assert not success
        assert result is None
        assert error is not None
        assert call_count == 3  # initial + 2 retries

    def test_no_retry_for_non_retryable(self):
        call_count = 0

        def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("bad")

        policy = RetryPolicy(
            max_retries=3,
            non_retryable_exceptions={ValueError},
            initial_delay=0.01,
        )
        executor = RetryExecutor(policy)
        success, result, error = executor.execute(raises_value_error)
        assert not success
        assert call_count == 1  # no retries

    def test_on_retry_callback(self):
        retries = []

        def on_retry(attempt, delay, exception):
            retries.append((attempt, delay, str(exception)))

        policy = RetryPolicy(max_retries=2, initial_delay=0.01, on_retry=on_retry)
        executor = RetryExecutor(policy)
        executor.execute(lambda: (_ for _ in ()).throw(ConnectionError("fail")))
        assert len(retries) == 2
        assert retries[0][0] == 1
        assert retries[1][0] == 2

    def test_execute_with_timeout(self):
        def slow_function():
            time.sleep(10)
            return "done"

        executor = RetryExecutor(RetryPolicy(max_retries=0))
        success, result, error = executor.execute_with_timeout(slow_function, 0.1)
        assert not success
        assert result is None
        assert error is not None

    def test_execute_with_timeout_success(self):
        def fast_function():
            return "quick"

        executor = RetryExecutor(RetryPolicy(max_retries=0))
        success, result, error = executor.execute_with_timeout(fast_function, 5.0)
        assert success
        assert result == "quick"
        assert error is None


# ============================================================================
# Timeout Manager Tests
# ============================================================================


class TestTimeoutManager:
    """Tests for timeout management."""

    def test_step_timeout(self):
        config = TimeoutConfig(step_timeout=0.1)
        tm = TimeoutManager(config)
        tm.start_step("step1")
        time.sleep(0.15)
        record = tm.check_step_timeout("step1")
        assert record is not None
        assert record.step_name == "step1"
        assert record.timeout_type == "step"
        assert record.action_taken == TimeoutAction.FAIL

    def test_no_timeout_within_limit(self):
        config = TimeoutConfig(step_timeout=10.0)
        tm = TimeoutManager(config)
        tm.start_step("step1")
        record = tm.check_step_timeout("step1")
        assert record is None

    def test_saga_timeout(self):
        config = TimeoutConfig(saga_timeout=0.1)
        tm = TimeoutManager(config)
        tm.start_saga()
        time.sleep(0.15)
        record = tm.check_saga_timeout()
        assert record is not None
        assert record.timeout_type == "saga"

    def test_no_saga_timeout(self):
        config = TimeoutConfig(saga_timeout=10.0)
        tm = TimeoutManager(config)
        tm.start_saga()
        record = tm.check_saga_timeout()
        assert record is None

    def test_get_step_elapsed(self):
        config = TimeoutConfig()
        tm = TimeoutManager(config)
        tm.start_step("step1")
        time.sleep(0.05)
        elapsed = tm.get_step_elapsed("step1")
        assert elapsed >= 0.05

    def test_get_saga_elapsed(self):
        config = TimeoutConfig()
        tm = TimeoutManager(config)
        tm.start_saga()
        time.sleep(0.05)
        elapsed = tm.get_saga_elapsed()
        assert elapsed >= 0.05

    def test_clear(self):
        config = TimeoutConfig(step_timeout=0.1)
        tm = TimeoutManager(config)
        tm.start_saga()
        tm.start_step("step1")
        time.sleep(0.15)
        tm.check_step_timeout("step1")
        assert len(tm.get_records()) > 0
        tm.clear()
        assert len(tm.get_records()) == 0
        assert tm.get_saga_elapsed() == 0.0

    def test_timeout_action_retry(self):
        config = TimeoutConfig(
            step_timeout=0.1,
            on_timeout=TimeoutAction.RETRY,
            timeout_retries=2,
        )
        tm = TimeoutManager(config)
        tm.start_step("step1")
        time.sleep(0.15)
        record = tm.check_step_timeout("step1")
        assert record is not None
        assert record.action_taken == TimeoutAction.RETRY

    def test_timeout_action_compensate(self):
        config = TimeoutConfig(
            step_timeout=0.1,
            on_timeout=TimeoutAction.COMPENSATE,
        )
        tm = TimeoutManager(config)
        tm.start_step("step1")
        time.sleep(0.15)
        record = tm.check_step_timeout("step1")
        assert record is not None
        assert record.action_taken == TimeoutAction.COMPENSATE


# ============================================================================
# Compensation Tests
# ============================================================================


class TestCompensationAction:
    """Tests for compensation actions."""

    def test_successful_compensation(self):
        def compensate(result, context):
            return f"compensated-{result}"

        action = CompensationAction(
            step_name="step1",
            action=compensate,
        )
        result = action.execute("original")
        assert result.status == CompensationStatus.SUCCEEDED
        assert result.result == "compensated-original"
        assert result.attempts == 1

    def test_failed_compensation(self):
        def bad_compensate(result, context):
            raise RuntimeError("compensation failed")

        action = CompensationAction(
            step_name="step1",
            action=bad_compensate,
            max_retries=2,
            retry_delay=0.01,
        )
        result = action.execute("original")
        assert result.status == CompensationStatus.FAILED
        assert result.error is not None
        assert result.attempts == 3  # initial + 2 retries

    def test_compensation_with_context(self):
        def compensate(result, context):
            return {"result": result, "extra": context.get("extra")}

        action = CompensationAction(
            step_name="step1",
            action=compensate,
            context={"extra": "data"},
        )
        result = action.execute("original")
        assert result.status == CompensationStatus.SUCCEEDED
        assert result.result == {"result": "original", "extra": "data"}

    def test_idempotent_compensation(self):
        call_count = 0

        def compensate(result, context):
            nonlocal call_count
            call_count += 1
            return "ok"

        action = CompensationAction(
            step_name="step1",
            action=compensate,
            idempotent=True,
            max_retries=2,
            retry_delay=0.01,
        )
        result = action.execute("original")
        assert result.status == CompensationStatus.SUCCEEDED
        assert call_count == 1  # no retries needed


class TestCompensationRegistry:
    """Tests for the compensation registry."""

    def test_register_and_get(self):
        registry = CompensationAction(
            step_name="step1",
            action=lambda r, c: None,
        )
        reg = CompensationRegistry()
        reg.register(registry)
        assert reg.has_compensation("step1")
        assert reg.get("step1") is not None

    def test_unregister(self):
        action = CompensationAction(
            step_name="step1",
            action=lambda r, c: None,
        )
        reg = CompensationRegistry()
        reg.register(action)
        assert reg.has_compensation("step1")
        reg.unregister("step1")
        assert not reg.has_compensation("step1")

    def test_get_all(self):
        reg = CompensationRegistry()
        reg.register(CompensationAction(step_name="s1", action=lambda r, c: None))
        reg.register(CompensationAction(step_name="s2", action=lambda r, c: None))
        all_actions = reg.get_all()
        assert len(all_actions) == 2
        assert "s1" in all_actions
        assert "s2" in all_actions

    def test_clear(self):
        reg = CompensationRegistry()
        reg.register(CompensationAction(step_name="s1", action=lambda r, c: None))
        reg.clear()
        assert len(reg.get_all()) == 0


# ============================================================================
# Saga Orchestrator Tests
# ============================================================================


class TestSagaOrchestrator:
    """Tests for the saga orchestrator."""

    def test_successful_saga(self):
        step1 = SagaStep(name="step1", action=lambda: "result1")
        step2 = SagaStep(name="step2", action=lambda: "result2")

        orchestrator = SagaOrchestrator(name="test-saga", steps=[step1, step2])
        result = orchestrator.execute()

        assert result.success
        assert result.state == SagaState.COMPLETED
        assert result.step_results["step1"] == "result1"
        assert result.step_results["step2"] == "result2"
        assert result.steps["step1"] == SagaStepStatus.SUCCEEDED
        assert result.steps["step2"] == SagaStepStatus.SUCCEEDED

    def test_saga_with_compensation(self):
        executed = []

        def action1():
            executed.append("action1")
            return "r1"

        def compensate1(result, context):
            executed.append("compensate1")

        def action2():
            executed.append("action2")
            raise RuntimeError("step2 failed")

        step1 = SagaStep(
            name="step1",
            action=action1,
            compensation=CompensationAction(
                step_name="step1",
                action=compensate1,
            ),
        )
        step2 = SagaStep(name="step2", action=action2)

        orchestrator = SagaOrchestrator(name="test-saga", steps=[step1, step2])
        result = orchestrator.execute()

        assert not result.success
        assert result.state == SagaState.COMPENSATED
        assert "action1" in executed
        assert "action2" in executed
        assert "compensate1" in executed
        assert result.compensation_results["step1"].status == CompensationStatus.SUCCEEDED

    def test_saga_with_retry(self):
        call_count = 0

        def flaky_action():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("temporary")
            return "success"

        step = SagaStep(
            name="step1",
            action=flaky_action,
            retry_policy=RetryPolicy(max_retries=3, initial_delay=0.01),
        )

        orchestrator = SagaOrchestrator(name="test-saga", steps=[step])
        result = orchestrator.execute()

        assert result.success
        assert call_count == 3

    def test_saga_with_timeout(self):
        def slow_action():
            time.sleep(10)
            return "done"

        step = SagaStep(
            name="step1",
            action=slow_action,
            timeout=0.1,
        )

        orchestrator = SagaOrchestrator(
            name="test-saga",
            steps=[step],
            timeout_config=TimeoutConfig(step_timeout=0.1),
        )
        result = orchestrator.execute()

        assert not result.success
        assert result.state == SagaState.FAILED

    def test_saga_step_skip_on_failure(self):
        def action1():
            raise RuntimeError("fail")

        def action2():
            return "should not run"

        step1 = SagaStep(name="step1", action=action1)
        step2 = SagaStep(name="step2", action=action2, skip_on_failure=True)

        orchestrator = SagaOrchestrator(name="test-saga", steps=[step1, step2])
        result = orchestrator.execute()

        assert not result.success
        assert result.steps["step2"] == SagaStepStatus.SKIPPED

    def test_saga_with_dependencies(self):
        execution_order = []

        def action1():
            execution_order.append("step1")
            return "r1"

        def action2():
            execution_order.append("step2")
            return "r2"

        step1 = SagaStep(name="step1", action=action1)
        step2 = SagaStep(name="step2", action=action2, depends_on=["step1"])

        orchestrator = SagaOrchestrator(name="test-saga", steps=[step1, step2])
        result = orchestrator.execute()

        assert result.success
        assert execution_order == ["step1", "step2"]

    def test_saga_with_unsatisfied_dependencies(self):
        def action1():
            raise RuntimeError("fail")

        def action2():
            return "should not run"

        step1 = SagaStep(name="step1", action=action1)
        step2 = SagaStep(name="step2", action=action2, depends_on=["step1"])

        orchestrator = SagaOrchestrator(name="test-saga", steps=[step1, step2])
        result = orchestrator.execute()

        assert not result.success
        assert result.steps["step2"] == SagaStepStatus.SKIPPED

    def test_saga_result_to_dict(self):
        step = SagaStep(name="step1", action=lambda: "result")
        orchestrator = SagaOrchestrator(name="test-saga", steps=[step])
        result = orchestrator.execute()

        d = result.to_dict()
        assert d["saga_name"] == "test-saga"
        assert d["state"] == "completed"
        assert d["step_results"]["step1"] == "result"
        assert "duration" in d

    def test_saga_with_context(self):
        def action_with_context(value):
            return value * 2

        step = SagaStep(
            name="step1",
            action=action_with_context,
            context={"value": 21},
        )

        orchestrator = SagaOrchestrator(name="test-saga", steps=[step])
        result = orchestrator.execute()

        assert result.success
        assert result.step_results["step1"] == 42

    def test_create_saga_factory(self):
        step = SagaStep(name="step1", action=lambda: "ok")
        orchestrator = create_saga("factory-saga", [step])
        assert orchestrator.name == "factory-saga"
        result = orchestrator.execute()
        assert result.success

    def test_saga_with_parallel_execution(self):
        execution_order = []
        lock = threading.Lock()

        def make_action(name, delay):
            def action():
                with lock:
                    execution_order.append(f"{name}-start")
                time.sleep(delay)
                with lock:
                    execution_order.append(f"{name}-end")
                return name
            return action

        step1 = SagaStep(name="step1", action=make_action("step1", 0.1))
        step2 = SagaStep(name="step2", action=make_action("step2", 0.05))

        orchestrator = SagaOrchestrator(
            name="parallel-saga",
            steps=[step1, step2],
            parallel=True,
            max_parallel=2,
        )
        result = orchestrator.execute()

        assert result.success
        # Both should have started (order may vary due to threading)
        assert "step1-start" in execution_order
        assert "step2-start" in execution_order

    def test_saga_with_parallel_failure(self):
        def action1():
            return "ok"

        def action2():
            raise RuntimeError("parallel fail")

        step1 = SagaStep(name="step1", action=action1)
        step2 = SagaStep(name="step2", action=action2)

        orchestrator = SagaOrchestrator(
            name="parallel-saga",
            steps=[step1, step2],
            parallel=True,
        )
        result = orchestrator.execute()

        assert not result.success

    def test_saga_stop(self):
        def slow_action():
            time.sleep(10)
            return "done"

        step = SagaStep(name="step1", action=slow_action)
        orchestrator = SagaOrchestrator(name="test-saga", steps=[step])

        # Stop after a short delay
        def stop_soon():
            time.sleep(0.05)
            orchestrator.stop()

        t = threading.Thread(target=stop_soon)
        t.start()
        result = orchestrator.execute()
        t.join()

        assert not result.success

    def test_saga_metadata(self):
        step = SagaStep(name="step1", action=lambda: "ok")
        orchestrator = SagaOrchestrator(
            name="test-saga",
            steps=[step],
            metadata={"key": "value"},
        )
        result = orchestrator.execute()
        assert result.metadata["key"] == "value"

    def test_compensation_failure_continues(self):
        executed = []

        def action1():
            executed.append("action1")
            return "r1"

        def compensate1(result, context):
            executed.append("compensate1")

        def action2():
            executed.append("action2")
            return "r2"

        def compensate2(result, context):
            executed.append("compensate2")
            raise RuntimeError("compensation failed")

        def action3():
            executed.append("action3")
            raise RuntimeError("step3 failed")

        step1 = SagaStep(
            name="step1",
            action=action1,
            compensation=CompensationAction(step_name="step1", action=compensate1),
        )
        step2 = SagaStep(
            name="step2",
            action=action2,
            compensation=CompensationAction(
                step_name="step2",
                action=compensate2,
                continue_on_failure=True,
            ),
        )
        step3 = SagaStep(name="step3", action=action3)

        orchestrator = SagaOrchestrator(
            name="test-saga",
            steps=[step1, step2, step3],
            continue_on_compensation_failure=True,
        )
        result = orchestrator.execute()

        assert not result.success
        assert result.state == SagaState.PARTIALLY_COMPENSATED
        assert "compensate1" in executed
        assert "compensate2" in executed

    def test_compensation_failure_stops(self):
        executed = []

        def action1():
            executed.append("action1")
            return "r1"

        def compensate1(result, context):
            executed.append("compensate1")

        def action2():
            executed.append("action2")
            return "r2"

        def compensate2(result, context):
            executed.append("compensate2")
            raise RuntimeError("compensation failed")

        def action3():
            executed.append("action3")
            raise RuntimeError("step3 failed")

        step1 = SagaStep(
            name="step1",
            action=action1,
            compensation=CompensationAction(step_name="step1", action=compensate1),
        )
        step2 = SagaStep(
            name="step2",
            action=action2,
            compensation=CompensationAction(
                step_name="step2",
                action=compensate2,
                continue_on_failure=False,
            ),
        )
        step3 = SagaStep(name="step3", action=action3)

        orchestrator = SagaOrchestrator(
            name="test-saga",
            steps=[step1, step2, step3],
            continue_on_compensation_failure=False,
        )
        result = orchestrator.execute()

        assert not result.success
        # compensate1 should run (reverse order: step2 fails, compensate step2 fails, stop)
        assert "compensate2" in executed
        # compensate1 should NOT run because continue_on_compensation_failure is False
        assert "compensate1" not in executed

    def test_saga_with_multiple_compensations(self):
        executed = []

        def make_action(name):
            def action():
                executed.append(f"action-{name}")
                return name
            return action

        def make_compensate(name):
            def compensate(result, context):
                executed.append(f"compensate-{name}")
            return compensate

        def failing_action():
            executed.append("action-fail")
            raise RuntimeError("fail")

        steps = [
            SagaStep(
                name=f"step{i}",
                action=make_action(i),
                compensation=CompensationAction(
                    step_name=f"step{i}",
                    action=make_compensate(i),
                ),
            )
            for i in range(1, 4)
        ]
        steps.append(SagaStep(name="step-fail", action=failing_action))

        orchestrator = SagaOrchestrator(name="test-saga", steps=steps)
        result = orchestrator.execute()

        assert not result.success
        assert result.state == SagaState.COMPENSATED
        # Compensations should run in reverse order
        comp_order = [e for e in executed if e.startswith("compensate-")]
        assert comp_order == ["compensate-3", "compensate-2", "compensate-1"]

    def test_empty_saga(self):
        orchestrator = SagaOrchestrator(name="empty-saga", steps=[])
        result = orchestrator.execute()
        assert result.success
        assert result.state == SagaState.COMPLETED

    def test_saga_step_with_custom_retry_policy(self):
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("temporary")
            return "ok"

        step = SagaStep(
            name="step1",
            action=flaky,
            retry_policy=RetryPolicy(
                max_retries=5,
                initial_delay=0.01,
                backoff_strategy=BackoffStrategy.EXPONENTIAL,
            ),
        )

        orchestrator = SagaOrchestrator(name="test-saga", steps=[step])
        result = orchestrator.execute()

        assert result.success
        assert call_count == 3

    def test_saga_with_timeout_action_retry(self):
        call_count = 0

        def sometimes_slow():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                time.sleep(10)  # will timeout
            return "ok"

        step = SagaStep(
            name="step1",
            action=sometimes_slow,
            timeout=0.1,
            retry_policy=RetryPolicy(max_retries=1, initial_delay=0.01),
        )

        orchestrator = SagaOrchestrator(
            name="test-saga",
            steps=[step],
            timeout_config=TimeoutConfig(
                step_timeout=0.1,
                on_timeout=TimeoutAction.RETRY,
            ),
        )
        result = orchestrator.execute()

        # Should succeed on retry
        assert result.success
        assert call_count == 2


# ============================================================================
# Integration Tests
# ============================================================================


class TestSagaIntegration:
    """Integration tests for the saga system."""

    def test_full_saga_with_all_features(self):
        """Test a saga using retry, timeout, compensation, and dependencies."""
        events = []

        def payment_action():
            events.append("payment")
            return "payment-ok"

        def payment_compensate(result, context):
            events.append("payment-refund")

        def inventory_action():
            events.append("inventory")
            return "inventory-ok"

        def inventory_compensate(result, context):
            events.append("inventory-restore")

        def shipping_action():
            events.append("shipping")
            raise RuntimeError("shipping failed")

        steps = [
            SagaStep(
                name="payment",
                action=payment_action,
                compensation=CompensationAction(
                    step_name="payment",
                    action=payment_compensate,
                ),
                retry_policy=RetryPolicy(max_retries=1, initial_delay=0.01),
            ),
            SagaStep(
                name="inventory",
                action=inventory_action,
                compensation=CompensationAction(
                    step_name="inventory",
                    action=inventory_compensate,
                ),
                depends_on=["payment"],
            ),
            SagaStep(
                name="shipping",
                action=shipping_action,
                depends_on=["inventory"],
            ),
        ]

        orchestrator = SagaOrchestrator(
            name="order-saga",
            steps=steps,
            timeout_config=TimeoutConfig(step_timeout=30.0),
        )
        result = orchestrator.execute()

        assert not result.success
        assert result.state == SagaState.COMPENSATED
        assert "payment" in events
        assert "inventory" in events
        assert "shipping" in events
        assert "payment-refund" in events
        assert "inventory-restore" in events

    def test_saga_state_machine_integration(self):
        """Test that the state machine tracks all transitions correctly."""
        step1 = SagaStep(name="step1", action=lambda: "ok")
        step2 = SagaStep(name="step2", action=lambda: "ok")

        orchestrator = SagaOrchestrator(name="test-saga", steps=[step1, step2])
        result = orchestrator.execute()

        sm = orchestrator.state_machine
        assert sm.saga_state == SagaState.COMPLETED
        assert sm.get_step_state("step1") == SagaStepState.SUCCEEDED
        assert sm.get_step_state("step2") == SagaStepState.SUCCEEDED

        history = sm.get_saga_history()
        assert len(history) >= 4  # saga running + 2 steps + saga completed

    def test_concurrent_sagas(self):
        """Test running multiple sagas concurrently."""
        results = []

        def run_saga(idx):
            step = SagaStep(name=f"step-{idx}", action=lambda: f"result-{idx}")
            orchestrator = SagaOrchestrator(name=f"saga-{idx}", steps=[step])
            results.append(orchestrator.execute())

        threads = [threading.Thread(target=run_saga, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 5
        assert all(r.success for r in results)
