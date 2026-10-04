"""Workflow routes."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from apex_os_bp.api.models import (
    WorkflowCreate,
    WorkflowExecutionResponse,
    WorkflowResponse,
    WorkflowStepCreate,
)
from apex_os_bp.workflow.engine import Workflow, WorkflowEngine, WorkflowStep

router = APIRouter(prefix="/workflows", tags=["Workflows"])


def get_workflow_engine(request: Request) -> WorkflowEngine:
    """Get the workflow engine from the app state."""
    return request.app.state.workflow_engine


def _workflow_to_response(workflow: Workflow) -> WorkflowResponse:
    """Convert a Workflow model to a response."""
    return WorkflowResponse(
        name=workflow.name,
        steps=[{"name": s.name, "action": s.action, "status": s.status.value, "config": s.config}
            for s in workflow.steps],
        metadata=workflow.metadata,
    )


@router.get("", response_model=List[WorkflowResponse])
async def list_workflows(
    engine: WorkflowEngine = Depends(get_workflow_engine),
) -> List[WorkflowResponse]:
    """List all workflows."""
    return [_workflow_to_response(w) for w in engine._workflows.values()]


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    body: WorkflowCreate,
    engine: WorkflowEngine = Depends(get_workflow_engine),
) -> WorkflowResponse:
    """Create a new workflow."""
    steps = [WorkflowStep(name=s.name, action=s.action, config=s.config) for s in body.steps]
    workflow = engine.create_workflow(name=body.name, steps=steps, metadata=body.metadata)
    return _workflow_to_response(workflow)


@router.get("/{name}", response_model=WorkflowResponse)
async def get_workflow(
    name: str,
    engine: WorkflowEngine = Depends(get_workflow_engine),
) -> WorkflowResponse:
    """Get a workflow by name."""
    workflow = engine.get_workflow(name)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {name}",
        )
    return _workflow_to_response(workflow)


@router.post("/{name}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    name: str,
    engine: WorkflowEngine = Depends(get_workflow_engine),
) -> WorkflowExecutionResponse:
    """Execute a workflow."""
    try:
        result = engine.execute(name)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    return WorkflowExecutionResponse(**result)


@router.post("/{name}/steps", response_model=WorkflowResponse)
async def add_step_to_workflow(
    name: str,
    body: WorkflowStepCreate,
    engine: WorkflowEngine = Depends(get_workflow_engine),
) -> WorkflowResponse:
    """Add a step to an existing workflow."""
    workflow = engine.get_workflow(name)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {name}",
        )
    step = WorkflowStep(name=body.name, action=body.action, config=body.config)
    workflow.add_step(step)
    return _workflow_to_response(workflow)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    name: str,
    engine: WorkflowEngine = Depends(get_workflow_engine),
) -> None:
    """Delete a workflow."""
    workflow = engine.get_workflow(name)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow not found: {name}",
        )
    engine._workflows.pop(name, None)
