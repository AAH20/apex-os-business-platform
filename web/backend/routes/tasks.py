"""Task CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    status: str = Field(default="todo", pattern="^(todo|in_progress|done)$")
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    assignee: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(todo|in_progress|done)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    assignee: Optional[str] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    assignee: Optional[str] = None
    created_at: str
    updated_at: str


# Synthetic in-memory data store
_TASKS = [
    {"id": i, "title": f"Task {i}", "description": f"Description for task {i}",
     "status": ["todo", "in_progress", "done"][i % 3], "priority": ["low", "medium", "high"][i % 3],
     "assignee": f"user{i % 5}@example.com", "created_at": "2025-01-01T00:00:00",
     "updated_at": "2025-01-01T00:00:00"}
    for i in range(1, 26)
]
_next_id = 26


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
):
    """List all tasks with pagination and optional status filter."""
    filtered = [t for t in _TASKS if not status or t["status"] == status]
    start = (page - 1) * page_size
    return filtered[start : start + page_size]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int):
    """Get a single task by ID."""
    for task in _TASKS:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(payload: TaskCreate):
    """Create a new task."""
    global _next_id
    now = datetime.utcnow().isoformat()
    task = {"id": _next_id, **payload.model_dump(), "created_at": now, "updated_at": now}
    _TASKS.append(task)
    _next_id += 1
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, payload: TaskUpdate):
    """Update an existing task."""
    for i, task in enumerate(_TASKS):
        if task["id"] == task_id:
            updates = payload.model_dump(exclude_unset=True)
            _TASKS[i].update(updates)
            _TASKS[i]["updated_at"] = datetime.utcnow().isoformat()
            return _TASKS[i]
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int):
    """Delete a task by ID."""
    for i, task in enumerate(_TASKS):
        if task["id"] == task_id:
            _TASKS.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
