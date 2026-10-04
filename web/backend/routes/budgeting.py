"""Budgeting module CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/budgeting", tags=["budgeting"])

# ─── In-memory data stores ──────────────────────────────────────────────────

_budgets_db = [
    {"id": 1, "name": "FY2026 Operating Budget", "fiscal_year": 2026, "status": "active",
     "total_budgeted": 5000000.00, "total_actual": 3200000.00, "currency": "USD",
     "start_date": "2026-01-01", "end_date": "2026-12-31", "created_at": "2026-01-01T00:00:00"},
    {"id": 2, "name": "FY2026 Marketing Budget", "fiscal_year": 2026, "status": "draft",
     "total_budgeted": 1200000.00, "total_actual": 450000.00, "currency": "USD",
     "start_date": "2026-01-01", "end_date": "2026-12-31", "created_at": "2026-01-15T00:00:00"},
    {"id": 3, "name": "FY2025 Operating Budget", "fiscal_year": 2025, "status": "closed",
     "total_budgeted": 4500000.00, "total_actual": 4350000.00, "currency": "USD",
     "start_date": "2025-01-01", "end_date": "2025-12-31", "created_at": "2025-01-01T00:00:00"},
]
_budget_lines_db = [
    {"id": 1, "budget_id": 1, "cost_center_id": 1, "category": "Salaries",
     "description": "Engineering salaries", "budgeted_amount": 2000000.00, "actual_amount": 1300000.00,
     "period": "2026-Q1", "created_at": "2026-01-01T00:00:00"},
    {"id": 2, "budget_id": 1, "cost_center_id": 2, "category": "Infrastructure",
     "description": "Cloud hosting", "budgeted_amount": 500000.00, "actual_amount": 320000.00,
     "period": "2026-Q1", "created_at": "2026-01-01T00:00:00"},
    {"id": 3, "budget_id": 2, "cost_center_id": 3, "category": "Advertising",
     "description": "Digital ads", "budgeted_amount": 800000.00, "actual_amount": 300000.00,
     "period": "2026-Q1", "created_at": "2026-01-15T00:00:00"},
]
_cost_centers_db = [
    {"id": 1, "name": "Engineering", "code": "ENG", "manager": "Alice Chen",
     "department": "Technology", "created_at": "2026-01-01T00:00:00"},
    {"id": 2, "name": "Infrastructure", "code": "INF", "manager": "Bob Smith",
     "department": "Technology", "created_at": "2026-01-01T00:00:00"},
    {"id": 3, "name": "Marketing", "code": "MKT", "manager": "Carol Davis",
     "department": "Sales", "created_at": "2026-01-01T00:00:00"},
    {"id": 4, "name": "Sales", "code": "SAL", "manager": "Dave Wilson",
     "department": "Sales", "created_at": "2026-01-01T00:00:00"},
]
_variance_analysis_db = [
    {"id": 1, "budget_id": 1, "budget_line_id": 1, "period": "2026-Q1",
     "budgeted_amount": 2000000.00, "actual_amount": 1300000.00,
     "variance_amount": -700000.00, "variance_percent": -35.0,
     "status": "under_budget", "notes": "Lower headcount than planned",
     "created_at": "2026-04-01T00:00:00"},
    {"id": 2, "budget_id": 1, "budget_line_id": 2, "period": "2026-Q1",
     "budgeted_amount": 500000.00, "actual_amount": 320000.00,
     "variance_amount": -180000.00, "variance_percent": -36.0,
     "status": "under_budget", "notes": "Optimized cloud spend",
     "created_at": "2026-04-01T00:00:00"},
    {"id": 3, "budget_id": 2, "budget_line_id": 3, "period": "2026-Q1",
     "budgeted_amount": 800000.00, "actual_amount": 300000.00,
     "variance_amount": -500000.00, "variance_percent": -62.5,
     "status": "under_budget", "notes": "Campaigns delayed",
     "created_at": "2026-04-01T00:00:00"},
]

_next_budget_id = 4
_next_line_id = 4
_next_cc_id = 5
_next_variance_id = 4


# ─── Pydantic Models ────────────────────────────────────────────────────────

class BudgetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    fiscal_year: int = Field(..., ge=2000, le=2100)
    status: str = Field("draft", pattern="^(draft|active|closed)$")
    total_budgeted: float = Field(0.0, ge=0)
    total_actual: float = Field(0.0, ge=0)
    currency: str = "USD"
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class BudgetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    fiscal_year: Optional[int] = Field(None, ge=2000, le=2100)
    status: Optional[str] = Field(None, pattern="^(draft|active|closed)$")
    total_budgeted: Optional[float] = Field(None, ge=0)
    total_actual: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class BudgetResponse(BaseModel):
    id: int
    name: str
    fiscal_year: int
    status: str
    total_budgeted: float
    total_actual: float
    currency: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    created_at: str


class BudgetLineCreate(BaseModel):
    budget_id: int
    cost_center_id: int
    category: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    budgeted_amount: float = Field(0.0, ge=0)
    actual_amount: float = Field(0.0, ge=0)
    period: Optional[str] = None


class BudgetLineUpdate(BaseModel):
    budget_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    budgeted_amount: Optional[float] = Field(None, ge=0)
    actual_amount: Optional[float] = Field(None, ge=0)
    period: Optional[str] = None


class BudgetLineResponse(BaseModel):
    id: int
    budget_id: int
    cost_center_id: int
    category: str
    description: Optional[str] = None
    budgeted_amount: float
    actual_amount: float
    period: Optional[str] = None
    created_at: str


class CostCenterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    manager: Optional[str] = None
    department: Optional[str] = None


class CostCenterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    manager: Optional[str] = None
    department: Optional[str] = None


class CostCenterResponse(BaseModel):
    id: int
    name: str
    code: str
    manager: Optional[str] = None
    department: Optional[str] = None
    created_at: str


class VarianceAnalysisCreate(BaseModel):
    budget_id: int
    budget_line_id: int
    period: str = Field(..., min_length=1, max_length=20)
    budgeted_amount: float = Field(0.0, ge=0)
    actual_amount: float = Field(0.0, ge=0)
    variance_amount: float = 0.0
    variance_percent: float = 0.0
    status: str = Field("on_budget", pattern="^(under_budget|on_budget|over_budget)$")
    notes: Optional[str] = None


class VarianceAnalysisUpdate(BaseModel):
    budget_id: Optional[int] = None
    budget_line_id: Optional[int] = None
    period: Optional[str] = Field(None, min_length=1, max_length=20)
    budgeted_amount: Optional[float] = Field(None, ge=0)
    actual_amount: Optional[float] = Field(None, ge=0)
    variance_amount: Optional[float] = None
    variance_percent: Optional[float] = None
    status: Optional[str] = Field(None, pattern="^(under_budget|on_budget|over_budget)$")
    notes: Optional[str] = None


class VarianceAnalysisResponse(BaseModel):
    id: int
    budget_id: int
    budget_line_id: int
    period: str
    budgeted_amount: float
    actual_amount: float
    variance_amount: float
    variance_percent: float
    status: str
    notes: Optional[str] = None
    created_at: str


# ─── Budget Endpoints ───────────────────────────────────────────────────────

@router.get("/budgets/", response_model=List[BudgetResponse])
async def list_budgets(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    fiscal_year: Optional[int] = None,
    status: Optional[str] = None,
):
    results = _budgets_db
    if fiscal_year:
        results = [b for b in results if b["fiscal_year"] == fiscal_year]
    if status:
        results = [b for b in results if b["status"] == status]
    return results[skip : skip + limit]


@router.get("/budgets/{budget_id}", response_model=BudgetResponse)
async def get_budget(budget_id: int):
    for b in _budgets_db:
        if b["id"] == budget_id:
            return b
    raise HTTPException(status_code=404, detail=f"Budget {budget_id} not found")


@router.post("/budgets/", response_model=BudgetResponse, status_code=201)
async def create_budget(budget: BudgetCreate):
    global _next_budget_id
    new = {"id": _next_budget_id, **budget.model_dump(), "created_at": datetime.utcnow().isoformat()}
    _budgets_db.append(new)
    _next_budget_id += 1
    return new


@router.put("/budgets/{budget_id}", response_model=BudgetResponse)
async def update_budget(budget_id: int, budget: BudgetUpdate):
    for i, existing in enumerate(_budgets_db):
        if existing["id"] == budget_id:
            _budgets_db[i] = {**existing, **budget.model_dump(exclude_unset=True)}
            return _budgets_db[i]
    raise HTTPException(status_code=404, detail=f"Budget {budget_id} not found")


@router.delete("/budgets/{budget_id}", status_code=204)
async def delete_budget(budget_id: int):
    for i, b in enumerate(_budgets_db):
        if b["id"] == budget_id:
            _budgets_db.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Budget {budget_id} not found")


# ─── Budget Line Endpoints ──────────────────────────────────────────────────

@router.get("/budget-lines/", response_model=List[BudgetLineResponse])
async def list_budget_lines(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    budget_id: Optional[int] = None,
    cost_center_id: Optional[int] = None,
):
    results = _budget_lines_db
    if budget_id:
        results = [l for l in results if l["budget_id"] == budget_id]
    if cost_center_id:
        results = [l for l in results if l["cost_center_id"] == cost_center_id]
    return results[skip : skip + limit]


@router.get("/budget-lines/{line_id}", response_model=BudgetLineResponse)
async def get_budget_line(line_id: int):
    for l in _budget_lines_db:
        if l["id"] == line_id:
            return l
    raise HTTPException(status_code=404, detail=f"Budget line {line_id} not found")


@router.post("/budget-lines/", response_model=BudgetLineResponse, status_code=201)
async def create_budget_line(line: BudgetLineCreate):
    global _next_line_id
    new = {"id": _next_line_id, **line.model_dump(), "created_at": datetime.utcnow().isoformat()}
    _budget_lines_db.append(new)
    _next_line_id += 1
    return new


@router.put("/budget-lines/{line_id}", response_model=BudgetLineResponse)
async def update_budget_line(line_id: int, line: BudgetLineUpdate):
    for i, existing in enumerate(_budget_lines_db):
        if existing["id"] == line_id:
            _budget_lines_db[i] = {**existing, **line.model_dump(exclude_unset=True)}
            return _budget_lines_db[i]
    raise HTTPException(status_code=404, detail=f"Budget line {line_id} not found")


@router.delete("/budget-lines/{line_id}", status_code=204)
async def delete_budget_line(line_id: int):
    for i, l in enumerate(_budget_lines_db):
        if l["id"] == line_id:
            _budget_lines_db.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Budget line {line_id} not found")


# ─── Cost Center Endpoints ──────────────────────────────────────────────────

@router.get("/cost-centers/", response_model=List[CostCenterResponse])
async def list_cost_centers(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    department: Optional[str] = None,
):
    results = _cost_centers_db
    if department:
        results = [c for c in results if c.get("department") == department]
    return results[skip : skip + limit]


@router.get("/cost-centers/{cc_id}", response_model=CostCenterResponse)
async def get_cost_center(cc_id: int):
    for c in _cost_centers_db:
        if c["id"] == cc_id:
            return c
    raise HTTPException(status_code=404, detail=f"Cost center {cc_id} not found")


@router.post("/cost-centers/", response_model=CostCenterResponse, status_code=201)
async def create_cost_center(cc: CostCenterCreate):
    global _next_cc_id
    new = {"id": _next_cc_id, **cc.model_dump(), "created_at": datetime.utcnow().isoformat()}
    _cost_centers_db.append(new)
    _next_cc_id += 1
    return new


@router.put("/cost-centers/{cc_id}", response_model=CostCenterResponse)
async def update_cost_center(cc_id: int, cc: CostCenterUpdate):
    for i, existing in enumerate(_cost_centers_db):
        if existing["id"] == cc_id:
            _cost_centers_db[i] = {**existing, **cc.model_dump(exclude_unset=True)}
            return _cost_centers_db[i]
    raise HTTPException(status_code=404, detail=f"Cost center {cc_id} not found")


@router.delete("/cost-centers/{cc_id}", status_code=204)
async def delete_cost_center(cc_id: int):
    for i, c in enumerate(_cost_centers_db):
        if c["id"] == cc_id:
            _cost_centers_db.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Cost center {cc_id} not found")


# ─── Variance Analysis Endpoints ────────────────────────────────────────────

@router.get("/variance-analysis/", response_model=List[VarianceAnalysisResponse])
async def list_variance_analysis(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    budget_id: Optional[int] = None,
    status: Optional[str] = None,
):
    results = _variance_analysis_db
    if budget_id:
        results = [v for v in results if v["budget_id"] == budget_id]
    if status:
        results = [v for v in results if v["status"] == status]
    return results[skip : skip + limit]


@router.get("/variance-analysis/{variance_id}", response_model=VarianceAnalysisResponse)
async def get_variance_analysis(variance_id: int):
    for v in _variance_analysis_db:
        if v["id"] == variance_id:
            return v
    raise HTTPException(status_code=404, detail=f"Variance analysis {variance_id} not found")


@router.post("/variance-analysis/", response_model=VarianceAnalysisResponse, status_code=201)
async def create_variance_analysis(variance: VarianceAnalysisCreate):
    global _next_variance_id
    new = {"id": _next_variance_id, **variance.model_dump(), "created_at": datetime.utcnow().isoformat()}
    _variance_analysis_db.append(new)
    _next_variance_id += 1
    return new


@router.put("/variance-analysis/{variance_id}", response_model=VarianceAnalysisResponse)
async def update_variance_analysis(variance_id: int, variance: VarianceAnalysisUpdate):
    for i, existing in enumerate(_variance_analysis_db):
        if existing["id"] == variance_id:
            _variance_analysis_db[i] = {**existing, **variance.model_dump(exclude_unset=True)}
            return _variance_analysis_db[i]
    raise HTTPException(status_code=404, detail=f"Variance analysis {variance_id} not found")


@router.delete("/variance-analysis/{variance_id}", status_code=204)
async def delete_variance_analysis(variance_id: int):
    for i, v in enumerate(_variance_analysis_db):
        if v["id"] == variance_id:
            _variance_analysis_db.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Variance analysis {variance_id} not found")
