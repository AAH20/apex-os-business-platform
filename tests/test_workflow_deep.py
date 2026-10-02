"""Tests for deepened workflow module."""
import time
import pytest
from apex_os_bp.workflow.engine import WorkflowEngine, Workflow, WorkflowStep, WorkflowStatus


class TestParallelExecution:
    """Test parallel execution."""

    def test_parallel_group_execution(self):
        """Steps in a parallel group are executed."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("parallel-test")
        workflow.add_step(WorkflowStep(name="step-1", action="action_1", parallel_group="group-1"))
        workflow.add_step(WorkflowStep(name="step-2", action="action_2", parallel_group="group-1"))
        workflow.add_step(WorkflowStep(name="step-3", action="action_3", parallel_group="group-1"))

        result = engine.execute("parallel-test")

        assert result["status"] == "completed"
        assert len(result["steps"]) == 3
        for step in result["steps"]:
            assert step["status"] == "completed"

    def test_parallel_and_sequential_mixed(self):
        """Parallel and sequential steps can be mixed."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("mixed-test")
        workflow.add_step(WorkflowStep(name="step-1", action="action_1"))
        workflow.add_step(WorkflowStep(name="step-2", action="action_2", parallel_group="group-1"))
        workflow.add_step(WorkflowStep(name="step-3", action="action_3", parallel_group="group-1"))
        workflow.add_step(WorkflowStep(name="step-4", action="action_4"))

        result = engine.execute("mixed-test")

        assert result["status"] == "completed"
        assert len(result["steps"]) == 4

    def test_parallel_group_with_two_steps(self):
        """Two steps in a parallel group are executed."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("parallel-2")
        workflow.add_step(WorkflowStep(name="a", action="a", parallel_group="g"))
        workflow.add_step(WorkflowStep(name="b", action="b", parallel_group="g"))

        result = engine.execute("parallel-2")

        assert result["status"] == "completed"
        assert len(result["steps"]) == 2

    def test_parallel_group_with_condition_skip(self):
        """Steps with false condition are skipped even in parallel group."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("parallel-cond")
        workflow.add_step(WorkflowStep(name="a", action="a", parallel_group="g"))
        workflow.add_step(WorkflowStep(
            name="b", action="b", parallel_group="g",
            condition=lambda ctx: False
        ))

        result = engine.execute("parallel-cond")

        assert result["status"] == "completed"
        assert len(result["steps"]) == 2
        statuses = {s["step"]: s["status"] for s in result["steps"]}
        assert statuses["a"] == "completed"
        assert statuses["b"] == "skipped"


class TestConditionalBranching:
    """Test conditional branching."""

    def test_condition_true(self):
        """Step with true condition is executed."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("cond-true")
        workflow.add_step(WorkflowStep(
            name="step-1",
            action="action_1",
            condition=lambda ctx: True
        ))

        result = engine.execute("cond-true")

        assert result["status"] == "completed"
        assert result["steps"][0]["status"] == "completed"

    def test_condition_false(self):
        """Step with false condition is skipped."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("cond-false")
        workflow.add_step(WorkflowStep(
            name="step-1",
            action="action_1",
            condition=lambda ctx: False
        ))

        result = engine.execute("cond-false")

        assert result["status"] == "completed"
        assert result["steps"][0]["status"] == "skipped"

    def test_condition_with_context(self):
        """Step condition can use context."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("cond-ctx")
        workflow.add_step(WorkflowStep(
            name="step-1",
            action="action_1",
            condition=lambda ctx: ctx.get("run", False)
        ))

        result = engine.execute("cond-ctx", context={"run": True})
        assert result["steps"][0]["status"] == "completed"

        result = engine.execute("cond-ctx", context={"run": False})
        assert result["steps"][0]["status"] == "skipped"

    def test_on_success_branching(self):
        """Step with on_success executes next step on success."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("branch-success")
        workflow.add_step(WorkflowStep(
            name="step-1",
            action="action_1",
            on_success="step-2"
        ))
        workflow.add_step(WorkflowStep(name="step-2", action="action_2"))

        result = engine.execute("branch-success")

        assert result["status"] == "completed"
        assert len(result["steps"]) == 2

    def test_on_failure_branching(self):
        """Step with on_failure executes next step on failure."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("branch-failure")
        workflow.add_step(WorkflowStep(
            name="step-1",
            action="action_1",
            config={"fail_count": 1},
            max_retries=0,
            on_failure="step-2"
        ))
        workflow.add_step(WorkflowStep(name="step-2", action="action_2"))

        result = engine.execute("branch-failure")

        assert result["status"] == "failed"
        assert len(result["steps"]) == 2
        assert result["steps"][0]["status"] == "failed"
        assert result["steps"][1]["status"] == "completed"


class TestErrorHandlingRetries:
    """Test error handling with retries."""

    def test_retry_success(self):
        """Step succeeds after retry."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("retry-success")
        workflow.add_step(WorkflowStep(
            name="step-1",
            action="action_1",
            config={"fail_count": 1},
            max_retries=2,
            retry_delay=0.01
        ))

        result = engine.execute("retry-success")

        assert result["status"] == "completed"
        assert result["steps"][0]["status"] == "completed"
        assert result["steps"][0]["retry_count"] == 1

    def test_retry_exhausted(self):
        """Step fails after all retries exhausted."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("retry-exhausted")
        workflow.add_step(WorkflowStep(
            name="step-1",
            action="action_1",
            config={"fail_count": 5},
            max_retries=2,
            retry_delay=0.01
        ))

        result = engine.execute("retry-exhausted")

        assert result["status"] == "failed"
        assert result["steps"][0]["status"] == "failed"
        assert result["steps"][0]["retry_count"] == 2

    def test_no_retry(self):
        """Step fails without retries."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("no-retry")
        workflow.add_step(WorkflowStep(
            name="step-1",
            action="action_1",
            config={"fail_count": 1},
            max_retries=0
        ))

        result = engine.execute("no-retry")

        assert result["status"] == "failed"
        assert result["steps"][0]["status"] == "failed"
        assert result["steps"][0]["retry_count"] == 0


class TestHumanInTheLoop:
    """Test human-in-the-loop."""

    def test_approval_callback_called(self):
        """Approval callback is called for steps requiring approval."""
        callback_calls = []

        def approval_callback(step, ctx):
            callback_calls.append(step.name)
            return True

        engine = WorkflowEngine(approval_callback=approval_callback)
        workflow = engine.create_workflow("approval-test")
        workflow.add_step(WorkflowStep(
            name="step-1",
            action="action_1",
            requires_approval=True
        ))

        result = engine.execute("approval-test")

        assert result["status"] == "completed"
        assert len(callback_calls) == 1
        assert callback_calls[0] == "step-1"

    def test_approval_denied(self):
        """Step is skipped when approval is denied."""
        def approval_callback(step, ctx):
            return False

        engine = WorkflowEngine(approval_callback=approval_callback)
        workflow = engine.create_workflow("approval-denied")
        workflow.add_step(WorkflowStep(
            name="step-1",
            action="action_1",
            requires_approval=True
        ))

        result = engine.execute("approval-denied")

        assert result["status"] == "completed"
        assert result["steps"][0]["status"] == "skipped"

    def test_auto_approve_without_callback(self):
        """Step is auto-approved when no callback is provided."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("auto-approve")
        workflow.add_step(WorkflowStep(
            name="step-1",
            action="action_1",
            requires_approval=True
        ))

        result = engine.execute("auto-approve")

        assert result["status"] == "completed"
        assert result["steps"][0]["status"] == "completed"


class TestWorkflowVersioning:
    """Test workflow versioning."""

    def test_create_multiple_versions(self):
        """Multiple versions of a workflow can be created."""
        engine = WorkflowEngine()
        engine.create_workflow("versioned", version="1.0.0")
        engine.create_workflow("versioned", version="2.0.0")

        versions = engine.list_versions("versioned")

        assert len(versions) == 2
        assert "1.0.0" in versions
        assert "2.0.0" in versions

    def test_get_specific_version(self):
        """Specific version can be retrieved."""
        engine = WorkflowEngine()
        engine.create_workflow("versioned", version="1.0.0")
        engine.create_workflow("versioned", version="2.0.0")

        workflow = engine.get_workflow("versioned", version="1.0.0")

        assert workflow is not None
        assert workflow.version == "1.0.0"

    def test_get_latest_version(self):
        """Latest version is returned when no version specified."""
        engine = WorkflowEngine()
        engine.create_workflow("versioned", version="1.0.0")
        engine.create_workflow("versioned", version="2.0.0")

        workflow = engine.get_workflow("versioned")

        assert workflow is not None
        assert workflow.version == "2.0.0"

    def test_execute_specific_version(self):
        """Specific version can be executed."""
        engine = WorkflowEngine()
        workflow_v1 = engine.create_workflow("versioned", version="1.0.0")
        workflow_v1.add_step(WorkflowStep(name="step-1", action="action_v1"))

        workflow_v2 = engine.create_workflow("versioned", version="2.0.0")
        workflow_v2.add_step(WorkflowStep(name="step-1", action="action_v2"))

        result_v1 = engine.execute("versioned", version="1.0.0")
        result_v2 = engine.execute("versioned", version="2.0.0")

        assert result_v1["version"] == "1.0.0"
        assert result_v1["steps"][0]["action"] == "action_v1"

        assert result_v2["version"] == "2.0.0"
        assert result_v2["steps"][0]["action"] == "action_v2"

    def test_version_in_result(self):
        """Version is included in execution result."""
        engine = WorkflowEngine()
        engine.create_workflow("versioned", version="1.0.0")

        result = engine.execute("versioned")

        assert result["version"] == "1.0.0"
