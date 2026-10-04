"""Cost Management module CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/cost-management", tags=["cost-management"])

# ─── In-memory data stores ──────────────────────────────────────────────────

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

_cost_allocations_db = [
    {"id": 1, "cost_center_id": 1, "allocation_name": "Q1 Engineering Salaries",
     "amount": 500000.00, "period": "2026-Q1", "description": "Salaries for Q1",
     "created_at": "2026-01-01T00:00:00"},
    {"id": 2, "cost_center_id": 2, "allocation_name": "Q1 Cloud Infrastructure",
     "amount": 125000.00, "period": "2026-Q1", "description": "AWS/Azure costs",
     "created_at": "2026-01-01T00:00:00"},
    {"id": 3, "cost_center_id": 3, "allocation_name": "Q1 Marketing Campaign",
     "amount": 200000.00, "period": "2026-Q1", "description": "Digital advertising",
     "created_at": "2026-01-01T00:00:00"},
]

_cost_forecasts_db = [
    {"id": 1, "cost_center_id": 1, "forecast_name": "FY2026 Engineering Forecast",
     "period": "2026", "forecast_amount": 2400000.00, "actual_amount": 1800000.00,
     "created_at": "2026-01-01T00:00:00"},
    {"id": 2, "cost_center_id": 2, "forecast_name": "FY2026 Infrastructure Forecast",
     "period": "2026", "forecast_amount": 600000.00, "actual_amount": 450000.00,
     "created_at": "2026-01-01T00:00:00"},
    {"id": 3, "cost_center_id": 3, "forecast_name": "FY2026 Marketing Forecast",
     "period": "2026", "forecast_amount": 800000.00, "actual_amount": 600000.00,
     "created_at": "2026-01-01T00:00:00"},
]

_cost_variances_db = [
    {"id": 1, "cost_center_id": 1, "period": "2026-Q1",
     "budgeted_amount": 500000.00, "actual_amount": 450000.00,
     "variance_amount": -50000.00, "variance_percent": -10.0,
     "status": "under_budget", "notes": "Lower headcount than planned",
     "created_at": "2026-04-01T00:00:00"},
    {"id": 2, "cost_center_id": 2, "period": "2026-Q1",
     "budgeted_amount": 125000.00, "actual_amount": 140000.00,
     "variance_amount": 15000.00, "variance_percent": 12.0,
     "status": "over_budget", "notes": "Higher cloud usage",
     "created_at": "2026-04-01T00:00:00"},
    {"id": 3, "cost_center_id": 3, "period": "2026-Q1",
     "budgeted_amount": 200000.00, "actual_amount": 180000.00,
     "variance_amount": -20000.00, "variance_percent": -10.0,
     "status": "under_budget", "notes": "Campaigns delayed",
     "created_at": "2026-04-01T00:00:00"},
]

_next_cc_id = 5
_next_alloc_id = 4
_next_forecast_id = 4
_next_variance_id = 4


# ─── Pydantic Models ────────────────────────────────────────────────────────

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


class CostAllocationCreate(BaseModel):
    cost_center_id: int
    allocation_name: str = Field(..., min_length=1, max_length=200)
    amount: float = Field(0.0, ge=0)
    period: Optional[str] = None
    description: Optional[str] = None


class CostAllocationUpdate(BaseModel):
    cost_center_id: Optional[int] = None
    allocation_name: Optional[str] = Field(None, min_length=1, max_length=200)
    amount: Optional[float] = Field(None, ge=0)
    period: Optional[str] = None
    description: Optional[str] = None


class CostAllocationResponse(BaseModel):
    id: int
    cost_center_id: int
    allocation_name: str
    amount: float
    period: Optional[str] = None
    description: Optional[str] = None
    created_at: str


class CostForecastCreate(BaseModel):
    cost_center_id: int
    forecast_name: str = Field(..., min_length=1, max_length=200)
    period: str = Field(..., min_length=1, max_length=20)
    forecast_amount: float = Field(0.0, ge=0)
    actual_amount: float = Field(0.0, ge=0)


class CostForecastUpdate(BaseModel):
    cost_center_id: Optional[int] = None
    forecast_name: Optional[str] = Field(None, min_length=1, max_length=200)
    period: Optional[str] = Field(None, min_length=1, max_length=20)
    forecast_amount: Optional[float] = Field(None, ge=0)
    actual_amount: Optional[float] = Field(None, ge=0)


class CostForecastResponse(BaseModel):
    id: int
    cost_center_id: int
    forecast_name: str
    period: str
    forecast_amount: float
    actual_amount: float
    created_at: str


class CostVarianceCreate(BaseModel):
    cost_center_id: int
    period: str = Field(..., min_length=1, max_length=20)
    budgeted_amount: float = Field(0.0, ge=0)
    actual_amount: float = Field(0.0, ge=0)
    variance_amount: float = 0.0
    variance_percent: float = 0.0
    status: str = Field("on_budget", pattern="^(under_budget|on_budget|over_budget)$")
    notes: Optional[str] = None


class CostVarianceUpdate(BaseModel):
    cost_center_id: Optional[int] = None
    period: Optional[str] = Field(None, min_length=1, max_length=20)
    budgeted_amount: Optional[float] = Field(None, ge=0)
    actual_amount: Optional[float] = Field(None, ge=0)
    variance_amount: Optional[float] = None
    variance_percent: Optional[float] = None
    status: Optional[str] = Field(None, pattern="^(under_budget|on_budget|over_budget)$")
    notes: Optional[str] = None


class CostVarianceResponse(BaseModel):
    id: int
    cost_center_id: int
    period: str
    budgeted_amount: float
    actual_amount: float
    variance_amount: float
    variance_percent: float
    status: str
    notes: Optional[str] = None
    created_at: str


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


# ─── Cost Allocation Endpoints ──────────────────────────────────────────────

@router.get("/cost-allocations/", response_model=List[CostAllocationResponse])
async def list_cost_allocations(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    cost_center_id: Optional[int] = None,
):
    results = _cost_allocations_db
    if cost_center_id:
        results = [a for a in results if a["cost_center_id"] == cost_center_id]
    return results[skip : skip + limit]


@router.get("/cost-allocations/{alloc_id}", response_model=CostAllocationResponse)
async def get_cost_allocation(alloc_id: int):
    for a in _cost_allocations_db:
        if a["id"] == alloc_id:
            return a
    raise HTTPException(status_code=404, detail=f"Cost allocation {alloc_id} not found")


@router.post("/cost-allocations/", response_model=CostAllocationResponse, status_code=201)
async def create_cost_allocation(alloc: CostAllocationCreate):
    global _next_alloc_id
    new = {"id": _next_alloc_id, **alloc.model_dump(), "created_at": datetime.utcnow().isoformat()}
    _cost_allocations_db.append(new)
    _next_alloc_id += 1
    return new


@router.put("/cost-allocations/{alloc_id}", response_model=CostAllocationResponse)
async def update_cost_allocation(alloc_id: int, alloc: CostAllocationUpdate):
    for i, existing in enumerate(_cost_allocations_db):
        if existing["id"] == alloc_id:
            _cost_allocations_db[i] = {**existing, **alloc.model_dump(exclude_unset=True)}
            return _cost_allocations_db[i]
    raise HTTPException(status_code=404, detail=f"Cost allocation {alloc_id} not found")


@router.delete("/cost-allocations/{alloc_id}", status_code=204)
async def delete_cost_allocation(alloc_id: int):
    for i, a in enumerate(_cost_allocations_db):
        if a["id"] == alloc_id:
            _cost_allocations_db.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Cost allocation {alloc_id} not found")


# ─── Cost Forecast Endpoints ────────────────────────────────────────────────

@router.get("/cost-forecasts/", response_model=List[CostForecastResponse])
async def list_cost_forecasts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    cost_center_id: Optional[int] = None,
):
    results = _cost_forecasts_db
    if cost_center_id:
        results = [f for f in results if f["cost_center_id"] == cost_center_id]
    return results[skip : skip + limit]


@router.get("/cost-forecasts/{forecast_id}", response_model=CostForecastResponse)
async def get_cost_forecast(forecast_id: int):
    for f in _cost_forecasts_db:
        if f["id"] == forecast_id:
            return f
    raise HTTPException(status_code=404, detail=f"Cost forecast {forecast_id} not found")


@router.post("/cost-forecasts/", response_model=CostForecastResponse, status_code=201)
async def create_cost_forecast(forecast: CostForecastCreate):
    global _next_forecast_id
    new = {"id": _next_forecast_id, **forecast.model_dump(), "created_at": datetime.utcnow().isoformat()}
    _cost_forecasts_db.append(new)
    _next_forecast_id += 1
    return new


@router.put("/cost-forecasts/{forecast_id}", response_model=CostForecastResponse)
async def update_cost_forecast(forecast_id: int, forecast: CostForecastUpdate):
    for i, existing in enumerate(_cost_forecasts_db):
        if existing["id"] == forecast_id:
            _cost_forecasts_db[i] = {**existing, **forecast.model_dump(exclude_unset=True)}
            return _cost_forecasts_db[i]
    raise HTTPException(status_code=404, detail=f"Cost forecast {forecast_id} not found")


@router.delete("/cost-forecasts/{forecast_id}", status_code=204)
async def delete_cost_forecast(forecast_id: int):
    for i, f in enumerate(_cost_forecasts_db):
        if f["id"] == forecast_id:
            _cost_forecasts_db.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Cost forecast {forecast_id} not found")


# ─── Cost Variance Endpoints ────────────────────────────────────────────────

@router.get("/cost-variances/", response_model=List[CostVarianceResponse])
async def list_cost_variances(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    cost_center_id: Optional[int] = None,
    status: Optional[str] = None,
):
    results = _cost_variances_db
    if cost_center_id:
        results = [v for v in results if v["cost_center_id"] == cost_center_id]
    if status:
        results = [v for v in results if v["status"] == status]
    return results[skip : skip + limit]


@router.get("/cost-variances/{variance_id}", response_model=CostVarianceResponse)
async def get_cost_variance(variance_id: int):
    for v in _cost_variances_db:
        if v["id"] == variance_id:
            return v
    raise HTTPException(status_code=404, detail=f"Cost variance {variance_id} not found")


@router.post("/cost-variances/", response_model=CostVarianceResponse, status_code=201)
async def create_cost_variance(variance: CostVarianceCreate):
    global _next_variance_id
    new = {"id": _next_variance_id, **variance.model_dump(), "created_at": datetime.utcnow().isoformat()}
    _cost_variances_db.append(new)
    _next_variance_id += 1
    return new


@router.put("/cost-variances/{variance_id}", response_model=CostVarianceResponse)
async def update_cost_variance(variance_id: int, variance: CostVarianceUpdate):
    for i, existing in enumerate(_cost_variances_db):
        if existing["id"] == variance_id:
            _cost_variances_db[i] = {**existing, **variance.model_dump(exclude_unset=True)}
            return _cost_variances_db[i]
    raise HTTPException(status_code=404, detail=f"Cost variance {variance_id} not found")


@router.delete("/cost-variances/{variance_id}", status_code=204)
async def delete_cost_variance(variance_id: int):
    for i, v in enumerate(_cost_variances_db):
        if v["id"] == variance_id:
            _cost_variances_db.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Cost variance {variance_id} not found")
