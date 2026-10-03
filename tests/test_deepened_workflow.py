"""Tests for deepened workflow module."""
import pytest
from datetime import date, timedelta
from decimal import Decimal


class TestParallelExecution:
    @pytest.fixture
    def engine(self):
        from apex_os_bp.workflow.deepened import WorkflowContext
        return WorkflowContext()

    def test_parallel_tasks_complete(self, engine):
        wf = engine.create("parallel_test")
        engine.add_task(wf, "t1", fn=lambda: 1)
        engine.add_task(wf, "t2", fn=lambda: 2)
        engine.add_task(wf, "t3", fn=lambda: 3)
        engine.run_parallel(wf, ["t1", "t2", "t3"])
        assert engine.get_result(wf, "t1") == 1
        assert engine.get_result(wf, "t2") == 2
        assert engine.get_result(wf, "t3") == 3

    def test_parallel_with_failure(self, engine):
        wf = engine.create("parallel_fail")
        engine.add_task(wf, "ok", fn=lambda: "fine")
        engine.add_task(wf, "bad", fn=lambda: 1 / 0)
        results = engine.run_parallel(wf, ["ok", "bad"], raise_on_error=False)
        assert results["ok"] == "fine"
        assert isinstance(results["bad"], Exception)


class TestConditionalBranching:
    @pytest.fixture
    def engine(self):
        from apex_os_bp.workflow.deepened import WorkflowContext
        return WorkflowContext()

    def test_if_branch_taken(self, engine):
        wf = engine.create("cond_test")
        engine.add_task(wf, "check", fn=lambda: True)
        engine.add_branch(wf, "check", if_true="yes_task", if_false="no_task")
        engine.add_task(wf, "yes_task", fn=lambda: "yes")
        engine.add_task(wf, "no_task", fn=lambda: "no")
        engine.run(wf)
        assert engine.get_result(wf, "yes_task") == "yes"

    def test_else_branch_taken(self, engine):
        wf = engine.create("cond_test2")
        engine.add_task(wf, "check", fn=lambda: False)
        engine.add_branch(wf, "check", if_true="yes_task", if_false="no_task")
        engine.add_task(wf, "yes_task", fn=lambda: "yes")
        engine.add_task(wf, "no_task", fn=lambda: "no")
        engine.run(wf)
        assert engine.get_result(wf, "no_task") == "no"


class TestSubWorkflows:
    @pytest.fixture
    def engine(self):
        from apex_os_bp.workflow.deepened import WorkflowContext
        return WorkflowContext()

    def test_subworkflow_execution(self, engine):
        sub = engine.create("sub")
        engine.add_task(sub, "step1", fn=lambda: 10)
        engine.add_task(sub, "step2", fn=lambda x: x * 2, deps=["step1"])
        engine.run(sub)
        assert engine.get_result(sub, "step2") == 20

    def test_nested_subworkflows(self, engine):
        inner = engine.create("inner")
        engine.add_task(inner, "a", fn=lambda: 5)
        outer = engine.create("outer")
        engine.add_subworkflow(outer, "sub", inner)
        engine.add_task(outer, "b", fn=lambda x: x + 1, deps=["sub"])
        engine.run(outer)
        assert engine.get_result(outer, "b") == 6


class TestVersioning:
    @pytest.fixture
    def engine(self):
        from apex_os_bp.workflow.deepened import WorkflowContext
        return WorkflowContext()

    def test_create_version(self, engine):
        wf = engine.create("versioned")
        engine.add_task(wf, "t1", fn=lambda: 1)
        v1 = engine.commit_version(wf, "v1")
        assert v1 == "v1"

    def test_list_versions(self, engine):
        wf = engine.create("versioned2")
        engine.add_task(wf, "t1", fn=lambda: 1)
        engine.commit_version(wf, "v1")
        engine.commit_version(wf, "v2")
        versions = engine.list_versions(wf)
        assert "v1" in versions
        assert "v2" in versions

    def test_rollback(self, engine):
        wf = engine.create("rollback_test")
        engine.add_task(wf, "t1", fn=lambda: 1)
        engine.commit_version(wf, "v1")
        engine.add_task(wf, "t2", fn=lambda: 2)
        engine.rollback(wf, "v1")
        assert engine.has_task(wf, "t1")
        assert not engine.has_task(wf, "t2")


class TestWorkflowAnalytics:
    @pytest.fixture
    def engine(self):
        from apex_os_bp.workflow.deepened import WorkflowContext
        return WorkflowContext()

    def test_execution_time_recorded(self, engine):
        wf = engine.create("timed")
        engine.add_task(wf, "t1", fn=lambda: 1)
        engine.run(wf)
        stats = engine.get_stats(wf)
        assert "execution_time" in stats
        assert stats["execution_time"] >= 0

    def test_task_count(self, engine):
        wf = engine.create("counted")
        engine.add_task(wf, "t1", fn=lambda: 1)
        engine.add_task(wf, "t2", fn=lambda: 2)
        engine.run(wf)
        stats = engine.get_stats(wf)
        assert stats["task_count"] == 2

    def test_success_rate(self, engine):
        wf = engine.create("success_rate")
        engine.add_task(wf, "t1", fn=lambda: 1)
        engine.add_task(wf, "t2", fn=lambda: 1 / 0)
        engine.run(wf, raise_on_error=False)
        stats = engine.get_stats(wf)
        assert stats["success_rate"] == 0.5
