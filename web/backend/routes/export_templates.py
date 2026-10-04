"""Export Templates module CRUD API endpoints for templates, jobs, and schedules."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/export-templates", tags=["export-templates"])


# ─── Pydantic Models ─────────────────────────────────────────────────────────

class ExportTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: str = Field(default="general")
    format: str = Field(default="csv")
    query: Optional[str] = None
    parameters: Optional[dict] = None
    is_active: bool = True


class ExportTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    format: Optional[str] = None
    query: Optional[str] = None
    parameters: Optional[dict] = None
    is_active: Optional[bool] = None


class ExportJobCreate(BaseModel):
    template_id: int
    name: str = Field(..., min_length=1, max_length=200)
    status: str = Field(default="pending")
    parameters: Optional[dict] = None
    row_count: Optional[int] = None
    file_size: Optional[str] = None


class ExportJobUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[str] = None
    parameters: Optional[dict] = None
    row_count: Optional[int] = None
    file_size: Optional[str] = None


class ExportScheduleCreate(BaseModel):
    template_id: int
    name: str = Field(..., min_length=1, max_length=200)
    cron_expression: str = Field(..., min_length=1)
    recipients: list[str] = Field(default_factory=list)
    is_active: bool = True


class ExportScheduleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    cron_expression: Optional[str] = None
    recipients: Optional[list[str]] = None
    is_active: Optional[bool] = None


# ─── In-Memory Stores ────────────────────────────────────────────────────────

_export_templates = [
    {"id": i, "name": f"Export Template {i}", "description": f"Sample export template {i}",
     "category": ["sales", "marketing", "operations", "finance"][i % 4],
     "format": ["csv", "json", "xlsx", "pdf"][i % 4],
     "query": f"SELECT * FROM data WHERE id = {i}",
     "parameters": {"start_date": "2025-01-01", "end_date": "2025-12-31"},
     "is_active": i % 3 != 0,
     "created_at": "2025-01-01T00:00:00", "updated_at": "2025-01-01T00:00:00"}
    for i in range(1, 11)
]
_next_template_id = 11

_export_jobs = [
    {"id": i, "template_id": i, "name": f"Export Job {i}",
     "status": ["pending", "running", "completed", "failed"][i % 4],
     "parameters": {"start_date": "2025-01-01", "end_date": "2025-12-31"},
     "row_count": i * 1000,
     "file_size": f"{i * 1.5:.1f} MB",
     "created_at": "2025-01-01T00:00:00", "updated_at": "2025-01-01T00:00:00"}
    for i in range(1, 11)
]
_next_job_id = 11

_export_schedules = [
    {"id": i, "template_id": i, "name": f"Export Schedule {i}",
     "cron_expression": ["0 8 * * *", "0 9 * * 1", "0 10 * * 1,3,5"][i % 3],
     "recipients": [f"user{j}@example.com" for j in range(1, 4)],
     "is_active": i % 2 == 0,
     "created_at": "2025-01-01T00:00:00", "updated_at": "2025-01-01T00:00:00"}
    for i in range(1, 11)
]
_next_schedule_id = 11


# ─── Export Templates CRUD ───────────────────────────────────────────────────

@router.get("/templates", response_model=list[dict])
def list_templates(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    start = (page - 1) * page_size
    return _export_templates[start:start + page_size]


@router.get("/templates/{template_id}")
def get_template(template_id: int):
    for t in _export_templates:
        if t["id"] == template_id:
            return t
    raise HTTPException(status_code=404, detail="Export template not found")


@router.post("/templates", status_code=201)
def create_template(body: ExportTemplateCreate):
    global _next_template_id
    now = datetime.utcnow().isoformat()
    t = {"id": _next_template_id, **body.model_dump(), "created_at": now, "updated_at": now}
    _export_templates.append(t)
    _next_template_id += 1
    return t


@router.put("/templates/{template_id}")
def update_template(template_id: int, body: ExportTemplateUpdate):
    for t in _export_templates:
        if t["id"] == template_id:
            for k, v in body.model_dump(exclude_unset=True).items():
                t[k] = v
            t["updated_at"] = datetime.utcnow().isoformat()
            return t
    raise HTTPException(status_code=404, detail="Export template not found")


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(template_id: int):
    for i, t in enumerate(_export_templates):
        if t["id"] == template_id:
            _export_templates.pop(i)
            return
    raise HTTPException(status_code=404, detail="Export template not found")


# ─── Export Jobs CRUD ────────────────────────────────────────────────────────

@router.get("/jobs", response_model=list[dict])
def list_jobs(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    start = (page - 1) * page_size
    return _export_jobs[start:start + page_size]


@router.get("/jobs/{job_id}")
def get_job(job_id: int):
    for j in _export_jobs:
        if j["id"] == job_id:
            return j
    raise HTTPException(status_code=404, detail="Export job not found")


@router.post("/jobs", status_code=201)
def create_job(body: ExportJobCreate):
    global _next_job_id
    now = datetime.utcnow().isoformat()
    j = {"id": _next_job_id, **body.model_dump(), "created_at": now, "updated_at": now}
    _export_jobs.append(j)
    _next_job_id += 1
    return j


@router.put("/jobs/{job_id}")
def update_job(job_id: int, body: ExportJobUpdate):
    for j in _export_jobs:
        if j["id"] == job_id:
            for k, v in body.model_dump(exclude_unset=True).items():
                j[k] = v
            j["updated_at"] = datetime.utcnow().isoformat()
            return j
    raise HTTPException(status_code=404, detail="Export job not found")


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: int):
    for i, j in enumerate(_export_jobs):
        if j["id"] == job_id:
            _export_jobs.pop(i)
            return
    raise HTTPException(status_code=404, detail="Export job not found")


# ─── Export Schedules CRUD ───────────────────────────────────────────────────

@router.get("/schedules", response_model=list[dict])
def list_schedules(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    start = (page - 1) * page_size
    return _export_schedules[start:start + page_size]


@router.get("/schedules/{schedule_id}")
def get_schedule(schedule_id: int):
    for s in _export_schedules:
        if s["id"] == schedule_id:
            return s
    raise HTTPException(status_code=404, detail="Export schedule not found")


@router.post("/schedules", status_code=201)
def create_schedule(body: ExportScheduleCreate):
    global _next_schedule_id
    now = datetime.utcnow().isoformat()
    s = {"id": _next_schedule_id, **body.model_dump(), "created_at": now, "updated_at": now}
    _export_schedules.append(s)
    _next_schedule_id += 1
    return s


@router.put("/schedules/{schedule_id}")
def update_schedule(schedule_id: int, body: ExportScheduleUpdate):
    for s in _export_schedules:
        if s["id"] == schedule_id:
            for k, v in body.model_dump(exclude_unset=True).items():
                s[k] = v
            s["updated_at"] = datetime.utcnow().isoformat()
            return s
    raise HTTPException(status_code=404, detail="Export schedule not found")


@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: int):
    for i, s in enumerate(_export_schedules):
        if s["id"] == schedule_id:
            _export_schedules.pop(i)
            return
    raise HTTPException(status_code=404, detail="Export schedule not found")
