"""Supply Chain CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/supply-chain", tags=["supply-chain"])


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    status: Optional[str] = "active"


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    status: Optional[str] = None


class Supplier(BaseModel):
    id: int
    name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    status: Optional[str] = "active"
    created_at: datetime
    updated_at: datetime


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    product_name: str = Field(..., min_length=1, max_length=200)
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., ge=0)
    status: Optional[str] = "pending"
    expected_delivery: Optional[str] = None


class PurchaseOrderUpdate(BaseModel):
    supplier_id: Optional[int] = None
    product_name: Optional[str] = Field(None, min_length=1, max_length=200)
    quantity: Optional[int] = Field(None, ge=1)
    unit_price: Optional[float] = Field(None, ge=0)
    status: Optional[str] = None
    expected_delivery: Optional[str] = None


class PurchaseOrder(BaseModel):
    id: int
    supplier_id: int
    product_name: str
    quantity: int
    unit_price: float
    total_price: float
    status: str
    expected_delivery: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ShipmentCreate(BaseModel):
    purchase_order_id: int
    origin: str = Field(..., min_length=1, max_length=200)
    destination: str = Field(..., min_length=1, max_length=200)
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    status: Optional[str] = "in_transit"
    shipped_date: Optional[str] = None
    estimated_arrival: Optional[str] = None


class ShipmentUpdate(BaseModel):
    purchase_order_id: Optional[int] = None
    origin: Optional[str] = Field(None, min_length=1, max_length=200)
    destination: Optional[str] = Field(None, min_length=1, max_length=200)
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    status: Optional[str] = None
    shipped_date: Optional[str] = None
    estimated_arrival: Optional[str] = None


class Shipment(BaseModel):
    id: int
    purchase_order_id: int
    origin: str
    destination: str
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    status: str
    shipped_date: Optional[str] = None
    estimated_arrival: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class LogisticsRouteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    origin: str = Field(..., min_length=1, max_length=200)
    destination: str = Field(..., min_length=1, max_length=200)
    distance_km: Optional[float] = Field(None, ge=0)
    estimated_duration_hours: Optional[float] = Field(None, ge=0)
    transport_mode: Optional[str] = None
    cost: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = True


class LogisticsRouteUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    origin: Optional[str] = Field(None, min_length=1, max_length=200)
    destination: Optional[str] = Field(None, min_length=1, max_length=200)
    distance_km: Optional[float] = Field(None, ge=0)
    estimated_duration_hours: Optional[float] = Field(None, ge=0)
    transport_mode: Optional[str] = None
    cost: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None


class LogisticsRoute(BaseModel):
    id: int
    name: str
    origin: str
    destination: str
    distance_km: Optional[float] = None
    estimated_duration_hours: Optional[float] = None
    transport_mode: Optional[str] = None
    cost: Optional[float] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ─── In-Memory Data Store ─────────────────────────────────────────────────────

_suppliers_db: dict[int, dict] = {
    1: {"id": 1, "name": "Acme Supplies", "contact_email": "orders@acme.com", "contact_phone": "+1-555-0101",
        "address": "123 Industrial Way", "country": "USA", "status": "active",
        "created_at": datetime(2024, 1, 1), "updated_at": datetime(2024, 1, 1)},
    2: {"id": 2, "name": "Global Parts Co", "contact_email": "sales@globalparts.com", "contact_phone": "+1-555-0202",
        "address": "456 Commerce Blvd", "country": "Germany", "status": "active",
        "created_at": datetime(2024, 1, 2), "updated_at": datetime(2024, 1, 2)},
    3: {"id": 3, "name": "TechSource Ltd", "contact_email": "info@techsource.com", "contact_phone": "+1-555-0303",
        "address": "789 Innovation Dr", "country": "Japan", "status": "active",
        "created_at": datetime(2024, 1, 3), "updated_at": datetime(2024, 1, 3)},
}
_next_supplier_id = 4

_purchase_orders_db: dict[int, dict] = {
    1: {"id": 1, "supplier_id": 1, "product_name": "Widget A", "quantity": 100, "unit_price": 9.99,
        "total_price": 999.00, "status": "pending", "expected_delivery": "2024-02-15",
        "created_at": datetime(2024, 1, 10), "updated_at": datetime(2024, 1, 10)},
    2: {"id": 2, "supplier_id": 2, "product_name": "Gadget B", "quantity": 50, "unit_price": 24.50,
        "total_price": 1225.00, "status": "approved", "expected_delivery": "2024-02-20",
        "created_at": datetime(2024, 1, 11), "updated_at": datetime(2024, 1, 11)},
    3: {"id": 3, "supplier_id": 3, "product_name": "Component C", "quantity": 200, "unit_price": 3.75,
        "total_price": 750.00, "status": "delivered", "expected_delivery": "2024-02-10",
        "created_at": datetime(2024, 1, 12), "updated_at": datetime(2024, 1, 12)},
}
_next_po_id = 4

_shipments_db: dict[int, dict] = {
    1: {"id": 1, "purchase_order_id": 1, "origin": "Shanghai, CN", "destination": "Los Angeles, US",
        "carrier": "Maersk", "tracking_number": "MSK-001234", "status": "in_transit",
        "shipped_date": "2024-01-15", "estimated_arrival": "2024-02-15",
        "created_at": datetime(2024, 1, 15), "updated_at": datetime(2024, 1, 15)},
    2: {"id": 2, "purchase_order_id": 2, "origin": "Berlin, DE", "destination": "New York, US",
        "carrier": "DHL", "tracking_number": "DHL-005678", "status": "delivered",
        "shipped_date": "2024-01-10", "estimated_arrival": "2024-01-20",
        "created_at": datetime(2024, 1, 10), "updated_at": datetime(2024, 1, 10)},
}
_next_shipment_id = 3

_logistics_routes_db: dict[int, dict] = {
    1: {"id": 1, "name": "Trans-Pacific Route", "origin": "Shanghai, CN", "destination": "Los Angeles, US",
        "distance_km": 10500.0, "estimated_duration_hours": 336.0, "transport_mode": "sea",
        "cost": 2500.00, "is_active": True,
        "created_at": datetime(2024, 1, 1), "updated_at": datetime(2024, 1, 1)},
    2: {"id": 2, "name": "Euro-Atlantic Route", "origin": "Berlin, DE", "destination": "New York, US",
        "distance_km": 6380.0, "estimated_duration_hours": 168.0, "transport_mode": "air",
        "cost": 5800.00, "is_active": True,
        "created_at": datetime(2024, 1, 2), "updated_at": datetime(2024, 1, 2)},
    3: {"id": 3, "name": "Domestic Express", "origin": "Chicago, US", "destination": "Dallas, US",
        "distance_km": 1290.0, "estimated_duration_hours": 18.0, "transport_mode": "road",
        "cost": 450.00, "is_active": True,
        "created_at": datetime(2024, 1, 3), "updated_at": datetime(2024, 1, 3)},
}
_next_route_id = 4


# ─── Supplier Endpoints ───────────────────────────────────────────────────────

@router.get("/suppliers", response_model=List[Supplier])
async def list_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
):
    """List all suppliers with pagination and optional status filter."""
    items = list(_suppliers_db.values())
    if status:
        items = [s for s in items if s.get("status") == status]
    return items[skip : skip + limit]


@router.get("/suppliers/{supplier_id}", response_model=Supplier)
async def get_supplier(supplier_id: int):
    """Get a single supplier by ID."""
    if supplier_id not in _suppliers_db:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    return _suppliers_db[supplier_id]


@router.post("/suppliers", response_model=Supplier, status_code=201)
async def create_supplier(supplier: SupplierCreate):
    """Create a new supplier."""
    global _next_supplier_id
    now = datetime.utcnow()
    new_item = {
        "id": _next_supplier_id,
        **supplier.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _suppliers_db[_next_supplier_id] = new_item
    _next_supplier_id += 1
    return new_item


@router.put("/suppliers/{supplier_id}", response_model=Supplier)
async def update_supplier(supplier_id: int, supplier: SupplierUpdate):
    """Update an existing supplier."""
    if supplier_id not in _suppliers_db:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    stored = _suppliers_db[supplier_id]
    update_data = supplier.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        stored[field] = value
    stored["updated_at"] = datetime.utcnow()
    return stored


@router.delete("/suppliers/{supplier_id}", status_code=204)
async def delete_supplier(supplier_id: int):
    """Delete a supplier."""
    if supplier_id not in _suppliers_db:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    del _suppliers_db[supplier_id]


# ─── Purchase Order Endpoints ─────────────────────────────────────────────────

@router.get("/purchase-orders", response_model=List[PurchaseOrder])
async def list_purchase_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    supplier_id: Optional[int] = None,
):
    """List all purchase orders with pagination and optional filters."""
    items = list(_purchase_orders_db.values())
    if status:
        items = [po for po in items if po.get("status") == status]
    if supplier_id:
        items = [po for po in items if po.get("supplier_id") == supplier_id]
    return items[skip : skip + limit]


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrder)
async def get_purchase_order(po_id: int):
    """Get a single purchase order by ID."""
    if po_id not in _purchase_orders_db:
        raise HTTPException(status_code=404, detail=f"Purchase order {po_id} not found")
    return _purchase_orders_db[po_id]


@router.post("/purchase-orders", response_model=PurchaseOrder, status_code=201)
async def create_purchase_order(po: PurchaseOrderCreate):
    """Create a new purchase order."""
    global _next_po_id
    now = datetime.utcnow()
    total = po.quantity * po.unit_price
    new_item = {
        "id": _next_po_id,
        **po.model_dump(),
        "total_price": total,
        "created_at": now,
        "updated_at": now,
    }
    _purchase_orders_db[_next_po_id] = new_item
    _next_po_id += 1
    return new_item


@router.put("/purchase-orders/{po_id}", response_model=PurchaseOrder)
async def update_purchase_order(po_id: int, po: PurchaseOrderUpdate):
    """Update an existing purchase order."""
    if po_id not in _purchase_orders_db:
        raise HTTPException(status_code=404, detail=f"Purchase order {po_id} not found")
    stored = _purchase_orders_db[po_id]
    update_data = po.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        stored[field] = value
    stored["total_price"] = stored["quantity"] * stored["unit_price"]
    stored["updated_at"] = datetime.utcnow()
    return stored


@router.delete("/purchase-orders/{po_id}", status_code=204)
async def delete_purchase_order(po_id: int):
    """Delete a purchase order."""
    if po_id not in _purchase_orders_db:
        raise HTTPException(status_code=404, detail=f"Purchase order {po_id} not found")
    del _purchase_orders_db[po_id]


# ─── Shipment Endpoints ───────────────────────────────────────────────────────

@router.get("/shipments", response_model=List[Shipment])
async def list_shipments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
):
    """List all shipments with pagination and optional status filter."""
    items = list(_shipments_db.values())
    if status:
        items = [s for s in items if s.get("status") == status]
    return items[skip : skip + limit]


@router.get("/shipments/{shipment_id}", response_model=Shipment)
async def get_shipment(shipment_id: int):
    """Get a single shipment by ID."""
    if shipment_id not in _shipments_db:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    return _shipments_db[shipment_id]


@router.post("/shipments", response_model=Shipment, status_code=201)
async def create_shipment(shipment: ShipmentCreate):
    """Create a new shipment."""
    global _next_shipment_id
    now = datetime.utcnow()
    new_item = {
        "id": _next_shipment_id,
        **shipment.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _shipments_db[_next_shipment_id] = new_item
    _next_shipment_id += 1
    return new_item


@router.put("/shipments/{shipment_id}", response_model=Shipment)
async def update_shipment(shipment_id: int, shipment: ShipmentUpdate):
    """Update an existing shipment."""
    if shipment_id not in _shipments_db:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    stored = _shipments_db[shipment_id]
    update_data = shipment.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        stored[field] = value
    stored["updated_at"] = datetime.utcnow()
    return stored


@router.delete("/shipments/{shipment_id}", status_code=204)
async def delete_shipment(shipment_id: int):
    """Delete a shipment."""
    if shipment_id not in _shipments_db:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    del _shipments_db[shipment_id]


# ─── Logistics Route Endpoints ────────────────────────────────────────────────

@router.get("/logistics-routes", response_model=List[LogisticsRoute])
async def list_logistics_routes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
):
    """List all logistics routes with pagination and optional active filter."""
    items = list(_logistics_routes_db.values())
    if is_active is not None:
        items = [r for r in items if r.get("is_active") == is_active]
    return items[skip : skip + limit]


@router.get("/logistics-routes/{route_id}", response_model=LogisticsRoute)
async def get_logistics_route(route_id: int):
    """Get a single logistics route by ID."""
    if route_id not in _logistics_routes_db:
        raise HTTPException(status_code=404, detail=f"Logistics route {route_id} not found")
    return _logistics_routes_db[route_id]


@router.post("/logistics-routes", response_model=LogisticsRoute, status_code=201)
async def create_logistics_route(route: LogisticsRouteCreate):
    """Create a new logistics route."""
    global _next_route_id
    now = datetime.utcnow()
    new_item = {
        "id": _next_route_id,
        **route.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _logistics_routes_db[_next_route_id] = new_item
    _next_route_id += 1
    return new_item


@router.put("/logistics-routes/{route_id}", response_model=LogisticsRoute)
async def update_logistics_route(route_id: int, route: LogisticsRouteUpdate):
    """Update an existing logistics route."""
    if route_id not in _logistics_routes_db:
        raise HTTPException(status_code=404, detail=f"Logistics route {route_id} not found")
    stored = _logistics_routes_db[route_id]
    update_data = route.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        stored[field] = value
    stored["updated_at"] = datetime.utcnow()
    return stored


@router.delete("/logistics-routes/{route_id}", status_code=204)
async def delete_logistics_route(route_id: int):
    """Delete a logistics route."""
    if route_id not in _logistics_routes_db:
        raise HTTPException(status_code=404, detail=f"Logistics route {route_id} not found")
    del _logistics_routes_db[route_id]
