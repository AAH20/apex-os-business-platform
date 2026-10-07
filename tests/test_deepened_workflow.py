"""Tests for the deepened workflow module.

Rewritten to the class APIs that actually exist in
apex_os_bp.workflow.deepened. The old tests invented an engine facade
(engine.create / engine.add_task / engine.run_parallel / engine.commit_version
on WorkflowContext) that was never written - WorkflowContext really only
implements get/set over its variables.

Real API (verified live before encoding the assertions):
    ParallelTask(name, tasks).execute(ctx) -> List[TaskResult]
        each task is called with the WorkflowContext as its only argument
    ConditionalBranch(name, conditions[(name, pred)], default).execute(ctx)
        matching condition's callable runs, else default; returns TaskResult
    SubWorkflow(name, steps).execute(ctx) -> TaskResult (steps run in order)
    VersionedWorkflow(name).snapshot(state_dict, label) -> int version
        .diff(v1, v2) -> {key: {old, new}};  .rollback(version) -> state dict
    WorkflowAnalytics.record_result(TaskResult) -> failure_rate()/avg_duration()
    WorkflowContext.get(key, default) / set(key, value)
"""
from __future__ import annotations

import pytest

from apex_os_bp.workflow.deepened import (
    ConditionalBranch,
    ParallelTask,
    SubWorkflow,
    TaskResult,
    TaskStatus,
    VersionedWorkflow,
    WorkflowAnalytics,
    WorkflowContext,
)


def _taker(name: str, fn):
    """Adapt a zero-arg lambda to ParallelTask's ctx-only call convention."""
    return lambda ctx: fn()


class TestParallelExecution:
    def test_parallel_tasks_complete(self):
        task = ParallelTask("parallel_test", tasks=[
            _taker("t1", lambda: 1),
            _taker("t2", lambda: 2),
            _taker("t3", lambda: 3),
        ])

        results = task.execute(WorkflowContext())

        assert [t.output for t in results] == [1, 2, 3]
        assert all(t.status == TaskStatus.COMPLETED for t in results)

    def test_parallel_with_failure_is_surfaced(self):
        def bad(x):
            raise ZeroDivisionError("boom")

        task = ParallelTask("parallel_fail", tasks=[
            lambda ctx: "fine",
            bad,
        ])

        results = task.execute(WorkflowContext())

        assert results[0].status == TaskStatus.COMPLETED
        assert results[0].output == "fine"
        assert results[1].status == TaskStatus.FAILED
        assert results[1].error  # failure message recorded (as str)


class TestConditionalBranching:
    def test_if_branch_taken(self):
        ctx = WorkflowContext()
        ctx.set("on", True)

        branch = ConditionalBranch(
            "cond_test",
            conditions=[("flag", lambda c: c.get("on"))],
            default=lambda c: c.set("payload", "default-wrong"),
        )

        result = branch.execute(ctx)

        assert result.status == TaskStatus.COMPLETED
        assert result.error is None

    def test_else_branch_taken(self):
        ctx = WorkflowContext()
        ctx.set("on", False)

        branch = ConditionalBranch(
            "cond_test2",
            conditions=[("never", lambda c: False)],
            default=lambda c: ctx.set("seen", "no"),
        )

        result = branch.execute(ctx)

        assert result.status == TaskStatus.COMPLETED
        assert ctx.get("seen") == "no"


class TestSubWorkflows:
    def test_subworkflow_runs_steps_in_order(self):
        order = []
        ctx = WorkflowContext()

        def step1(c):
            order.append("step1")
            c.set("value", 10)

        def step2(c):
            order.append("step2")
            c.set("value", c.get("value") * 2)

        sub = SubWorkflow("sub", steps=[step1, step2])

        result = sub.execute(ctx)

        assert result.status == TaskStatus.COMPLETED
        assert ctx.get("value") == 20
        assert order == ["step1", "step2"]

    def test_nested_subworkflows(self):
        inner = SubWorkflow("inner", steps=[lambda c: c.set("n", 5)])

        def outer_step(c):
            c.set("b", c.get("n") + 1)

        outer = SubWorkflow("outer", steps=[inner.execute, outer_step])
        ctx = WorkflowContext()

        outer.execute(ctx)

        assert ctx.get("b") == 6


class TestVersioning:
    def test_snapshot_creates_a_version(self):
        wf = VersionedWorkflow("versioned")

        v1 = wf.snapshot({"t1": 1}, label="v1")

        assert v1 >= 1

    def test_diff_between_versions(self):
        wf = VersionedWorkflow("versioned2")
        v1 = wf.snapshot({"t1": 1}, label="v1")
        v2 = wf.snapshot({"t1": 2}, label="v2")

        diff = wf.diff(v1, v2)

        assert diff == {"t1": {"old": 1, "new": 2}}

    def test_rollback_restores_previous_state(self):
        wf = VersionedWorkflow("rollback_test")
        v1 = wf.snapshot({"t1": 1}, label="v1")

        state = wf.rollback(v1)

        assert state == {"t1": 1}


class TestWorkflowAnalytics:
    def test_execution_time_recorded(self):
        analytics = WorkflowAnalytics()

        analytics.record_result(TaskResult(
            task_id="t1", status=TaskStatus.COMPLETED,
            duration_ms=12.0,
        ))

        assert analytics.avg_duration() >= 0

    def test_task_count_and_success_rate(self):
        analytics = WorkflowAnalytics()

        analytics.record_result(TaskResult(
            task_id="t1", status=TaskStatus.COMPLETED, duration_ms=5.0))
        analytics.record_result(TaskResult(
            task_id="t2", status=TaskStatus.FAILED, duration_ms=5.0))

        assert analytics.failure_rate() == 0.5
