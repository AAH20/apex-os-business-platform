"""Asset Management CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date

router = APIRouter(prefix="/api/assets", tags=["assets"])


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class AssetCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    depreciation_method: str = "straight_line"
    useful_life_years: int = Field(..., ge=1, le=100)


class AssetCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    depreciation_method: Optional[str] = None
    useful_life_years: Optional[int] = Field(None, ge=1, le=100)


class AssetCategory(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    depreciation_method: str
    useful_life_years: int
    created_at: datetime
    updated_at: datetime


class AssetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    asset_tag: str = Field(..., min_length=1, max_length=50)
    category_id: int
    purchase_date: date
    purchase_cost: float = Field(..., ge=0)
    salvage_value: float = Field(0, ge=0)
    status: str = "active"
    location: Optional[str] = None
    description: Optional[str] = None


class AssetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    asset_tag: Optional[str] = Field(None, min_length=1, max_length=50)
    category_id: Optional[int] = None
    purchase_date: Optional[date] = None
    purchase_cost: Optional[float] = Field(None, ge=0)
    salvage_value: Optional[float] = Field(None, ge=0)
    status: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None


class Asset(BaseModel):
    id: int
    name: str
    asset_tag: str
    category_id: int
    purchase_date: date
    purchase_cost: float
    salvage_value: float
    status: str
    location: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MaintenanceScheduleCreate(BaseModel):
    asset_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    frequency: str = "monthly"
    next_due_date: date
    assigned_to: Optional[str] = None
    estimated_cost: float = Field(0, ge=0)
    status: str = "scheduled"


class MaintenanceScheduleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    frequency: Optional[str] = None
    next_due_date: Optional[date] = None
    assigned_to: Optional[str] = None
    estimated_cost: Optional[float] = Field(None, ge=0)
    status: Optional[str] = None


class MaintenanceSchedule(BaseModel):
    id: int
    asset_id: int
    title: str
    description: Optional[str] = None
    frequency: str
    next_due_date: date
    assigned_to: Optional[str] = None
    estimated_cost: float
    status: str
    created_at: datetime
    updated_at: datetime


class DepreciationRecordCreate(BaseModel):
    asset_id: int
    period_start: date
    period_end: date
    depreciation_amount: float = Field(..., ge=0)
    accumulated_depreciation: float = Field(..., ge=0)
    book_value: float = Field(..., ge=0)


class DepreciationRecordUpdate(BaseModel):
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    depreciation_amount: Optional[float] = Field(None, ge=0)
    accumulated_depreciation: Optional[float] = Field(None, ge=0)
    book_value: Optional[float] = Field(None, ge=0)


class DepreciationRecord(BaseModel):
    id: int
    asset_id: int
    period_start: date
    period_end: date
    depreciation_amount: float
    accumulated_depreciation: float
    book_value: float
    created_at: datetime


# ─── In-Memory Data Stores ────────────────────────────────────────────────────

_categories_db: dict[int, dict] = {
    1: {"id": 1, "name": "IT Equipment", "description": "Computers, servers, networking",
        "depreciation_method": "straight_line", "useful_life_years": 5,
        "created_at": datetime(2024, 1, 1), "updated_at": datetime(2024, 1, 1)},
    2: {"id": 2, "name": "Furniture", "description": "Office furniture and fixtures",
        "depreciation_method": "straight_line", "useful_life_years": 7,
        "created_at": datetime(2024, 1, 2), "updated_at": datetime(2024, 1, 2)},
    3: {"id": 3, "name": "Vehicles", "description": "Company vehicles",
        "depreciation_method": "declining_balance", "useful_life_years": 5,
        "created_at": datetime(2024, 1, 3), "updated_at": datetime(2024, 1, 3)},
    4: {"id": 4, "name": "Machinery", "description": "Manufacturing equipment",
        "depreciation_method": "units_of_production", "useful_life_years": 10,
        "created_at": datetime(2024, 1, 4), "updated_at": datetime(2024, 1, 4)},
}

_assets_db: dict[int, dict] = {
    1: {"id": 1, "name": "Dell PowerEdge R740", "asset_tag": "SRV-001", "category_id": 1,
        "purchase_date": date(2023, 6, 15), "purchase_cost": 8500.00, "salvage_value": 500.00,
        "status": "active", "location": "Data Center A", "description": "Primary application server",
        "created_at": datetime(2023, 6, 15), "updated_at": datetime(2023, 6, 15)},
    2: {"id": 2, "name": "MacBook Pro 16\"", "asset_tag": "LAP-001", "category_id": 1,
        "purchase_date": date(2024, 1, 10), "purchase_cost": 2499.00, "salvage_value": 200.00,
        "status": "active", "location": "Office 3F", "description": "Developer laptop",
        "created_at": datetime(2024, 1, 10), "updated_at": datetime(2024, 1, 10)},
    3: {"id": 3, "name": "Herman Miller Aeron", "asset_tag": "FUR-001", "category_id": 2,
        "purchase_date": date(2023, 3, 20), "purchase_cost": 1395.00, "salvage_value": 100.00,
        "status": "active", "location": "Office 2F", "description": "Ergonomic office chair",
        "created_at": datetime(2023, 3, 20), "updated_at": datetime(2023, 3, 20)},
    4: {"id": 4, "name": "Toyota Hilux", "asset_tag": "VEH-001", "category_id": 3,
        "purchase_date": date(2022, 8, 5), "purchase_cost": 35000.00, "salvage_value": 5000.00,
        "status": "maintenance", "location": "Warehouse B", "description": "Delivery vehicle",
        "created_at": datetime(2022, 8, 5), "updated_at": datetime(2022, 8, 5)},
    5: {"id": 5, "name": "CNC Milling Machine", "asset_tag": "MCH-001", "category_id": 4,
        "purchase_date": date(2021, 11, 12), "purchase_cost": 125000.00, "salvage_value": 10000.00,
        "status": "active", "location": "Factory Floor", "description": "Precision CNC mill",
        "created_at": datetime(2021, 11, 12), "updated_at": datetime(2021, 11, 12)},
}

_maintenance_db: dict[int, dict] = {
    1: {"id": 1, "asset_id": 1, "title": "Server firmware update", "description": "Update BIOS and firmware",
        "frequency": "quarterly", "next_due_date": date(2025, 1, 15), "assigned_to": "IT Team",
        "estimated_cost": 0, "status": "scheduled",
        "created_at": datetime(2024, 10, 15), "updated_at": datetime(2024, 10, 15)},
    2: {"id": 2, "asset_id": 4, "title": "Oil change and inspection", "description": "Routine vehicle maintenance",
        "frequency": "monthly", "next_due_date": date(2024, 11, 1), "assigned_to": "Fleet Manager",
        "estimated_cost": 150, "status": "scheduled",
        "created_at": datetime(2024, 10, 1), "updated_at": datetime(2024, 10, 1)},
    3: {"id": 3, "asset_id": 5, "title": "Calibration check", "description": "Verify CNC accuracy",
        "frequency": "weekly", "next_due_date": date(2024, 10, 20), "assigned_to": "Maintenance",
        "estimated_cost": 500, "status": "completed",
        "created_at": datetime(2024, 10, 6), "updated_at": datetime(2024, 10, 6)},
}

_depreciation_db: dict[int, dict] = {
    1: {"id": 1, "asset_id": 1, "period_start": date(2023, 6, 15), "period_end": date(2024, 6, 14),
        "depreciation_amount": 1600.00, "accumulated_depreciation": 1600.00, "book_value": 6900.00,
        "created_at": datetime(2024, 6, 14)},
    2: {"id": 2, "asset_id": 2, "period_start": date(2024, 1, 10), "period_end": date(2025, 1, 9),
        "depreciation_amount": 459.80, "accumulated_depreciation": 459.80, "book_value": 2039.20,
        "created_at": datetime(2025, 1, 9)},
    3: {"id": 3, "asset_id": 4, "period_start": date(2022, 8, 5), "period_end": date(2023, 8, 4),
        "depreciation_amount": 6000.00, "accumulated_depreciation": 6000.00, "book_value": 29000.00,
        "created_at": datetime(2023, 8, 4)},
}

_cat_next_id = 5
_asset_next_id = 6
_maint_next_id = 4
_dep_next_id = 4


# ─── Asset Categories CRUD ────────────────────────────────────────────────────

@router.get("/categories/", response_model=List[AssetCategory])
async def list_categories(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    items = list(_categories_db.values())
    return items[skip : skip + limit]


@router.get("/categories/{category_id}", response_model=AssetCategory)
async def get_category(category_id: int):
    if category_id not in _categories_db:
        raise HTTPException(status_code=404, detail=f"Category {category_id} not found")
    return _categories_db[category_id]


@router.post("/categories/", response_model=AssetCategory, status_code=201)
async def create_category(cat: AssetCategoryCreate):
    global _cat_next_id
    now = datetime.utcnow()
    new_item = {"id": _cat_next_id, **cat.model_dump(), "created_at": now, "updated_at": now}
    _categories_db[_cat_next_id] = new_item
    _cat_next_id += 1
    return new_item


@router.put("/categories/{category_id}", response_model=AssetCategory)
async def update_category(category_id: int, cat: AssetCategoryUpdate):
    if category_id not in _categories_db:
        raise HTTPException(status_code=404, detail=f"Category {category_id} not found")
    stored = _categories_db[category_id]
    for field, value in cat.model_dump(exclude_unset=True).items():
        stored[field] = value
    stored["updated_at"] = datetime.utcnow()
    return stored


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(category_id: int):
    if category_id not in _categories_db:
        raise HTTPException(status_code=404, detail=f"Category {category_id} not found")
    del _categories_db[category_id]


# ─── Maintenance Schedules CRUD (defined before /{asset_id} to avoid shadowing) ─

@router.get("/maintenance/", response_model=List[MaintenanceSchedule])
async def list_maintenance(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    asset_id: Optional[int] = None,
    status: Optional[str] = None,
):
    items = list(_maintenance_db.values())
    if asset_id:
        items = [i for i in items if i.get("asset_id") == asset_id]
    if status:
        items = [i for i in items if i.get("status") == status]
    return items[skip : skip + limit]


@router.get("/maintenance/{schedule_id}", response_model=MaintenanceSchedule)
async def get_maintenance(schedule_id: int):
    if schedule_id not in _maintenance_db:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    return _maintenance_db[schedule_id]


@router.post("/maintenance/", response_model=MaintenanceSchedule, status_code=201)
async def create_maintenance(schedule: MaintenanceScheduleCreate):
    global _maint_next_id
    now = datetime.utcnow()
    new_item = {"id": _maint_next_id, **schedule.model_dump(), "created_at": now, "updated_at": now}
    _maintenance_db[_maint_next_id] = new_item
    _maint_next_id += 1
    return new_item


@router.put("/maintenance/{schedule_id}", response_model=MaintenanceSchedule)
async def update_maintenance(schedule_id: int, schedule: MaintenanceScheduleUpdate):
    if schedule_id not in _maintenance_db:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    stored = _maintenance_db[schedule_id]
    for field, value in schedule.model_dump(exclude_unset=True).items():
        stored[field] = value
    stored["updated_at"] = datetime.utcnow()
    return stored


@router.delete("/maintenance/{schedule_id}", status_code=204)
async def delete_maintenance(schedule_id: int):
    if schedule_id not in _maintenance_db:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    del _maintenance_db[schedule_id]


# ─── Depreciation Records CRUD (defined before /{asset_id} to avoid shadowing) ──

@router.get("/depreciation/", response_model=List[DepreciationRecord])
async def list_depreciation(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    asset_id: Optional[int] = None,
):
    items = list(_depreciation_db.values())
    if asset_id:
        items = [i for i in items if i.get("asset_id") == asset_id]
    return items[skip : skip + limit]


@router.get("/depreciation/{record_id}", response_model=DepreciationRecord)
async def get_depreciation(record_id: int):
    if record_id not in _depreciation_db:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
    return _depreciation_db[record_id]


@router.post("/depreciation/", response_model=DepreciationRecord, status_code=201)
async def create_depreciation(record: DepreciationRecordCreate):
    global _dep_next_id
    new_item = {"id": _dep_next_id, **record.model_dump(), "created_at": datetime.utcnow()}
    _depreciation_db[_dep_next_id] = new_item
    _dep_next_id += 1
    return new_item


@router.put("/depreciation/{record_id}", response_model=DepreciationRecord)
async def update_depreciation(record_id: int, record: DepreciationRecordUpdate):
    if record_id not in _depreciation_db:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
    stored = _depreciation_db[record_id]
    for field, value in record.model_dump(exclude_unset=True).items():
        stored[field] = value
    return stored


@router.delete("/depreciation/{record_id}", status_code=204)
async def delete_depreciation(record_id: int):
    if record_id not in _depreciation_db:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
    del _depreciation_db[record_id]


# ─── Assets CRUD ───────────────────────────────────────────────────────────────

@router.get("/", response_model=List[Asset])
async def list_assets(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    status: Optional[str] = None,
):
    items = list(_assets_db.values())
    if category_id:
        items = [i for i in items if i.get("category_id") == category_id]
    if status:
        items = [i for i in items if i.get("status") == status]
    return items[skip : skip + limit]


@router.get("/{asset_id}", response_model=Asset)
async def get_asset(asset_id: int):
    if asset_id not in _assets_db:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
    return _assets_db[asset_id]


@router.post("/", response_model=Asset, status_code=201)
async def create_asset(asset: AssetCreate):
    global _asset_next_id
    now = datetime.utcnow()
    new_item = {"id": _asset_next_id, **asset.model_dump(), "created_at": now, "updated_at": now}
    _assets_db[_asset_next_id] = new_item
    _asset_next_id += 1
    return new_item


@router.put("/{asset_id}", response_model=Asset)
async def update_asset(asset_id: int, asset: AssetUpdate):
    if asset_id not in _assets_db:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
    stored = _assets_db[asset_id]
    for field, value in asset.model_dump(exclude_unset=True).items():
        stored[field] = value
    stored["updated_at"] = datetime.utcnow()
    return stored


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(asset_id: int):
    if asset_id not in _assets_db:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
    del _assets_db[asset_id]
