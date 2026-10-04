"""Manufacturing CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/manufacturing", tags=["manufacturing"])


# ─── Pydantic Models ─────────────────────────────────────────────────────────

class ProductionLineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=50)
    status: str = Field("active", pattern="^(active|inactive|maintenance)$")
    capacity_per_hour: float = Field(..., gt=0)
    location: Optional[str] = None
    supervisor: Optional[str] = None


class ProductionLineUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    status: Optional[str] = Field(None, pattern="^(active|inactive|maintenance)$")
    capacity_per_hour: Optional[float] = Field(None, gt=0)
    location: Optional[str] = None
    supervisor: Optional[str] = None


class ProductionLine(BaseModel):
    id: int
    name: str
    code: str
    status: str
    capacity_per_hour: float
    location: Optional[str] = None
    supervisor: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WorkOrderCreate(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)
    quantity: int = Field(..., gt=0)
    production_line_id: int
    priority: str = Field("normal", pattern="^(low|normal|high|urgent)$")
    status: str = Field("pending", pattern="^(pending|in_progress|completed|cancelled)$")
    due_date: Optional[datetime] = None
    notes: Optional[str] = None


class WorkOrderUpdate(BaseModel):
    product_name: Optional[str] = Field(None, min_length=1, max_length=200)
    quantity: Optional[int] = Field(None, gt=0)
    production_line_id: Optional[int] = None
    priority: Optional[str] = Field(None, pattern="^(low|normal|high|urgent)$")
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|cancelled)$")
    due_date: Optional[datetime] = None
    notes: Optional[str] = None


class WorkOrder(BaseModel):
    id: int
    product_name: str
    quantity: int
    production_line_id: int
    priority: str
    status: str
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class QualityCheckCreate(BaseModel):
    work_order_id: int
    inspector: str = Field(..., min_length=1, max_length=200)
    result: str = Field(..., pattern="^(pass|fail|pending)$")
    defect_count: int = Field(0, ge=0)
    notes: Optional[str] = None


class QualityCheckUpdate(BaseModel):
    inspector: Optional[str] = Field(None, min_length=1, max_length=200)
    result: Optional[str] = Field(None, pattern="^(pass|fail|pending)$")
    defect_count: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class QualityCheck(BaseModel):
    id: int
    work_order_id: int
    inspector: str
    result: str
    defect_count: int
    notes: Optional[str] = None
    checked_at: datetime


class BOMItem(BaseModel):
    material_name: str = Field(..., min_length=1, max_length=200)
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1, max_length=20)


class BillOfMaterialsCreate(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)
    version: str = Field("1.0", min_length=1, max_length=20)
    items: List[BOMItem] = Field(..., min_length=1)
    notes: Optional[str] = None


class BillOfMaterialsUpdate(BaseModel):
    product_name: Optional[str] = Field(None, min_length=1, max_length=200)
    version: Optional[str] = Field(None, min_length=1, max_length=20)
    items: Optional[List[BOMItem]] = None
    notes: Optional[str] = None


class BillOfMaterials(BaseModel):
    id: int
    product_name: str
    version: str
    items: List[BOMItem]
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ─── In-Memory Data Stores ───────────────────────────────────────────────────

_production_lines_db: dict[int, dict] = {
    1: {"id": 1, "name": "Assembly Line A", "code": "ASM-A", "status": "active",
        "capacity_per_hour": 120, "location": "Building 1, Floor 2", "supervisor": "John Smith",
        "created_at": datetime(2024, 1, 1), "updated_at": datetime(2024, 1, 1)},
    2: {"id": 2, "name": "Assembly Line B", "code": "ASM-B", "status": "active",
        "capacity_per_hour": 95, "location": "Building 1, Floor 3", "supervisor": "Jane Doe",
        "created_at": datetime(2024, 1, 2), "updated_at": datetime(2024, 1, 2)},
    3: {"id": 3, "name": "Packaging Line", "code": "PKG-1", "status": "maintenance",
        "capacity_per_hour": 200, "location": "Building 2, Floor 1", "supervisor": "Bob Wilson",
        "created_at": datetime(2024, 1, 3), "updated_at": datetime(2024, 1, 3)},
    4: {"id": 4, "name": "CNC Machining", "code": "CNC-1", "status": "active",
        "capacity_per_hour": 45, "location": "Building 3, Floor 1", "supervisor": "Alice Brown",
        "created_at": datetime(2024, 1, 4), "updated_at": datetime(2024, 1, 4)},
    5: {"id": 5, "name": "Quality Control", "code": "QC-1", "status": "active",
        "capacity_per_hour": 300, "location": "Building 1, Floor 1", "supervisor": "Charlie Davis",
        "created_at": datetime(2024, 1, 5), "updated_at": datetime(2024, 1, 5)},
}

_work_orders_db: dict[int, dict] = {
    1: {"id": 1, "product_name": "Widget X200", "quantity": 500, "production_line_id": 1,
        "priority": "high", "status": "in_progress", "due_date": datetime(2024, 2, 15),
        "notes": "Rush order for client ABC", "created_at": datetime(2024, 1, 10), "updated_at": datetime(2024, 1, 10)},
    2: {"id": 2, "product_name": "Gadget Y500", "quantity": 250, "production_line_id": 2,
        "priority": "normal", "status": "pending", "due_date": datetime(2024, 2, 20),
        "notes": None, "created_at": datetime(2024, 1, 12), "updated_at": datetime(2024, 1, 12)},
    3: {"id": 3, "product_name": "Component Z100", "quantity": 1000, "production_line_id": 4,
        "priority": "urgent", "status": "in_progress", "due_date": datetime(2024, 2, 10),
        "notes": "Critical shortage", "created_at": datetime(2024, 1, 15), "updated_at": datetime(2024, 1, 15)},
    4: {"id": 4, "product_name": "Widget X200", "quantity": 300, "production_line_id": 1,
        "priority": "low", "status": "completed", "due_date": datetime(2024, 2, 5),
        "notes": None, "created_at": datetime(2024, 1, 5), "updated_at": datetime(2024, 1, 5)},
    5: {"id": 5, "product_name": "Gadget Y500", "quantity": 150, "production_line_id": 3,
        "priority": "normal", "status": "pending", "due_date": datetime(2024, 2, 25),
        "notes": "Standard production run", "created_at": datetime(2024, 1, 18), "updated_at": datetime(2024, 1, 18)},
}

_quality_checks_db: dict[int, dict] = {
    1: {"id": 1, "work_order_id": 1, "inspector": "Mike Johnson", "result": "pass",
        "defect_count": 2, "notes": "Minor cosmetic defects within tolerance",
        "checked_at": datetime(2024, 1, 20)},
    2: {"id": 2, "work_order_id": 3, "inspector": "Sarah Lee", "result": "fail",
        "defect_count": 15, "notes": "Dimensional tolerance exceeded on 15 units",
        "checked_at": datetime(2024, 1, 22)},
    3: {"id": 3, "work_order_id": 4, "inspector": "Mike Johnson", "result": "pass",
        "defect_count": 0, "notes": "All units passed inspection",
        "checked_at": datetime(2024, 1, 25)},
    4: {"id": 4, "work_order_id": 2, "inspector": "Tom Chen", "result": "pending",
        "defect_count": 0, "notes": "Inspection scheduled",
        "checked_at": datetime(2024, 1, 28)},
}

_bills_of_materials_db: dict[int, dict] = {
    1: {"id": 1, "product_name": "Widget X200", "version": "1.0",
        "items": [
            {"material_name": "Steel Frame", "quantity": 1, "unit": "pcs"},
            {"material_name": "Electronic Board", "quantity": 1, "unit": "pcs"},
            {"material_name": "Plastic Casing", "quantity": 2, "unit": "pcs"},
            {"material_name": "Screws M4", "quantity": 8, "unit": "pcs"},
        ],
        "notes": "Standard configuration", "created_at": datetime(2024, 1, 1), "updated_at": datetime(2024, 1, 1)},
    2: {"id": 2, "product_name": "Gadget Y500", "version": "2.1",
        "items": [
            {"material_name": "Aluminum Body", "quantity": 1, "unit": "pcs"},
            {"material_name": "LCD Display", "quantity": 1, "unit": "pcs"},
            {"material_name": "Battery Pack", "quantity": 1, "unit": "pcs"},
            {"material_name": "Wiring Harness", "quantity": 1, "unit": "set"},
        ],
        "notes": "Revised for cost reduction", "created_at": datetime(2024, 1, 5), "updated_at": datetime(2024, 1, 5)},
    3: {"id": 3, "product_name": "Component Z100", "version": "1.0",
        "items": [
            {"material_name": "Copper Wire", "quantity": 0.5, "unit": "m"},
            {"material_name": "PCB Substrate", "quantity": 1, "unit": "pcs"},
            {"material_name": "Solder Paste", "quantity": 10, "unit": "g"},
        ],
        "notes": None, "created_at": datetime(2024, 1, 8), "updated_at": datetime(2024, 1, 8)},
}

_next_ids = {"production_line": 6, "work_order": 6, "quality_check": 5, "bill_of_materials": 4}


# ─── Production Lines CRUD ───────────────────────────────────────────────────

@router.get("/production-lines/", response_model=List[ProductionLine])
async def list_production_lines(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
):
    """List all production lines with pagination and optional status filter."""
    items = list(_production_lines_db.values())
    if status:
        items = [i for i in items if i.get("status") == status]
    return items[skip : skip + limit]


@router.get("/production-lines/{item_id}", response_model=ProductionLine)
async def get_production_line(item_id: int):
    """Get a single production line by ID."""
    if item_id not in _production_lines_db:
        raise HTTPException(status_code=404, detail=f"Production line {item_id} not found")
    return _production_lines_db[item_id]


@router.post("/production-lines/", response_model=ProductionLine, status_code=201)
async def create_production_line(item: ProductionLineCreate):
    """Create a new production line."""
    global _next_ids
    now = datetime.utcnow()
    new_item = {
        "id": _next_ids["production_line"],
        **item.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _production_lines_db[_next_ids["production_line"]] = new_item
    _next_ids["production_line"] += 1
    return new_item


@router.put("/production-lines/{item_id}", response_model=ProductionLine)
async def update_production_line(item_id: int, item: ProductionLineUpdate):
    """Update an existing production line."""
    if item_id not in _production_lines_db:
        raise HTTPException(status_code=404, detail=f"Production line {item_id} not found")
    stored = _production_lines_db[item_id]
    update_data = item.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        stored[field] = value
    stored["updated_at"] = datetime.utcnow()
    return stored


@router.delete("/production-lines/{item_id}", status_code=204)
async def delete_production_line(item_id: int):
    """Delete a production line."""
    if item_id not in _production_lines_db:
        raise HTTPException(status_code=404, detail=f"Production line {item_id} not found")
    del _production_lines_db[item_id]


# ─── Work Orders CRUD ────────────────────────────────────────────────────────

@router.get("/work-orders/", response_model=List[WorkOrder])
async def list_work_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    priority: Optional[str] = None,
):
    """List all work orders with pagination and optional filters."""
    items = list(_work_orders_db.values())
    if status:
        items = [i for i in items if i.get("status") == status]
    if priority:
        items = [i for i in items if i.get("priority") == priority]
    return items[skip : skip + limit]


@router.get("/work-orders/{item_id}", response_model=WorkOrder)
async def get_work_order(item_id: int):
    """Get a single work order by ID."""
    if item_id not in _work_orders_db:
        raise HTTPException(status_code=404, detail=f"Work order {item_id} not found")
    return _work_orders_db[item_id]


@router.post("/work-orders/", response_model=WorkOrder, status_code=201)
async def create_work_order(item: WorkOrderCreate):
    """Create a new work order."""
    global _next_ids
    now = datetime.utcnow()
    new_item = {
        "id": _next_ids["work_order"],
        **item.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _work_orders_db[_next_ids["work_order"]] = new_item
    _next_ids["work_order"] += 1
    return new_item


@router.put("/work-orders/{item_id}", response_model=WorkOrder)
async def update_work_order(item_id: int, item: WorkOrderUpdate):
    """Update an existing work order."""
    if item_id not in _work_orders_db:
        raise HTTPException(status_code=404, detail=f"Work order {item_id} not found")
    stored = _work_orders_db[item_id]
    update_data = item.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        stored[field] = value
    stored["updated_at"] = datetime.utcnow()
    return stored


@router.delete("/work-orders/{item_id}", status_code=204)
async def delete_work_order(item_id: int):
    """Delete a work order."""
    if item_id not in _work_orders_db:
        raise HTTPException(status_code=404, detail=f"Work order {item_id} not found")
    del _work_orders_db[item_id]


# ─── Quality Checks CRUD ─────────────────────────────────────────────────────

@router.get("/quality-checks/", response_model=List[QualityCheck])
async def list_quality_checks(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    result: Optional[str] = None,
):
    """List all quality checks with pagination and optional result filter."""
    items = list(_quality_checks_db.values())
    if result:
        items = [i for i in items if i.get("result") == result]
    return items[skip : skip + limit]


@router.get("/quality-checks/{item_id}", response_model=QualityCheck)
async def get_quality_check(item_id: int):
    """Get a single quality check by ID."""
    if item_id not in _quality_checks_db:
        raise HTTPException(status_code=404, detail=f"Quality check {item_id} not found")
    return _quality_checks_db[item_id]


@router.post("/quality-checks/", response_model=QualityCheck, status_code=201)
async def create_quality_check(item: QualityCheckCreate):
    """Create a new quality check."""
    global _next_ids
    now = datetime.utcnow()
    new_item = {
        "id": _next_ids["quality_check"],
        **item.model_dump(),
        "checked_at": now,
    }
    _quality_checks_db[_next_ids["quality_check"]] = new_item
    _next_ids["quality_check"] += 1
    return new_item


@router.put("/quality-checks/{item_id}", response_model=QualityCheck)
async def update_quality_check(item_id: int, item: QualityCheckUpdate):
    """Update an existing quality check."""
    if item_id not in _quality_checks_db:
        raise HTTPException(status_code=404, detail=f"Quality check {item_id} not found")
    stored = _quality_checks_db[item_id]
    update_data = item.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        stored[field] = value
    return stored


@router.delete("/quality-checks/{item_id}", status_code=204)
async def delete_quality_check(item_id: int):
    """Delete a quality check."""
    if item_id not in _quality_checks_db:
        raise HTTPException(status_code=404, detail=f"Quality check {item_id} not found")
    del _quality_checks_db[item_id]


# ─── Bills of Materials CRUD ─────────────────────────────────────────────────

@router.get("/bills-of-materials/", response_model=List[BillOfMaterials])
async def list_bills_of_materials(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List all bills of materials with pagination."""
    items = list(_bills_of_materials_db.values())
    return items[skip : skip + limit]


@router.get("/bills-of-materials/{item_id}", response_model=BillOfMaterials)
async def get_bill_of_materials(item_id: int):
    """Get a single bill of materials by ID."""
    if item_id not in _bills_of_materials_db:
        raise HTTPException(status_code=404, detail=f"Bill of materials {item_id} not found")
    return _bills_of_materials_db[item_id]


@router.post("/bills-of-materials/", response_model=BillOfMaterials, status_code=201)
async def create_bill_of_materials(item: BillOfMaterialsCreate):
    """Create a new bill of materials."""
    global _next_ids
    now = datetime.utcnow()
    new_item = {
        "id": _next_ids["bill_of_materials"],
        **item.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _bills_of_materials_db[_next_ids["bill_of_materials"]] = new_item
    _next_ids["bill_of_materials"] += 1
    return new_item


@router.put("/bills-of-materials/{item_id}", response_model=BillOfMaterials)
async def update_bill_of_materials(item_id: int, item: BillOfMaterialsUpdate):
    """Update an existing bill of materials."""
    if item_id not in _bills_of_materials_db:
        raise HTTPException(status_code=404, detail=f"Bill of materials {item_id} not found")
    stored = _bills_of_materials_db[item_id]
    update_data = item.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        stored[field] = value
    stored["updated_at"] = datetime.utcnow()
    return stored


@router.delete("/bills-of-materials/{item_id}", status_code=204)
async def delete_bill_of_materials(item_id: int):
    """Delete a bill of materials."""
    if item_id not in _bills_of_materials_db:
        raise HTTPException(status_code=404, detail=f"Bill of materials {item_id} not found")
    del _bills_of_materials_db[item_id]
