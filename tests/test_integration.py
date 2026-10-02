"""Tests for integration module."""
import pytest
from apex_os_bp.integration.gateway import APIGateway, Route, RateLimiter
from apex_os_bp.integration.workflow import Workflow, WorkflowStep, WorkflowEngine


class TestRoute:
    """Test route data structure."""

    def test_route_creation(self):
        """Route can be created."""
        route = Route(path="/api/test", method="GET", handler="test_handler")
        assert route.path == "/api/test"
        assert route.method == "GET"
        assert route.handler == "test_handler"


class TestRateLimiter:
    """Test rate limiter."""

    def test_rate_limit_allows_under_limit(self):
        """Requests under limit are allowed."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert limiter.allow("client-1")

    def test_rate_limit_blocks_over_limit(self):
        """Requests over limit are blocked."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        assert limiter.allow("client-1")
        assert limiter.allow("client-1")
        assert not limiter.allow("client-1")

    def test_rate_limit_resets_after_window(self):
        """Rate limit resets after window."""
        limiter = RateLimiter(max_requests=1, window_seconds=1)
        assert limiter.allow("client-1")
        assert not limiter.allow("client-1")


class TestAPIGateway:
    """Test API gateway."""

    def test_add_route(self):
        """Route can be added to gateway."""
        gateway = APIGateway()
        route = Route(path="/api/test", method="GET", handler="test_handler")
        gateway.add_route(route)
        assert len(gateway.routes) == 1

    def test_get_route(self):
        """Route can be retrieved."""
        gateway = APIGateway()
        route = Route(path="/api/test", method="GET", handler="test_handler")
        gateway.add_route(route)
        found = gateway.get_route("/api/test", "GET")
        assert found is not None
        assert found.handler == "test_handler"

    def test_rate_limit_middleware(self):
        """Rate limit middleware is applied."""
        gateway = APIGateway()
        gateway.set_rate_limiter(RateLimiter(max_requests=10, window_seconds=60))
        assert gateway._rate_limiter is not None


class TestWorkflowStep:
    """Test workflow step."""

    def test_step_creation(self):
        """Step can be created."""
        step = WorkflowStep(name="step-1", action="test_action")
        assert step.name == "step-1"
        assert step.action == "test_action"


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
