"""Project Management CRUD API endpoints.

Covers projects, milestones, tasks, resources, and time entries.
Each entity supports list, get, create, update, delete.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date

router = APIRouter(prefix="/api/project-mgmt", tags=["project-mgmt"])


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    status: str = Field(default="active", pattern="^(active|archived|completed|on_hold)$")
    owner: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|archived|completed|on_hold)$")
    owner: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class Project(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MilestoneBase(BaseModel):
    project_id: int
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: str = Field(default="pending", pattern="^(pending|in_progress|completed)$")


class MilestoneCreate(MilestoneBase):
    pass


class MilestoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed)$")


class Milestone(MilestoneBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    project_id: int
    milestone_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    status: str = Field(default="todo", pattern="^(todo|in_progress|done)$")
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    assignee: Optional[str] = None
    due_date: Optional[date] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(todo|in_progress|done)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    assignee: Optional[str] = None
    due_date: Optional[date] = None
    milestone_id: Optional[int] = None


class Task(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResourceBase(BaseModel):
    project_id: int
    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(default="human", pattern="^(human|equipment|software|budget)$")
    allocation: float = Field(default=100.0, ge=0, le=100)


class ResourceCreate(ResourceBase):
    pass


class ResourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    type: Optional[str] = Field(None, pattern="^(human|equipment|software|budget)$")
    allocation: Optional[float] = Field(None, ge=0, le=100)


class Resource(ResourceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TimeEntryBase(BaseModel):
    task_id: int
    user: str = Field(..., min_length=1, max_length=100)
    hours: float = Field(..., gt=0, le=24)
    date: date
    description: Optional[str] = None


class TimeEntryCreate(TimeEntryBase):
    pass


class TimeEntryUpdate(BaseModel):
    user: Optional[str] = Field(None, min_length=1, max_length=100)
    hours: Optional[float] = Field(None, gt=0, le=24)
    date: Optional[date] = None
    description: Optional[str] = None


class TimeEntry(TimeEntryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── In-Memory Data Stores ────────────────────────────────────────────────────

_projects: List[dict] = [
    {
        "id": i,
        "name": f"Project {i}",
        "description": f"Description for project {i}",
        "status": ["active", "completed", "on_hold", "archived"][i % 4],
        "owner": f"user{i % 5 + 1}@example.com",
        "start_date": date(2024, 1, i).isoformat(),
        "end_date": date(2024, 12, i).isoformat() if i % 3 == 0 else None,
        "created_at": datetime(2024, 1, i),
        "updated_at": datetime(2024, 6, i),
    }
    for i in range(1, 11)
]
_next_project_id = 11

_milestones: List[dict] = [
    {
        "id": i,
        "project_id": (i % 5) + 1,
        "name": f"Milestone {i}",
        "description": f"Milestone description {i}",
        "due_date": date(2024, 3 + i % 9, 15).isoformat(),
        "status": ["pending", "in_progress", "completed"][i % 3],
        "created_at": datetime(2024, 1, i),
        "updated_at": datetime(2024, 2, min(i, 28)),
    }
    for i in range(1, 16)
]
_next_milestone_id = 16

_tasks: List[dict] = [
    {
        "id": i,
        "project_id": (i % 5) + 1,
        "milestone_id": (i % 5) + 1 if i % 3 == 0 else None,
        "title": f"Task {i}",
        "description": f"Task description {i}",
        "status": ["todo", "in_progress", "done"][i % 3],
        "priority": ["low", "medium", "high"][i % 3],
        "assignee": f"user{i % 5 + 1}@example.com",
        "due_date": date(2024, 4 + i % 8, 10).isoformat(),
        "created_at": datetime(2024, 1, i),
        "updated_at": datetime(2024, 2, min(i, 28)),
    }
    for i in range(1, 31)
]
_next_task_id = 31

_resources: List[dict] = [
    {
        "id": i,
        "project_id": (i % 5) + 1,
        "name": f"Resource {i}",
        "type": ["human", "equipment", "software", "budget"][i % 4],
        "allocation": 25.0 * (i % 4 + 1),
        "created_at": datetime(2024, 1, i),
        "updated_at": datetime(2024, 2, min(i, 28)),
    }
    for i in range(1, 16)
]
_next_resource_id = 16

_time_entries: List[dict] = [
    {
        "id": i,
        "task_id": (i % 10) + 1,
        "user": f"user{i % 5 + 1}@example.com",
        "hours": 1.0 + (i % 8),
        "date": date(2024, 5, i % 28 + 1).isoformat(),
        "description": f"Work on task {(i % 10) + 1}",
        "created_at": datetime(2024, 5, i % 28 + 1),
        "updated_at": datetime(2024, 5, i % 28 + 1),
    }
    for i in range(1, 26)
]
_next_time_entry_id = 26


# ─── Helper ───────────────────────────────────────────────────────────────────

def _paginate(items: list, page: int, page_size: int) -> dict:
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": items[start:end],
        "total": len(items),
        "page": page,
        "page_size": page_size,
        "pages": (len(items) + page_size - 1) // page_size,
    }


# ─── Project Endpoints ────────────────────────────────────────────────────────

@router.get("/projects", response_model=dict)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
):
    filtered = _projects
    if status:
        filtered = [p for p in filtered if p["status"] == status]
    return _paginate(filtered, page, page_size)


@router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: int):
    for p in _projects:
        if p["id"] == project_id:
            return p
    raise HTTPException(status_code=404, detail="Project not found")


@router.post("/projects", response_model=Project, status_code=201)
async def create_project(project: ProjectCreate):
    global _next_project_id
    now = datetime.now()
    new_project = {
        "id": _next_project_id,
        **project.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _projects.append(new_project)
    _next_project_id += 1
    return new_project


@router.put("/projects/{project_id}", response_model=Project)
async def update_project(project_id: int, project: ProjectUpdate):
    for i, p in enumerate(_projects):
        if p["id"] == project_id:
            updated = {**p, **project.model_dump(exclude_unset=True), "updated_at": datetime.now()}
            _projects[i] = updated
            return updated
    raise HTTPException(status_code=404, detail="Project not found")


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: int):
    for i, p in enumerate(_projects):
        if p["id"] == project_id:
            _projects.pop(i)
            return
    raise HTTPException(status_code=404, detail="Project not found")


# ─── Milestone Endpoints ──────────────────────────────────────────────────────

@router.get("/milestones", response_model=dict)
async def list_milestones(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
):
    filtered = _milestones
    if project_id is not None:
        filtered = [m for m in filtered if m["project_id"] == project_id]
    if status:
        filtered = [m for m in filtered if m["status"] == status]
    return _paginate(filtered, page, page_size)


@router.get("/milestones/{milestone_id}", response_model=Milestone)
async def get_milestone(milestone_id: int):
    for m in _milestones:
        if m["id"] == milestone_id:
            return m
    raise HTTPException(status_code=404, detail="Milestone not found")


@router.post("/milestones", response_model=Milestone, status_code=201)
async def create_milestone(milestone: MilestoneCreate):
    global _next_milestone_id
    now = datetime.now()
    new_milestone = {
        "id": _next_milestone_id,
        **milestone.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _milestones.append(new_milestone)
    _next_milestone_id += 1
    return new_milestone


@router.put("/milestones/{milestone_id}", response_model=Milestone)
async def update_milestone(milestone_id: int, milestone: MilestoneUpdate):
    for i, m in enumerate(_milestones):
        if m["id"] == milestone_id:
            updated = {**m, **milestone.model_dump(exclude_unset=True), "updated_at": datetime.now()}
            _milestones[i] = updated
            return updated
    raise HTTPException(status_code=404, detail="Milestone not found")


@router.delete("/milestones/{milestone_id}", status_code=204)
async def delete_milestone(milestone_id: int):
    for i, m in enumerate(_milestones):
        if m["id"] == milestone_id:
            _milestones.pop(i)
            return
    raise HTTPException(status_code=404, detail="Milestone not found")


# ─── Task Endpoints ───────────────────────────────────────────────────────────

@router.get("/tasks", response_model=dict)
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
):
    filtered = _tasks
    if project_id is not None:
        filtered = [t for t in filtered if t["project_id"] == project_id]
    if status:
        filtered = [t for t in filtered if t["status"] == status]
    if priority:
        filtered = [t for t in filtered if t["priority"] == priority]
    return _paginate(filtered, page, page_size)


@router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: int):
    for t in _tasks:
        if t["id"] == task_id:
            return t
    raise HTTPException(status_code=404, detail="Task not found")


@router.post("/tasks", response_model=Task, status_code=201)
async def create_task(task: TaskCreate):
    global _next_task_id
    now = datetime.now()
    new_task = {
        "id": _next_task_id,
        **task.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _tasks.append(new_task)
    _next_task_id += 1
    return new_task


@router.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: int, task: TaskUpdate):
    for i, t in enumerate(_tasks):
        if t["id"] == task_id:
            updated = {**t, **task.model_dump(exclude_unset=True), "updated_at": datetime.now()}
            _tasks[i] = updated
            return updated
    raise HTTPException(status_code=404, detail="Task not found")


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int):
    for i, t in enumerate(_tasks):
        if t["id"] == task_id:
            _tasks.pop(i)
            return
    raise HTTPException(status_code=404, detail="Task not found")


# ─── Resource Endpoints ───────────────────────────────────────────────────────

@router.get("/resources", response_model=dict)
async def list_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    project_id: Optional[int] = Query(None),
    type: Optional[str] = Query(None),
):
    filtered = _resources
    if project_id is not None:
        filtered = [r for r in filtered if r["project_id"] == project_id]
    if type:
        filtered = [r for r in filtered if r["type"] == type]
    return _paginate(filtered, page, page_size)


@router.get("/resources/{resource_id}", response_model=Resource)
async def get_resource(resource_id: int):
    for r in _resources:
        if r["id"] == resource_id:
            return r
    raise HTTPException(status_code=404, detail="Resource not found")


@router.post("/resources", response_model=Resource, status_code=201)
async def create_resource(resource: ResourceCreate):
    global _next_resource_id
    now = datetime.now()
    new_resource = {
        "id": _next_resource_id,
        **resource.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _resources.append(new_resource)
    _next_resource_id += 1
    return new_resource


@router.put("/resources/{resource_id}", response_model=Resource)
async def update_resource(resource_id: int, resource: ResourceUpdate):
    for i, r in enumerate(_resources):
        if r["id"] == resource_id:
            updated = {**r, **resource.model_dump(exclude_unset=True), "updated_at": datetime.now()}
            _resources[i] = updated
            return updated
    raise HTTPException(status_code=404, detail="Resource not found")


@router.delete("/resources/{resource_id}", status_code=204)
async def delete_resource(resource_id: int):
    for i, r in enumerate(_resources):
        if r["id"] == resource_id:
            _resources.pop(i)
            return
    raise HTTPException(status_code=404, detail="Resource not found")


# ─── Time Entry Endpoints ─────────────────────────────────────────────────────

@router.get("/time-entries", response_model=dict)
async def list_time_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    task_id: Optional[int] = Query(None),
    user: Optional[str] = Query(None),
):
    filtered = _time_entries
    if task_id is not None:
        filtered = [t for t in filtered if t["task_id"] == task_id]
    if user:
        filtered = [t for t in filtered if t["user"] == user]
    return _paginate(filtered, page, page_size)


@router.get("/time-entries/{entry_id}", response_model=TimeEntry)
async def get_time_entry(entry_id: int):
    for t in _time_entries:
        if t["id"] == entry_id:
            return t
    raise HTTPException(status_code=404, detail="Time entry not found")


@router.post("/time-entries", response_model=TimeEntry, status_code=201)
async def create_time_entry(entry: TimeEntryCreate):
    global _next_time_entry_id
    now = datetime.now()
    new_entry = {
        "id": _next_time_entry_id,
        **entry.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _time_entries.append(new_entry)
    _next_time_entry_id += 1
    return new_entry


@router.put("/time-entries/{entry_id}", response_model=TimeEntry)
async def update_time_entry(entry_id: int, entry: TimeEntryUpdate):
    for i, t in enumerate(_time_entries):
        if t["id"] == entry_id:
            updated = {**t, **entry.model_dump(exclude_unset=True), "updated_at": datetime.now()}
            _time_entries[i] = updated
            return updated
    raise HTTPException(status_code=404, detail="Time entry not found")


@router.delete("/time-entries/{entry_id}", status_code=204)
async def delete_time_entry(entry_id: int):
    for i, t in enumerate(_time_entries):
        if t["id"] == entry_id:
            _time_entries.pop(i)
            return
    raise HTTPException(status_code=404, detail="Time entry not found")
