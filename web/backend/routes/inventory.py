"""Inventory CRUD API endpoints — products, categories, suppliers, stock_orders, warehouse_locations."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

# ─── Pydantic Models ──────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    sku: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    quantity: int = Field(0, ge=0)
    price: float = Field(..., ge=0)
    cost: Optional[float] = Field(None, ge=0)
    warehouse_location_id: Optional[int] = None
    reorder_level: int = Field(10, ge=0)

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    sku: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    quantity: Optional[int] = Field(None, ge=0)
    price: Optional[float] = Field(None, ge=0)
    cost: Optional[float] = Field(None, ge=0)
    warehouse_location_id: Optional[int] = None
    reorder_level: Optional[int] = Field(None, ge=0)

class Product(BaseModel):
    id: int
    name: str
    sku: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    quantity: int
    price: float
    cost: Optional[float] = None
    warehouse_location_id: Optional[int] = None
    reorder_level: int
    created_at: datetime
    updated_at: datetime

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None

class Category(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None

class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None

class Supplier(BaseModel):
    id: int
    name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class StockOrderCreate(BaseModel):
    product_id: int
    supplier_id: Optional[int] = None
    quantity: int = Field(..., ge=1)
    unit_cost: float = Field(..., ge=0)
    status: str = Field("pending", pattern="^(pending|ordered|received|cancelled)$")
    notes: Optional[str] = None

class StockOrderUpdate(BaseModel):
    product_id: Optional[int] = None
    supplier_id: Optional[int] = None
    quantity: Optional[int] = Field(None, ge=1)
    unit_cost: Optional[float] = Field(None, ge=0)
    status: Optional[str] = Field(None, pattern="^(pending|ordered|received|cancelled)$")
    notes: Optional[str] = None

class StockOrder(BaseModel):
    id: int
    product_id: int
    supplier_id: Optional[int] = None
    quantity: int
    unit_cost: float
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class WarehouseLocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    description: Optional[str] = None

class WarehouseLocationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    description: Optional[str] = None

class WarehouseLocation(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# ─── In-Memory Data Stores ───────────────────────────────────────────────────

_products: dict[int, dict] = {
    1: {"id": 1, "name": "Widget A", "sku": "WID-001", "description": "Standard widget",
        "category_id": 1, "supplier_id": 1, "quantity": 150, "price": 9.99, "cost": 4.50,
        "warehouse_location_id": 1, "reorder_level": 20,
        "created_at": datetime(2024, 1, 1), "updated_at": datetime(2024, 1, 1)},
    2: {"id": 2, "name": "Gadget B", "sku": "GAD-002", "description": "Premium gadget",
        "category_id": 2, "supplier_id": 2, "quantity": 75, "price": 24.50, "cost": 12.00,
        "warehouse_location_id": 2, "reorder_level": 15,
        "created_at": datetime(2024, 1, 2), "updated_at": datetime(2024, 1, 2)},
    3: {"id": 3, "name": "Component C", "sku": "COM-003", "description": "Raw component",
        "category_id": 3, "supplier_id": 1, "quantity": 300, "price": 3.75, "cost": 1.50,
        "warehouse_location_id": 1, "reorder_level": 50,
        "created_at": datetime(2024, 1, 3), "updated_at": datetime(2024, 1, 3)},
}
_categories: dict[int, dict] = {
    1: {"id": 1, "name": "Widgets", "description": "Standard widgets", "created_at": datetime(2024, 1, 1), "updated_at": datetime(2024, 1, 1)},
    2: {"id": 2, "name": "Gadgets", "description": "Premium gadgets", "created_at": datetime(2024, 1, 1), "updated_at": datetime(2024, 1, 1)},
    3: {"id": 3, "name": "Components", "description": "Raw components", "created_at": datetime(2024, 1, 1), "updated_at": datetime(2024, 1, 1)},
}
_suppliers: dict[int, dict] = {
    1: {"id": 1, "name": "Acme Supplies", "contact_email": "orders@acme.com", "contact_phone": "555-0100",
        "address": "123 Industrial Way", "created_at": datetime(2024, 1, 1), "updated_at": datetime(2024, 1, 1)},
    2: {"id": 2, "name": "TechParts Inc", "contact_email": "sales@techparts.com", "contact_phone": "555-0200",
        "address": "456 Tech Blvd", "created_at": datetime(2024, 1, 1), "updated_at": datetime(2024, 1, 1)},
}
_stock_orders: dict[int, dict] = {
    1: {"id": 1, "product_id": 1, "supplier_id": 1, "quantity": 100, "unit_cost": 4.50,
        "status": "received", "notes": "Initial stock", "created_at": datetime(2024, 1, 5), "updated_at": datetime(2024, 1, 5)},
    2: {"id": 2, "product_id": 2, "supplier_id": 2, "quantity": 50, "unit_cost": 12.00,
        "status": "pending", "notes": "Restock order", "created_at": datetime(2024, 1, 10), "updated_at": datetime(2024, 1, 10)},
}
_warehouse_locations: dict[int, dict] = {
    1: {"id": 1, "name": "Main Warehouse", "code": "WH-01", "description": "Primary storage facility", "created_at": datetime(2024, 1, 1), "updated_at": datetime(2024, 1, 1)},
    2: {"id": 2, "name": "Secondary Storage", "code": "WH-02", "description": "Overflow storage", "created_at": datetime(2024, 1, 1), "updated_at": datetime(2024, 1, 1)},
}

_next_ids = {"product": 4, "category": 4, "supplier": 3, "stock_order": 3, "warehouse_location": 3}

# ─── Helper ───────────────────────────────────────────────────────────────────

def _get_next_id(entity: str) -> int:
    val = _next_ids[entity]
    _next_ids[entity] += 1
    return val

# ─── Products CRUD ────────────────────────────────────────────────────────────

@router.get("/products", response_model=List[Product])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
):
    items = list(_products.values())
    if category_id is not None:
        items = [i for i in items if i.get("category_id") == category_id]
    if supplier_id is not None:
        items = [i for i in items if i.get("supplier_id") == supplier_id]
    return items[skip : skip + limit]

@router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: int):
    if product_id not in _products:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return _products[product_id]

@router.post("/products", response_model=Product, status_code=201)
async def create_product(product: ProductCreate):
    now = datetime.utcnow()
    pid = _get_next_id("product")
    new_product = {"id": pid, **product.model_dump(), "created_at": now, "updated_at": now}
    _products[pid] = new_product
    return new_product

@router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: int, product: ProductUpdate):
    if product_id not in _products:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    stored = _products[product_id]
    for field, value in product.model_dump(exclude_unset=True).items():
        stored[field] = value
    stored["updated_at"] = datetime.utcnow()
    return stored

@router.delete("/products/{product_id}", status_code=204)
async def delete_product(product_id: int):
    if product_id not in _products:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    del _products[product_id]

# ─── Categories CRUD ──────────────────────────────────────────────────────────

@router.get("/categories", response_model=List[Category])
async def list_categories(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    return list(_categories.values())[skip : skip + limit]

@router.get("/categories/{category_id}", response_model=Category)
async def get_category(category_id: int):
    if category_id not in _categories:
        raise HTTPException(status_code=404, detail=f"Category {category_id} not found")
    return _categories[category_id]

@router.post("/categories", response_model=Category, status_code=201)
async def create_category(category: CategoryCreate):
    now = datetime.utcnow()
    cid = _get_next_id("category")
    new_cat = {"id": cid, **category.model_dump(), "created_at": now, "updated_at": now}
    _categories[cid] = new_cat
    return new_cat

@router.put("/categories/{category_id}", response_model=Category)
async def update_category(category_id: int, category: CategoryUpdate):
    if category_id not in _categories:
        raise HTTPException(status_code=404, detail=f"Category {category_id} not found")
    stored = _categories[category_id]
    for field, value in category.model_dump(exclude_unset=True).items():
        stored[field] = value
    stored["updated_at"] = datetime.utcnow()
    return stored

@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(category_id: int):
    if category_id not in _categories:
        raise HTTPException(status_code=404, detail=f"Category {category_id} not found")
    del _categories[category_id]

# ─── Suppliers CRUD ───────────────────────────────────────────────────────────

@router.get("/suppliers", response_model=List[Supplier])
async def list_suppliers(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    return list(_suppliers.values())[skip : skip + limit]

@router.get("/suppliers/{supplier_id}", response_model=Supplier)
async def get_supplier(supplier_id: int):
    if supplier_id not in _suppliers:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    return _suppliers[supplier_id]

@router.post("/suppliers", response_model=Supplier, status_code=201)
async def create_supplier(supplier: SupplierCreate):
    now = datetime.utcnow()
    sid = _get_next_id("supplier")
    new_sup = {"id": sid, **supplier.model_dump(), "created_at": now, "updated_at": now}
    _suppliers[sid] = new_sup
    return new_sup

@router.put("/suppliers/{supplier_id}", response_model=Supplier)
async def update_supplier(supplier_id: int, supplier: SupplierUpdate):
    if supplier_id not in _suppliers:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    stored = _suppliers[supplier_id]
    for field, value in supplier.model_dump(exclude_unset=True).items():
        stored[field] = value
    stored["updated_at"] = datetime.utcnow()
    return stored

@router.delete("/suppliers/{supplier_id}", status_code=204)
async def delete_supplier(supplier_id: int):
    if supplier_id not in _suppliers:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    del _suppliers[supplier_id]

# ─── Stock Orders CRUD ────────────────────────────────────────────────────────

@router.get("/stock-orders", response_model=List[StockOrder])
async def list_stock_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    product_id: Optional[int] = None,
):
    items = list(_stock_orders.values())
    if status:
        items = [i for i in items if i.get("status") == status]
    if product_id is not None:
        items = [i for i in items if i.get("product_id") == product_id]
    return items[skip : skip + limit]

@router.get("/stock-orders/{order_id}", response_model=StockOrder)
async def get_stock_order(order_id: int):
    if order_id not in _stock_orders:
        raise HTTPException(status_code=404, detail=f"Stock order {order_id} not found")
    return _stock_orders[order_id]

@router.post("/stock-orders", response_model=StockOrder, status_code=201)
async def create_stock_order(order: StockOrderCreate):
    now = datetime.utcnow()
    oid = _get_next_id("stock_order")
    new_order = {"id": oid, **order.model_dump(), "created_at": now, "updated_at": now}
    _stock_orders[oid] = new_order
    return new_order

@router.put("/stock-orders/{order_id}", response_model=StockOrder)
async def update_stock_order(order_id: int, order: StockOrderUpdate):
    if order_id not in _stock_orders:
        raise HTTPException(status_code=404, detail=f"Stock order {order_id} not found")
    stored = _stock_orders[order_id]
    for field, value in order.model_dump(exclude_unset=True).items():
        stored[field] = value
    stored["updated_at"] = datetime.utcnow()
    return stored

@router.delete("/stock-orders/{order_id}", status_code=204)
async def delete_stock_order(order_id: int):
    if order_id not in _stock_orders:
        raise HTTPException(status_code=404, detail=f"Stock order {order_id} not found")
    del _stock_orders[order_id]

# ─── Warehouse Locations CRUD ─────────────────────────────────────────────────

@router.get("/warehouse-locations", response_model=List[WarehouseLocation])
async def list_warehouse_locations(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    return list(_warehouse_locations.values())[skip : skip + limit]

@router.get("/warehouse-locations/{location_id}", response_model=WarehouseLocation)
async def get_warehouse_location(location_id: int):
    if location_id not in _warehouse_locations:
        raise HTTPException(status_code=404, detail=f"Warehouse location {location_id} not found")
    return _warehouse_locations[location_id]

@router.post("/warehouse-locations", response_model=WarehouseLocation, status_code=201)
async def create_warehouse_location(location: WarehouseLocationCreate):
    now = datetime.utcnow()
    lid = _get_next_id("warehouse_location")
    new_loc = {"id": lid, **location.model_dump(), "created_at": now, "updated_at": now}
    _warehouse_locations[lid] = new_loc
    return new_loc

@router.put("/warehouse-locations/{location_id}", response_model=WarehouseLocation)
async def update_warehouse_location(location_id: int, location: WarehouseLocationUpdate):
    if location_id not in _warehouse_locations:
        raise HTTPException(status_code=404, detail=f"Warehouse location {location_id} not found")
    stored = _warehouse_locations[location_id]
    for field, value in location.model_dump(exclude_unset=True).items():
        stored[field] = value
    stored["updated_at"] = datetime.utcnow()
    return stored

@router.delete("/warehouse-locations/{location_id}", status_code=204)
async def delete_warehouse_location(location_id: int):
    if location_id not in _warehouse_locations:
        raise HTTPException(status_code=404, detail=f"Warehouse location {location_id} not found")
    del _warehouse_locations[location_id]
