"""
ContinuousBI CRUD API endpoints.
Provides list, retrieve, create, update, and delete operations for BI reports.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/reports", tags=["continuous-bi"])


# ── Synthetic in-memory store ────────────────────────────────────────────────
class ReportModel(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    report_type: str = "dashboard"
    owner: str = "system"
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReportCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    report_type: str = "dashboard"
    owner: str = "system"
    is_active: bool = True


class ReportUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    report_type: Optional[str] = None
    owner: Optional[str] = None
    is_active: Optional[bool] = None


# Seed data
_reports: List[ReportModel] = [
    ReportModel(id=1, name="Revenue Dashboard", description="Monthly revenue trends",
                report_type="dashboard", owner="finance-team"),
    ReportModel(id=2, name="User Growth", description="Weekly active users",
                report_type="chart", owner="growth-team"),
    ReportModel(id=3, name="Churn Analysis", description="Customer churn breakdown",
                report_type="table", owner="retention-team"),
    ReportModel(id=4, name="Sales Pipeline", description="Deal stage funnel",
                report_type="funnel", owner="sales-team"),
    ReportModel(id=5, name="Support Tickets", description="Ticket volume by category",
                report_type="chart", owner="support-team"),
]
_next_id: int = 6


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_model=List[ReportModel])
async def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    report_type: Optional[str] = None,
    is_active: Optional[bool] = None,
 -> List[ReportModel]:
    """List all reports with optional filtering and pagination."""
    try:
        filtered = _reports
        if report_type:
            filtered = [r for r in filtered if r.report_type == report_type]
        if is_active is not None:
            filtered = [r for r in filtered if r.is_active == is_active]
        return filtered[skip : skip + limit]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{report_id}", response_model=ReportModel)
async def get_report(report_id: int) -> ReportModel:
    """Retrieve a single report by ID."""
    try:
        for r in _reports:
            if r.id == report_id:
                return r
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ReportModel, status_code=201)
async def create_report(payload: ReportCreate) -> ReportModel:
    """Create a new report."""
    try:
        global _next_id
        report = ReportModel(id=_next_id, **payload.model_dump())
        _reports.append(report)
        _next_id += 1
        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{report_id}", response_model=ReportModel)
async def update_report(report_id: int, payload: ReportUpdate) -> ReportModel:
    """Update an existing report."""
    try:
        for i, r in enumerate(_reports -> ReportModel:
            if r.id == report_id:
                updates = payload.model_dump(exclude_unset=True)
                updates["updated_at"] = datetime.utcnow()
                _reports[i] = r.model_copy(update=updates)
                return _reports[i]
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{report_id}", status_code=204)
async def delete_report(report_id: int) -> None:
    """Delete a report by ID."""
    try:
        for i, r in enumerate(_reports -> None:
            if r.id == report_id:
                _reports.pop(i)
                return
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
