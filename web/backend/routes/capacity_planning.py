"""Capacity Planning module CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/capacity-planning", tags=["capacity-planning"])

# ─── In-memory data stores ──────────────────────────────────────────────────

_capacity_plans_db = [
    {"id": 1, "name": "Q4 2026 Capacity Plan", "status": "active", "start_date": "2026-10-01", "end_date": "2026-12-31",
     "total_budget": 2500000.00, "currency": "USD", "notes": "Q4 peak season planning", "created_at": "2026-09-15T00:00:00"},
    {"id": 2, "name": "FY2027 Annual Plan", "status": "draft", "start_date": "2027-01-01", "end_date": "2027-12-31",
     "total_budget": 8000000.00, "currency": "USD", "notes": "Annual infrastructure growth", "created_at": "2026-09-20T00:00:00"},
]
_resource_allocations_db = [
    {"id": 1, "plan_id": 1, "resource_type": "compute", "resource_name": "AWS EC2 Cluster", "allocated_units": 500,
     "utilized_units": 380, "unit": "instances", "cost_per_unit": 120.00, "created_at": "2026-09-15T00:00:00"},
    {"id": 2, "plan_id": 1, "resource_type": "storage", "resource_name": "S3 Storage", "allocated_units": 2000,
     "utilized_units": 1450, "unit": "GB", "cost_per_unit": 0.023, "created_at": "2026-09-15T00:00:00"},
    {"id": 3, "plan_id": 1, "resource_type": "personnel", "resource_name": "Engineering Team", "allocated_units": 25,
     "utilized_units": 22, "unit": "FTE", "cost_per_unit": 15000.00, "created_at": "2026-09-15T00:00:00"},
    {"id": 4, "plan_id": 2, "resource_type": "compute", "resource_name": "GCP Cluster", "allocated_units": 800,
     "utilized_units": 0, "unit": "instances", "cost_per_unit": 110.00, "created_at": "2026-09-20T00:00:00"},
]
_forecasts_db = [
    {"id": 1, "plan_id": 1, "metric": "cpu_utilization", "period": "2026-Q4", "forecast_value": 72.5,
     "confidence_lower": 65.0, "confidence_upper": 80.0, "model": "ARIMA", "created_at": "2026-09-15T00:00:00"},
    {"id": 2, "plan_id": 1, "metric": "memory_utilization", "period": "2026-Q4", "forecast_value": 68.0,
     "confidence_lower": 60.0, "confidence_upper": 76.0, "model": "ARIMA", "created_at": "2026-09-15T00:00:00"},
    {"id": 3, "plan_id": 1, "metric": "storage_growth", "period": "2026-Q4", "forecast_value": 35.0,
     "confidence_lower": 28.0, "confidence_upper": 42.0, "model": "Prophet", "created_at": "2026-09-15T00:00:00"},
    {"id": 4, "plan_id": 2, "metric": "cpu_utilization", "period": "2027-Q1", "forecast_value": 55.0,
     "confidence_lower": 48.0, "confidence_upper": 62.0, "model": "ARIMA", "created_at": "2026-09-20T00:00:00"},
]
_scenarios_db = [
    {"id": 1, "plan_id": 1, "name": "High Growth", "description": "20% traffic increase scenario",
     "assumptions": "Marketing campaign drives 20% more users", "probability": 0.3, "impact": "high",
     "created_at": "2026-09-15T00:00:00"},
    {"id": 2, "plan_id": 1, "name": "Moderate Growth", "description": "10% traffic increase scenario",
     "assumptions": "Steady organic growth", "probability": 0.5, "impact": "medium",
     "created_at": "2026-09-15T00:00:00"},
    {"id": 3, "plan_id": 1, "name": "Low Growth", "description": "Flat traffic scenario",
     "assumptions": "Market conditions remain stable", "probability": 0.2, "impact": "low",
     "created_at": "2026-09-15T00:00:00"},
]

_next_plan_id = 3
_next_alloc_id = 5
_next_forecast_id = 5
_next_scenario_id = 4


# ─── Pydantic Models ────────────────────────────────────────────────────────

class CapacityPlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    status: str = Field("draft", pattern="^(draft|active|archived)$")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_budget: float = Field(0.0, ge=0)
    currency: str = "USD"
    notes: Optional[str] = None


class CapacityPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[str] = Field(None, pattern="^(draft|active|archived)$")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_budget: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = None
    notes: Optional[str] = None


class CapacityPlanResponse(BaseModel):
    id: int
    name: str
    status: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_budget: float
    currency: str
    notes: Optional[str] = None
    created_at: str


class ResourceAllocationCreate(BaseModel):
    plan_id: int
    resource_type: str = Field(..., min_length=1, max_length=50)
    resource_name: str = Field(..., min_length=1, max_length=200)
    allocated_units: float = Field(0.0, ge=0)
    utilized_units: float = Field(0.0, ge=0)
    unit: Optional[str] = None
    cost_per_unit: float = Field(0.0, ge=0)


class ResourceAllocationUpdate(BaseModel):
    plan_id: Optional[int] = None
    resource_type: Optional[str] = Field(None, min_length=1, max_length=50)
    resource_name: Optional[str] = Field(None, min_length=1, max_length=200)
    allocated_units: Optional[float] = Field(None, ge=0)
    utilized_units: Optional[float] = Field(None, ge=0)
    unit: Optional[str] = None
    cost_per_unit: Optional[float] = Field(None, ge=0)


class ResourceAllocationResponse(BaseModel):
    id: int
    plan_id: int
    resource_type: str
    resource_name: str
    allocated_units: float
    utilized_units: float
    unit: Optional[str] = None
    cost_per_unit: float
    created_at: str


class ForecastCreate(BaseModel):
    plan_id: int
    metric: str = Field(..., min_length=1, max_length=100)
    period: str = Field(..., min_length=1, max_length=20)
    forecast_value: float
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None
    model: Optional[str] = None


class ForecastUpdate(BaseModel):
    plan_id: Optional[int] = None
    metric: Optional[str] = Field(None, min_length=1, max_length=100)
    period: Optional[str] = Field(None, min_length=1, max_length=20)
    forecast_value: Optional[float] = None
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None
    model: Optional[str] = None


class ForecastResponse(BaseModel):
    id: int
    plan_id: int
    metric: str
    period: str
    forecast_value: float
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None
    model: Optional[str] = None
    created_at: str


class ScenarioCreate(BaseModel):
    plan_id: int
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    assumptions: Optional[str] = None
    probability: float = Field(0.5, ge=0, le=1)
    impact: str = Field("medium", pattern="^(low|medium|high|critical)$")


class ScenarioUpdate(BaseModel):
    plan_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    assumptions: Optional[str] = None
    probability: Optional[float] = Field(None, ge=0, le=1)
    impact: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")


class ScenarioResponse(BaseModel):
    id: int
    plan_id: int
    name: str
    description: Optional[str] = None
    assumptions: Optional[str] = None
    probability: float
    impact: str
    created_at: str


# ─── Capacity Plan Endpoints ────────────────────────────────────────────────

@router.get("/capacity-plans/", response_model=List[CapacityPlanResponse])
async def list_capacity_plans(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
):
    results = _capacity_plans_db
    if status:
        results = [p for p in results if p["status"] == status]
    return results[skip : skip + limit]


@router.get("/capacity-plans/{plan_id}", response_model=CapacityPlanResponse)
async def get_capacity_plan(plan_id: int):
    for p in _capacity_plans_db:
        if p["id"] == plan_id:
            return p
    raise HTTPException(status_code=404, detail=f"Capacity plan {plan_id} not found")


@router.post("/capacity-plans/", response_model=CapacityPlanResponse, status_code=201)
async def create_capacity_plan(plan: CapacityPlanCreate):
    global _next_plan_id
    new = {"id": _next_plan_id, **plan.model_dump(), "created_at": datetime.utcnow().isoformat()}
    _capacity_plans_db.append(new)
    _next_plan_id += 1
    return new


@router.put("/capacity-plans/{plan_id}", response_model=CapacityPlanResponse)
async def update_capacity_plan(plan_id: int, plan: CapacityPlanUpdate):
    for i, existing in enumerate(_capacity_plans_db):
        if existing["id"] == plan_id:
            _capacity_plans_db[i] = {**existing, **plan.model_dump(exclude_unset=True)}
            return _capacity_plans_db[i]
    raise HTTPException(status_code=404, detail=f"Capacity plan {plan_id} not found")


@router.delete("/capacity-plans/{plan_id}", status_code=204)
async def delete_capacity_plan(plan_id: int):
    for i, p in enumerate(_capacity_plans_db):
        if p["id"] == plan_id:
            _capacity_plans_db.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Capacity plan {plan_id} not found")


# ─── Resource Allocation Endpoints ──────────────────────────────────────────

@router.get("/resource-allocations/", response_model=List[ResourceAllocationResponse])
async def list_resource_allocations(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    plan_id: Optional[int] = None,
    resource_type: Optional[str] = None,
):
    results = _resource_allocations_db
    if plan_id:
        results = [a for a in results if a["plan_id"] == plan_id]
    if resource_type:
        results = [a for a in results if a["resource_type"] == resource_type]
    return results[skip : skip + limit]


@router.get("/resource-allocations/{alloc_id}", response_model=ResourceAllocationResponse)
async def get_resource_allocation(alloc_id: int):
    for a in _resource_allocations_db:
        if a["id"] == alloc_id:
            return a
    raise HTTPException(status_code=404, detail=f"Resource allocation {alloc_id} not found")


@router.post("/resource-allocations/", response_model=ResourceAllocationResponse, status_code=201)
async def create_resource_allocation(alloc: ResourceAllocationCreate):
    global _next_alloc_id
    new = {"id": _next_alloc_id, **alloc.model_dump(), "created_at": datetime.utcnow().isoformat()}
    _resource_allocations_db.append(new)
    _next_alloc_id += 1
    return new


@router.put("/resource-allocations/{alloc_id}", response_model=ResourceAllocationResponse)
async def update_resource_allocation(alloc_id: int, alloc: ResourceAllocationUpdate):
    for i, existing in enumerate(_resource_allocations_db):
        if existing["id"] == alloc_id:
            _resource_allocations_db[i] = {**existing, **alloc.model_dump(exclude_unset=True)}
            return _resource_allocations_db[i]
    raise HTTPException(status_code=404, detail=f"Resource allocation {alloc_id} not found")


@router.delete("/resource-allocations/{alloc_id}", status_code=204)
async def delete_resource_allocation(alloc_id: int):
    for i, a in enumerate(_resource_allocations_db):
        if a["id"] == alloc_id:
            _resource_allocations_db.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Resource allocation {alloc_id} not found")


# ─── Forecast Endpoints ─────────────────────────────────────────────────────

@router.get("/forecasts/", response_model=List[ForecastResponse])
async def list_forecasts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    plan_id: Optional[int] = None,
    metric: Optional[str] = None,
):
    results = _forecasts_db
    if plan_id:
        results = [f for f in results if f["plan_id"] == plan_id]
    if metric:
        results = [f for f in results if f["metric"] == metric]
    return results[skip : skip + limit]


@router.get("/forecasts/{forecast_id}", response_model=ForecastResponse)
async def get_forecast(forecast_id: int):
    for f in _forecasts_db:
        if f["id"] == forecast_id:
            return f
    raise HTTPException(status_code=404, detail=f"Forecast {forecast_id} not found")


@router.post("/forecasts/", response_model=ForecastResponse, status_code=201)
async def create_forecast(forecast: ForecastCreate):
    global _next_forecast_id
    new = {"id": _next_forecast_id, **forecast.model_dump(), "created_at": datetime.utcnow().isoformat()}
    _forecasts_db.append(new)
    _next_forecast_id += 1
    return new


@router.put("/forecasts/{forecast_id}", response_model=ForecastResponse)
async def update_forecast(forecast_id: int, forecast: ForecastUpdate):
    for i, existing in enumerate(_forecasts_db):
        if existing["id"] == forecast_id:
            _forecasts_db[i] = {**existing, **forecast.model_dump(exclude_unset=True)}
            return _forecasts_db[i]
    raise HTTPException(status_code=404, detail=f"Forecast {forecast_id} not found")


@router.delete("/forecasts/{forecast_id}", status_code=204)
async def delete_forecast(forecast_id: int):
    for i, f in enumerate(_forecasts_db):
        if f["id"] == forecast_id:
            _forecasts_db.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Forecast {forecast_id} not found")


# ─── Scenario Endpoints ─────────────────────────────────────────────────────

@router.get("/scenarios/", response_model=List[ScenarioResponse])
async def list_scenarios(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    plan_id: Optional[int] = None,
    impact: Optional[str] = None,
):
    results = _scenarios_db
    if plan_id:
        results = [s for s in results if s["plan_id"] == plan_id]
    if impact:
        results = [s for s in results if s["impact"] == impact]
    return results[skip : skip + limit]


@router.get("/scenarios/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(scenario_id: int):
    for s in _scenarios_db:
        if s["id"] == scenario_id:
            return s
    raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")


@router.post("/scenarios/", response_model=ScenarioResponse, status_code=201)
async def create_scenario(scenario: ScenarioCreate):
    global _next_scenario_id
    new = {"id": _next_scenario_id, **scenario.model_dump(), "created_at": datetime.utcnow().isoformat()}
    _scenarios_db.append(new)
    _next_scenario_id += 1
    return new


@router.put("/scenarios/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(scenario_id: int, scenario: ScenarioUpdate):
    for i, existing in enumerate(_scenarios_db):
        if existing["id"] == scenario_id:
            _scenarios_db[i] = {**existing, **scenario.model_dump(exclude_unset=True)}
            return _scenarios_db[i]
    raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")


@router.delete("/scenarios/{scenario_id}", status_code=204)
async def delete_scenario(scenario_id: int):
    for i, s in enumerate(_scenarios_db):
        if s["id"] == scenario_id:
            _scenarios_db.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")
