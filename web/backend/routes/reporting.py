"""Reporting module CRUD API endpoints for reports, templates, schedules, and subscriptions."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/reporting", tags=["reporting"])


# ─── Pydantic Models ─────────────────────────────────────────────────────────

class ReportCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    report_type: str = Field(default="sales")
    config: Optional[dict] = None
    is_active: bool = True


class ReportUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    report_type: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None


class ReportTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: str = Field(default="general")
    query: Optional[str] = None
    parameters: Optional[dict] = None


class ReportTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    query: Optional[str] = None
    parameters: Optional[dict] = None


class ScheduledReportCreate(BaseModel):
    report_id: int
    name: str = Field(..., min_length=1, max_length=200)
    cron_expression: str = Field(..., min_length=1)
    recipients: list[str] = Field(default_factory=list)
    is_active: bool = True


class ScheduledReportUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    cron_expression: Optional[str] = None
    recipients: Optional[list[str]] = None
    is_active: Optional[bool] = None


class ReportSubscriptionCreate(BaseModel):
    user_id: int
    report_id: int
    delivery_method: str = Field(default="email")
    frequency: str = Field(default="weekly")
    is_active: bool = True


class ReportSubscriptionUpdate(BaseModel):
    delivery_method: Optional[str] = None
    frequency: Optional[str] = None
    is_active: Optional[bool] = None


# ─── In-Memory Stores ────────────────────────────────────────────────────────

_reports = [
    {"id": i, "name": f"Report {i}", "description": f"Sample report {i}",
     "report_type": ["sales", "inventory", "financial", "customer"][i % 4],
     "config": {"format": "pdf", "sections": ["summary", "details"]},
     "is_active": i % 3 != 0,
     "created_at": "2025-01-01T00:00:00", "updated_at": "2025-01-01T00:00:00"}
    for i in range(1, 26)
]
_next_report_id = 26

_report_templates = [
    {"id": i, "name": f"Template {i}", "description": f"Sample template {i}",
     "category": ["sales", "marketing", "operations", "finance"][i % 4],
     "query": f"SELECT * FROM data WHERE id = {i}",
     "parameters": {"start_date": "2025-01-01", "end_date": "2025-12-31"},
     "created_at": "2025-01-01T00:00:00", "updated_at": "2025-01-01T00:00:00"}
    for i in range(1, 11)
]
_next_template_id = 11

_scheduled_reports = [
    {"id": i, "report_id": i, "name": f"Scheduled Report {i}",
     "cron_expression": ["0 8 * * *", "0 9 * * 1", "0 10 * * 1,3,5"][i % 3],
     "recipients": [f"user{j}@example.com" for j in range(1, 4)],
     "is_active": i % 2 == 0,
     "created_at": "2025-01-01T00:00:00", "updated_at": "2025-01-01T00:00:00"}
    for i in range(1, 11)
]
_next_scheduled_id = 11

_report_subscriptions = [
    {"id": i, "user_id": i, "report_id": i,
     "delivery_method": ["email", "slack", "webhook"][i % 3],
     "frequency": ["daily", "weekly", "monthly"][i % 3],
     "is_active": i % 2 == 0,
     "created_at": "2025-01-01T00:00:00", "updated_at": "2025-01-01T00:00:00"}
    for i in range(1, 11)
]
_next_subscription_id = 11


# ─── Reports CRUD ────────────────────────────────────────────────────────────

@router.get("/reports", response_model=list[dict])
def list_reports(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    start = (page - 1) * page_size
    return _reports[start:start + page_size]


@router.get("/reports/{report_id}")
def get_report(report_id: int):
    for r in _reports:
        if r["id"] == report_id:
            return r
    raise HTTPException(status_code=404, detail="Report not found")


@router.post("/reports", status_code=201)
def create_report(body: ReportCreate):
    global _next_report_id
    now = datetime.utcnow().isoformat()
    r = {"id": _next_report_id, **body.model_dump(), "created_at": now, "updated_at": now}
    _reports.append(r)
    _next_report_id += 1
    return r


@router.put("/reports/{report_id}")
def update_report(report_id: int, body: ReportUpdate):
    for r in _reports:
        if r["id"] == report_id:
            for k, v in body.model_dump(exclude_unset=True).items():
                r[k] = v
            r["updated_at"] = datetime.utcnow().isoformat()
            return r
    raise HTTPException(status_code=404, detail="Report not found")


@router.delete("/reports/{report_id}", status_code=204)
def delete_report(report_id: int):
    for i, r in enumerate(_reports):
        if r["id"] == report_id:
            _reports.pop(i)
            return
    raise HTTPException(status_code=404, detail="Report not found")


# ─── Report Templates CRUD ───────────────────────────────────────────────────

@router.get("/templates", response_model=list[dict])
def list_templates(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    start = (page - 1) * page_size
    return _report_templates[start:start + page_size]


@router.get("/templates/{template_id}")
def get_template(template_id: int):
    for t in _report_templates:
        if t["id"] == template_id:
            return t
    raise HTTPException(status_code=404, detail="Template not found")


@router.post("/templates", status_code=201)
def create_template(body: ReportTemplateCreate):
    global _next_template_id
    now = datetime.utcnow().isoformat()
    t = {"id": _next_template_id, **body.model_dump(), "created_at": now, "updated_at": now}
    _report_templates.append(t)
    _next_template_id += 1
    return t


@router.put("/templates/{template_id}")
def update_template(template_id: int, body: ReportTemplateUpdate):
    for t in _report_templates:
        if t["id"] == template_id:
            for k, v in body.model_dump(exclude_unset=True).items():
                t[k] = v
            t["updated_at"] = datetime.utcnow().isoformat()
            return t
    raise HTTPException(status_code=404, detail="Template not found")


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(template_id: int):
    for i, t in enumerate(_report_templates):
        if t["id"] == template_id:
            _report_templates.pop(i)
            return
    raise HTTPException(status_code=404, detail="Template not found")


# ─── Scheduled Reports CRUD ──────────────────────────────────────────────────

@router.get("/scheduled", response_model=list[dict])
def list_scheduled(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    start = (page - 1) * page_size
    return _scheduled_reports[start:start + page_size]


@router.get("/scheduled/{scheduled_id}")
def get_scheduled(scheduled_id: int):
    for s in _scheduled_reports:
        if s["id"] == scheduled_id:
            return s
    raise HTTPException(status_code=404, detail="Scheduled report not found")


@router.post("/scheduled", status_code=201)
def create_scheduled(body: ScheduledReportCreate):
    global _next_scheduled_id
    now = datetime.utcnow().isoformat()
    s = {"id": _next_scheduled_id, **body.model_dump(), "created_at": now, "updated_at": now}
    _scheduled_reports.append(s)
    _next_scheduled_id += 1
    return s


@router.put("/scheduled/{scheduled_id}")
def update_scheduled(scheduled_id: int, body: ScheduledReportUpdate):
    for s in _scheduled_reports:
        if s["id"] == scheduled_id:
            for k, v in body.model_dump(exclude_unset=True).items():
                s[k] = v
            s["updated_at"] = datetime.utcnow().isoformat()
            return s
    raise HTTPException(status_code=404, detail="Scheduled report not found")


@router.delete("/scheduled/{scheduled_id}", status_code=204)
def delete_scheduled(scheduled_id: int):
    for i, s in enumerate(_scheduled_reports):
        if s["id"] == scheduled_id:
            _scheduled_reports.pop(i)
            return
    raise HTTPException(status_code=404, detail="Scheduled report not found")


# ─── Report Subscriptions CRUD ───────────────────────────────────────────────

@router.get("/subscriptions", response_model=list[dict])
def list_subscriptions(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    start = (page - 1) * page_size
    return _report_subscriptions[start:start + page_size]


@router.get("/subscriptions/{subscription_id}")
def get_subscription(subscription_id: int):
    for s in _report_subscriptions:
        if s["id"] == subscription_id:
            return s
    raise HTTPException(status_code=404, detail="Subscription not found")


@router.post("/subscriptions", status_code=201)
def create_subscription(body: ReportSubscriptionCreate):
    global _next_subscription_id
    now = datetime.utcnow().isoformat()
    s = {"id": _next_subscription_id, **body.model_dump(), "created_at": now, "updated_at": now}
    _report_subscriptions.append(s)
    _next_subscription_id += 1
    return s


@router.put("/subscriptions/{subscription_id}")
def update_subscription(subscription_id: int, body: ReportSubscriptionUpdate):
    for s in _report_subscriptions:
        if s["id"] == subscription_id:
            for k, v in body.model_dump(exclude_unset=True).items():
                s[k] = v
            s["updated_at"] = datetime.utcnow().isoformat()
            return s
    raise HTTPException(status_code=404, detail="Subscription not found")


@router.delete("/subscriptions/{subscription_id}", status_code=204)
def delete_subscription(subscription_id: int):
    for i, s in enumerate(_report_subscriptions):
        if s["id"] == subscription_id:
            _report_subscriptions.pop(i)
            return
    raise HTTPException(status_code=404, detail="Subscription not found")
