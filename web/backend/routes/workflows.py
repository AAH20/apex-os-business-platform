"""Workflow Automation CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


# ─── Pydantic Models ────────────────────────────────────────────────────────

class WorkflowStepCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    order: int = Field(default=0, ge=0)
    action: str = Field(..., min_length=1, max_length=200)
    config: Optional[Dict[str, Any]] = None


class WorkflowStepUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    order: Optional[int] = Field(None, ge=0)
    action: Optional[str] = Field(None, min_length=1, max_length=200)
    config: Optional[Dict[str, Any]] = None


class WorkflowStepResponse(BaseModel):
    id: int
    workflow_id: int
    name: str
    order: int
    action: str
    config: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    status: str = Field(default="draft", pattern="^(draft|active|paused|archived)$")
    steps: Optional[List[WorkflowStepCreate]] = None


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|active|paused|archived)$")


class WorkflowResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: str
    steps: List[WorkflowStepResponse] = []
    created_at: str
    updated_at: str


class WorkflowRunCreate(BaseModel):
    workflow_id: int
    trigger_id: Optional[int] = None
    input_data: Optional[Dict[str, Any]] = None


class WorkflowRunUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(pending|running|completed|failed|cancelled)$")
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class WorkflowRunResponse(BaseModel):
    id: int
    workflow_id: int
    trigger_id: Optional[int] = None
    status: str
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None


class WorkflowTriggerCreate(BaseModel):
    workflow_id: int
    name: str = Field(..., min_length=1, max_length=200)
    trigger_type: str = Field(..., min_length=1, max_length=100)
    config: Optional[Dict[str, Any]] = None
    enabled: bool = True


class WorkflowTriggerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    trigger_type: Optional[str] = Field(None, min_length=1, max_length=100)
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class WorkflowTriggerResponse(BaseModel):
    id: int
    workflow_id: int
    name: str
    trigger_type: str
    config: Optional[Dict[str, Any]] = None
    enabled: bool
    created_at: str
    updated_at: str


# ─── In-Memory Data Stores ─────────────────────────────────────────────────

_WORKFLOWS: List[Dict[str, Any]] = [
    {
        "id": i,
        "name": f"Workflow {i}",
        "description": f"Description for workflow {i}",
        "status": ["draft", "active", "paused"][i % 3],
        "steps": [],
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }
    for i in range(1, 6)
]
_NEXT_WF_ID = 6

_STEPS: List[Dict[str, Any]] = [
    {
        "id": j,
        "workflow_id": (j % 5) + 1,
        "name": f"Step {j}",
        "order": j,
        "action": ["send_email", "create_task", "update_record", "call_api", "notify"][j % 5],
        "config": {"param": f"value_{j}"},
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }
    for j in range(1, 11)
]
_NEXT_STEP_ID = 11

_RUNS: List[Dict[str, Any]] = [
    {
        "id": k,
        "workflow_id": (k % 5) + 1,
        "trigger_id": None,
        "status": ["pending", "running", "completed", "failed"][k % 4],
        "input_data": {"key": f"input_{k}"},
        "output_data": {"result": f"output_{k}"} if k % 4 == 2 else None,
        "error_message": "Timeout" if k % 4 == 3 else None,
        "started_at": f"2025-01-{k:02d}T00:00:00",
        "completed_at": f"2025-01-{k:02d}T00:05:00" if k % 4 in (2, 3) else None,
    }
    for k in range(1, 16)
]
_NEXT_RUN_ID = 16

_TRIGGERS: List[Dict[str, Any]] = [
    {
        "id": m,
        "workflow_id": (m % 5) + 1,
        "name": f"Trigger {m}",
        "trigger_type": ["schedule", "webhook", "event", "manual"][m % 4],
        "config": {"schedule": "*/5 * * * *"} if m % 4 == 0 else {"url": f"/hook/{m}"},
        "enabled": m % 3 != 0,
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }
    for m in range(1, 6)
]
_NEXT_TRIGGER_ID = 6


# ─── Helper ────────────────────────────────────────────────────────────────

def _attach_steps(workflow: Dict[str, Any]) -> Dict[str, Any]:
    wf = dict(workflow)
    wf["steps"] = [s for s in _STEPS if s["workflow_id"] == workflow["id"]]
    return wf


# ─── Workflow Endpoints ───────────────────────────────────────────────────

@router.get("", response_model=List[WorkflowResponse])
async def list_workflows(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
):
    """List all workflows with pagination and optional status filter."""
    filtered = [w for w in _WORKFLOWS if not status or w["status"] == status]
    start = (page - 1) * page_size
    return [_attach_steps(w) for w in filtered[start : start + page_size]]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: int):
    """Get a single workflow by ID."""
    for wf in _WORKFLOWS:
        if wf["id"] == workflow_id:
            return _attach_steps(wf)
    raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(payload: WorkflowCreate):
    """Create a new workflow."""
    global _NEXT_WF_ID
    now = datetime.utcnow().isoformat()
    wf = {
        "id": _NEXT_WF_ID,
        "name": payload.name,
        "description": payload.description,
        "status": payload.status,
        "steps": [],
        "created_at": now,
        "updated_at": now,
    }
    _WORKFLOWS.append(wf)
    _NEXT_WF_ID += 1
    # Create steps if provided
    if payload.steps:
        for step_data in payload.steps:
            global _NEXT_STEP_ID
            step = {
                "id": _NEXT_STEP_ID,
                "workflow_id": wf["id"],
                "name": step_data.name,
                "order": step_data.order,
                "action": step_data.action,
                "config": step_data.config,
                "created_at": now,
                "updated_at": now,
            }
            _STEPS.append(step)
            wf["steps"].append(step)
            _NEXT_STEP_ID += 1
    return wf


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(workflow_id: int, payload: WorkflowUpdate):
    """Update an existing workflow."""
    for i, wf in enumerate(_WORKFLOWS):
        if wf["id"] == workflow_id:
            updates = payload.model_dump(exclude_unset=True)
            _WORKFLOWS[i].update(updates)
            _WORKFLOWS[i]["updated_at"] = datetime.utcnow().isoformat()
            return _attach_steps(_WORKFLOWS[i])
    raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(workflow_id: int):
    """Delete a workflow by ID."""
    for i, wf in enumerate(_WORKFLOWS):
        if wf["id"] == workflow_id:
            _WORKFLOWS.pop(i)
            # Cascade delete steps
            global _STEPS
            _STEPS = [s for s in _STEPS if s["workflow_id"] != workflow_id]
            return
    raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")


# ─── Workflow Step Endpoints ──────────────────────────────────────────────

@router.get("/{workflow_id}/steps", response_model=List[WorkflowStepResponse])
async def list_steps(workflow_id: int):
    """List all steps for a workflow."""
    return [s for s in _STEPS if s["workflow_id"] == workflow_id]


@router.post("/{workflow_id}/steps", response_model=WorkflowStepResponse, status_code=201)
async def create_step(workflow_id: int, payload: WorkflowStepCreate):
    """Add a step to a workflow."""
    for wf in _WORKFLOWS:
        if wf["id"] == workflow_id:
            global _NEXT_STEP_ID
            now = datetime.utcnow().isoformat()
            step = {
                "id": _NEXT_STEP_ID,
                "workflow_id": workflow_id,
                "name": payload.name,
                "order": payload.order,
                "action": payload.action,
                "config": payload.config,
                "created_at": now,
                "updated_at": now,
            }
            _STEPS.append(step)
            _NEXT_STEP_ID += 1
            return step
    raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")


@router.put("/{workflow_id}/steps/{step_id}", response_model=WorkflowStepResponse)
async def update_step(workflow_id: int, step_id: int, payload: WorkflowStepUpdate):
    """Update a workflow step."""
    for i, step in enumerate(_STEPS):
        if step["id"] == step_id and step["workflow_id"] == workflow_id:
            updates = payload.model_dump(exclude_unset=True)
            _STEPS[i].update(updates)
            _STEPS[i]["updated_at"] = datetime.utcnow().isoformat()
            return _STEPS[i]
    raise HTTPException(status_code=404, detail=f"Step {step_id} not found")


@router.delete("/{workflow_id}/steps/{step_id}", status_code=204)
async def delete_step(workflow_id: int, step_id: int):
    """Delete a workflow step."""
    for i, step in enumerate(_STEPS):
        if step["id"] == step_id and step["workflow_id"] == workflow_id:
            _STEPS.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Step {step_id} not found")


# ─── Workflow Run Endpoints ───────────────────────────────────────────────

@router.get("/{workflow_id}/runs", response_model=List[WorkflowRunResponse])
async def list_runs(
    workflow_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
):
    """List runs for a workflow with pagination."""
    filtered = [r for r in _RUNS if r["workflow_id"] == workflow_id and (not status or r["status"] == status)]
    start = (page - 1) * page_size
    return filtered[start : start + page_size]


@router.post("/{workflow_id}/runs", response_model=WorkflowRunResponse, status_code=201)
async def create_run(workflow_id: int, payload: WorkflowRunCreate):
    """Trigger a new workflow run."""
    for wf in _WORKFLOWS:
        if wf["id"] == workflow_id:
            global _NEXT_RUN_ID
            now = datetime.utcnow().isoformat()
            run = {
                "id": _NEXT_RUN_ID,
                "workflow_id": workflow_id,
                "trigger_id": payload.trigger_id,
                "status": "pending",
                "input_data": payload.input_data,
                "output_data": None,
                "error_message": None,
                "started_at": now,
                "completed_at": None,
            }
            _RUNS.append(run)
            _NEXT_RUN_ID += 1
            return run
    raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")


@router.get("/{workflow_id}/runs/{run_id}", response_model=WorkflowRunResponse)
async def get_run(workflow_id: int, run_id: int):
    """Get a specific workflow run."""
    for run in _RUNS:
        if run["id"] == run_id and run["workflow_id"] == workflow_id:
            return run
    raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


@router.put("/{workflow_id}/runs/{run_id}", response_model=WorkflowRunResponse)
async def update_run(workflow_id: int, run_id: int, payload: WorkflowRunUpdate):
    """Update a workflow run (e.g., mark as completed or failed)."""
    for i, run in enumerate(_RUNS):
        if run["id"] == run_id and run["workflow_id"] == workflow_id:
            updates = payload.model_dump(exclude_unset=True)
            _RUNS[i].update(updates)
            if updates.get("status") in ("completed", "failed", "cancelled"):
                _RUNS[i]["completed_at"] = datetime.utcnow().isoformat()
            return _RUNS[i]
    raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


@router.delete("/{workflow_id}/runs/{run_id}", status_code=204)
async def delete_run(workflow_id: int, run_id: int):
    """Delete a workflow run."""
    for i, run in enumerate(_RUNS):
        if run["id"] == run_id and run["workflow_id"] == workflow_id:
            _RUNS.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


# ─── Workflow Trigger Endpoints ───────────────────────────────────────────

@router.get("/{workflow_id}/triggers", response_model=List[WorkflowTriggerResponse])
async def list_triggers(workflow_id: int):
    """List all triggers for a workflow."""
    return [t for t in _TRIGGERS if t["workflow_id"] == workflow_id]


@router.post("/{workflow_id}/triggers", response_model=WorkflowTriggerResponse, status_code=201)
async def create_trigger(workflow_id: int, payload: WorkflowTriggerCreate):
    """Add a trigger to a workflow."""
    for wf in _WORKFLOWS:
        if wf["id"] == workflow_id:
            global _NEXT_TRIGGER_ID
            now = datetime.utcnow().isoformat()
            trigger = {
                "id": _NEXT_TRIGGER_ID,
                "workflow_id": workflow_id,
                "name": payload.name,
                "trigger_type": payload.trigger_type,
                "config": payload.config,
                "enabled": payload.enabled,
                "created_at": now,
                "updated_at": now,
            }
            _TRIGGERS.append(trigger)
            _NEXT_TRIGGER_ID += 1
            return trigger
    raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")


@router.put("/{workflow_id}/triggers/{trigger_id}", response_model=WorkflowTriggerResponse)
async def update_trigger(workflow_id: int, trigger_id: int, payload: WorkflowTriggerUpdate):
    """Update a workflow trigger."""
    for i, trig in enumerate(_TRIGGERS):
        if trig["id"] == trigger_id and trig["workflow_id"] == workflow_id:
            updates = payload.model_dump(exclude_unset=True)
            _TRIGGERS[i].update(updates)
            _TRIGGERS[i]["updated_at"] = datetime.utcnow().isoformat()
            return _TRIGGERS[i]
    raise HTTPException(status_code=404, detail=f"Trigger {trigger_id} not found")


@router.delete("/{workflow_id}/triggers/{trigger_id}", status_code=204)
async def delete_trigger(workflow_id: int, trigger_id: int):
    """Delete a workflow trigger."""
    for i, trig in enumerate(_TRIGGERS):
        if trig["id"] == trigger_id and trig["workflow_id"] == workflow_id:
            _TRIGGERS.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Trigger {trigger_id} not found")
