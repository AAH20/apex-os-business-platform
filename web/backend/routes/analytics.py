"""Analytics module CRUD API endpoints for dashboards."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/dashboards", tags=["analytics"])


class DashboardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None
    layout: str = Field(default="grid")
    is_public: bool = False


class DashboardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = None
    layout: Optional[str] = None
    is_public: Optional[bool] = None


class DashboardResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    layout: str
    is_public: bool
    created_at: str
    updated_at: str


_dashboards = [
    {"id": i, "name": f"Dashboard {i}", "description": f"Sample dashboard {i}",
     "layout": "grid", "is_public": i % 2 == 0,
     "created_at": "2025-01-01T00:00:00", "updated_at": "2025-01-01T00:00:00"}
    for i in range(1, 26)
]
_next_id = 26


@router.get("", response_model=list[DashboardResponse])
def list_dashboards(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    start = (page - 1) * page_size
    return _dashboards[start:start + page_size]


@router.get("/{dashboard_id}", response_model=DashboardResponse)
def get_dashboard(dashboard_id: int):
    for d in _dashboards:
        if d["id"] == dashboard_id:
            return d
    raise HTTPException(status_code=404, detail="Dashboard not found")


@router.post("", response_model=DashboardResponse, status_code=201)
def create_dashboard(body: DashboardCreate):
    global _next_id
    now = datetime.utcnow().isoformat()
    d = {"id": _next_id, **body.model_dump(), "created_at": now, "updated_at": now}
    _dashboards.append(d)
    _next_id += 1
    return d


@router.put("/{dashboard_id}", response_model=DashboardResponse)
def update_dashboard(dashboard_id: int, body: DashboardUpdate):
    for d in _dashboards:
        if d["id"] == dashboard_id:
            for k, v in body.model_dump(exclude_unset=True).items():
                d[k] = v
            d["updated_at"] = datetime.utcnow().isoformat()
            return d
    raise HTTPException(status_code=404, detail="Dashboard not found")


@router.delete("/{dashboard_id}", status_code=204)
def delete_dashboard(dashboard_id: int):
    for i, d in enumerate(_dashboards):
        if d["id"] == dashboard_id:
            _dashboards.pop(i)
            return
    raise HTTPException(status_code=404, detail="Dashboard not found")
