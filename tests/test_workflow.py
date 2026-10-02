"""Tests for workflow module."""
import pytest
from apex_os_bp.workflow.engine import WorkflowEngine, Workflow, WorkflowStep, WorkflowStatus


class TestWorkflowStep:
    """Test workflow step."""

    def test_step_creation(self):
        """Step can be created."""
        step = WorkflowStep(name="step-1", action="test_action")
        assert step.name == "step-1"
        assert step.action == "test_action"
        assert step.status == WorkflowStatus.PENDING


class TestWorkflow:
    """Test workflow."""

    def test_workflow_creation(self):
        """Workflow can be created."""
        workflow = Workflow(name="test-workflow")
        assert workflow.name == "test-workflow"
        assert len(workflow.steps) == 0

    def test_add_step(self):
        """Step can be added to workflow."""
        workflow = Workflow(name="test-workflow")
        step = WorkflowStep(name="step-1", action="test_action")
        workflow.add_step(step)
        assert len(workflow.steps) == 1


class TestWorkflowEngine:
    """Test workflow engine."""

    def test_create_workflow(self):
        """Workflow can be created."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("test-workflow")
        assert workflow.name == "test-workflow"

    def test_execute_workflow(self):
        """Workflow can be executed."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("test-workflow")
        workflow.add_step(WorkflowStep(name="step-1", action="test_action"))
        result = engine.execute(workflow.name)
        assert result["status"] == "completed"
        assert len(result["steps"]) == 1

    def test_workflow_with_multiple_steps(self):
        """Workflow with multiple steps can be executed."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("test-workflow")
        workflow.add_step(WorkflowStep(name="step-1", action="action_1"))
        workflow.add_step(WorkflowStep(name="step-2", action="action_2"))
        workflow.add_step(WorkflowStep(name="step-3", action="action_3"))
        result = engine.execute(workflow.name)
        assert result["status"] == "completed"
        assert len(result["steps"]) == 3

    def test_workflow_status_tracking(self):
        """Workflow tracks step status."""
        engine = WorkflowEngine()
        workflow = engine.create_workflow("test-workflow")
        workflow.add_step(WorkflowStep(name="step-1", action="action_1"))
        result = engine.execute(workflow.name)
        assert result["steps"][0]["status"] == "completed"
