"""Inventory CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


class InventoryItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    sku: str = Field(..., min_length=1, max_length=50)
    quantity: int = Field(..., ge=0)
    price: float = Field(..., ge=0)
    category: Optional[str] = None
    description: Optional[str] = None


class InventoryItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    sku: Optional[str] = Field(None, min_length=1, max_length=50)
    quantity: Optional[int] = Field(None, ge=0)
    price: Optional[float] = Field(None, ge=0)
    category: Optional[str] = None
    description: Optional[str] = None


class InventoryItem(BaseModel):
    id: int
    name: str
    sku: str
    quantity: int
    price: float
    category: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Synthetic in-memory data store
_inventory_db: dict[int, dict] = {
    1: {"id": 1, "name": "Widget A", "sku": "WID-001", "quantity": 150, "price": 9.99,
        "category": "widgets", "description": "Standard widget",
        "created_at": datetime(2024, 1, 1), "updated_at": datetime(2024, 1, 1)},
    2: {"id": 2, "name": "Gadget B", "sku": "GAD-002", "quantity": 75, "price": 24.50,
        "category": "gadgets", "description": "Premium gadget",
        "created_at": datetime(2024, 1, 2), "updated_at": datetime(2024, 1, 2)},
    3: {"id": 3, "name": "Component C", "sku": "COM-003", "quantity": 300, "price": 3.75,
        "category": "components", "description": "Raw component",
        "created_at": datetime(2024, 1, 3), "updated_at": datetime(2024, 1, 3)},
    4: {"id": 4, "name": "Tool D", "sku": "TOL-004", "quantity": 42, "price": 89.00,
        "category": "tools", "description": "Professional tool",
        "created_at": datetime(2024, 1, 4), "updated_at": datetime(2024, 1, 4)},
    5: {"id": 5, "name": "Part E", "sku": "PRT-005", "quantity": 500, "price": 1.25,
        "category": "parts", "description": "Replacement part",
        "created_at": datetime(2024, 1, 5), "updated_at": datetime(2024, 1, 5)},
}
_next_id = 6


@router.get("/", response_model=List[InventoryItem])
async def list_inventory(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
):
    """List all inventory items with pagination and optional category filter."""
    items = list(_inventory_db.values())
    if category:
        items = [i for i in items if i.get("category") == category]
    return items[skip : skip + limit]


@router.get("/{item_id}", response_model=InventoryItem)
async def get_inventory_item(item_id: int):
    """Get a single inventory item by ID."""
    if item_id not in _inventory_db:
        raise HTTPException(status_code=404, detail=f"Inventory item {item_id} not found")
    return _inventory_db[item_id]


@router.post("", response_model=InventoryItem, status_code=201)
async def create_inventory_item(item: InventoryItemCreate):
    """Create a new inventory item."""
    global _next_id
    now = datetime.utcnow()
    new_item = {
        "id": _next_id,
        **item.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _inventory_db[_next_id] = new_item
    _next_id += 1
    return new_item


@router.put("/{item_id}", response_model=InventoryItem)
async def update_inventory_item(item_id: int, item: InventoryItemUpdate):
    """Update an existing inventory item."""
    if item_id not in _inventory_db:
        raise HTTPException(status_code=404, detail=f"Inventory item {item_id} not found")
    stored = _inventory_db[item_id]
    update_data = item.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        stored[field] = value
    stored["updated_at"] = datetime.utcnow()
    return stored


@router.delete("/{item_id}", status_code=204)
async def delete_inventory_item(item_id: int):
    """Delete an inventory item."""
    if item_id not in _inventory_db:
        raise HTTPException(status_code=404, detail=f"Inventory item {item_id} not found")
    del _inventory_db[item_id]
