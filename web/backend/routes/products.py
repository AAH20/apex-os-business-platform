"""Product CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(prefix="/api/products", tags=["products"])


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    category: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    category: Optional[str] = None


class ProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    stock: int
    category: Optional[str] = None


_products_db = [
    {"id": 1, "name": "Widget A", "description": "Standard widget", "price": 9.99, "stock": 100, "category": "widgets"},
    {"id": 2, "name": "Gadget B", "description": "Premium gadget", "price": 24.99, "stock": 50, "category": "gadgets"},
    {"id": 3, "name": "Tool C", "description": "Professional tool", "price": 49.99, "stock": 25, "category": "tools"},
]
_next_id = 4


@router.get("", response_model=list[ProductResponse])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """List all products with pagination."""
    return _products_db[skip : skip + limit]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int):
    """Get a single product by ID."""
    for product in _products_db:
        if product["id"] == product_id:
            return product
    raise HTTPException(status_code=404, detail="Product not found")


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(product: ProductCreate):
    """Create a new product."""
    global _next_id
    new_product = {"id": _next_id, **product.model_dump()}
    _products_db.append(new_product)
    _next_id += 1
    return new_product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, product: ProductUpdate):
    """Update an existing product."""
    for idx, existing in enumerate(_products_db):
        if existing["id"] == product_id:
            updated = existing.copy()
            updated.update({k: v for k, v in product.model_dump().items() if v is not None})
            _products_db[idx] = updated
            return updated
    raise HTTPException(status_code=404, detail="Product not found")


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: int):
    """Delete a product by ID."""
    for idx, product in enumerate(_products_db):
        if product["id"] == product_id:
            _products_db.pop(idx)
            return
    raise HTTPException(status_code=404, detail="Product not found")
