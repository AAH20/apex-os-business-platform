"""Project CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    status: str = Field(default="active", pattern="^(active|archived|completed)$")
    owner: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|archived|completed)$")
    owner: Optional[str] = None


class Project(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Synthetic in-memory data store
_projects: List[dict] = [
    {
        "id": i,
        "name": f"Project {i}",
        "description": f"Description for project {i}",
        "status": "active" if i % 3 else "completed",
        "owner": f"user{i % 5 + 1}@example.com",
        "created_at": datetime(2024, 1, i),
        "updated_at": datetime(2024, 6, i),
    }
    for i in range(1, 26)
]
_next_id = 26


@router.get("", response_model=dict)
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
 -> dict:
    """List all projects with pagination."""
    try:
        filtered = _projects
        if status_filter:
            filtered = [p for p in filtered if p["status"] == status_filter]
        start = (page - 1) * page_size
        end = start + page_size
        items = filtered[start:end]
        return {
            "items": items,
            "total": len(filtered),
            "page": page,
            "page_size": page_size,
            "pages": (len(filtered) + page_size - 1) // page_size,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: int):
    """Get a single project by ID."""
    try:
        for p in _projects:
            if p["id"] == project_id:
                return p
        raise HTTPException(status_code=404, detail="Project not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=Project, status_code=201)
async def create_project(project: ProjectCreate):
    """Create a new project."""
    try:
        global _next_id
        now = datetime.now()
        new_project = {
            "id": _next_id,
            **project.model_dump(),
            "created_at": now,
            "updated_at": now,
        }
        _projects.append(new_project)
        _next_id += 1
        return new_project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}", response_model=Project)
async def update_project(project_id: int, project: ProjectUpdate):
    """Update an existing project."""
    try:
        for i, p in enumerate(_projects -> Project:
            if p["id"] == project_id:
                updated = {**p, **project.model_dump(exclude_unset=True), "updated_at": datetime.now()}
                _projects[i] = updated
                return updated
        raise HTTPException(status_code=404, detail="Project not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int):
    """Delete a project."""
    try:
        for i, p in enumerate(_projects -> None:
            if p["id"] == project_id:
                _projects.pop(i)
                return
        raise HTTPException(status_code=404, detail="Project not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
