"""Order CRUD API endpoints for APEX-OS Business Platform."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/orders", tags=["orders"])


class OrderItem(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: float = Field(gt=0)


class OrderCreate(BaseModel):
    customer_id: int
    items: List[OrderItem]
    status: str = Field(default="pending", pattern="^(pending|processing|shipped|delivered|cancelled)$")
    notes: Optional[str] = None


class OrderUpdate(BaseModel):
    customer_id: Optional[int] = None
    items: Optional[List[OrderItem]] = None
    status: Optional[str] = Field(default=None, pattern="^(pending|processing|shipped|delivered|cancelled)$")
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    customer_id: int
    items: List[OrderItem]
    status: str
    total: float
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Synthetic in-memory data store
_orders: dict[int, dict] = {
    1: {"id": 1, "customer_id": 101, "items": [{"product_id": 1, "quantity": 2, "unit_price": 29.99}],
        "status": "delivered", "total": 59.98, "notes": None,
        "created_at": datetime(2026, 9, 1, 10, 0), "updated_at": datetime(2026, 9, 5, 14, 30)},
    2: {"id": 2, "customer_id": 102, "items": [{"product_id": 3, "quantity": 1, "unit_price": 149.50}],
        "status": "shipped", "total": 149.50, "notes": "Express delivery",
        "created_at": datetime(2026, 9, 10, 9, 15), "updated_at": datetime(2026, 9, 12, 11, 0)},
    3: {"id": 3, "customer_id": 103, "items": [{"product_id": 2, "quantity": 5, "unit_price": 12.00}],
        "status": "pending", "total": 60.00, "notes": None,
        "created_at": datetime(2026, 10, 1, 8, 45), "updated_at": datetime(2026, 10, 1, 8, 45)},
}
_next_id = 4


def _compute_total(items: List[OrderItem]) -> float:
    return round(sum(i.quantity * i.unit_price for i in items), 2)


@router.get("/", response_model=List[OrderResponse])
async def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    status_filter: Optional[str] = Query(default=None, alias="status"),
):
    """List all orders with pagination and optional status filter."""
    orders = list(_orders.values())
    if status_filter:
        orders = [o for o in orders if o["status"] == status_filter]
    start = (page - 1) * page_size
    return orders[start : start + page_size]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int):
    """Get a single order by ID."""
    if order_id not in _orders:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return _orders[order_id]


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(payload: OrderCreate):
    """Create a new order."""
    global _next_id
    now = datetime.utcnow()
    order = {
        "id": _next_id,
        "customer_id": payload.customer_id,
        "items": [i.model_dump() for i in payload.items],
        "status": payload.status,
        "total": _compute_total(payload.items),
        "notes": payload.notes,
        "created_at": now,
        "updated_at": now,
    }
    _orders[_next_id] = order
    _next_id += 1
    return order


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(order_id: int, payload: OrderUpdate):
    """Update an existing order."""
    if order_id not in _orders:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    order = _orders[order_id]
    if payload.customer_id is not None:
        order["customer_id"] = payload.customer_id
    if payload.items is not None:
        order["items"] = [i.model_dump() for i in payload.items]
        order["total"] = _compute_total(payload.items)
    if payload.status is not None:
        order["status"] = payload.status
    if payload.notes is not None:
        order["notes"] = payload.notes
    order["updated_at"] = datetime.utcnow()
    return order


@router.delete("/{order_id}", status_code=204)
async def delete_order(order_id: int):
    """Delete an order by ID."""
    if order_id not in _orders:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    del _orders[order_id]
