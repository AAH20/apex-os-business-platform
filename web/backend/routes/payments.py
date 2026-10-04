"""Payment CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/payments", tags=["payments"])


class PaymentCreate(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    method: str
    status: str = Field(default="pending")
    order_id: Optional[str] = None
    customer_id: Optional[str] = None


class PaymentUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    method: Optional[str] = None
    status: Optional[str] = None
    order_id: Optional[str] = None
    customer_id: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int
    amount: float
    currency: str
    method: str
    status: str
    order_id: Optional[str] = None
    customer_id: Optional[str] = None
    created_at: str
    updated_at: str


# Synthetic in-memory data store
_payments_db: List[dict] = [
    {
        "id": i,
        "amount": round(50.0 + i * 25.99, 2),
        "currency": "USD",
        "method": ["credit_card", "bank_transfer", "paypal", "crypto"][i % 4],
        "status": ["pending", "completed", "failed", "refunded"][i % 4],
        "order_id": f"ORD-{1000 + i}",
        "customer_id": f"CUST-{2000 + i}",
        "created_at": datetime(2024, 1, i + 1).isoformat(),
        "updated_at": datetime(2024, 1, i + 1).isoformat(),
    }
    for i in range(1, 21)
]
_next_id = 21


@router.get("/", response_model=dict)
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
 -> dict:
    """List all payments with pagination."""
    try:
        start = (page - 1) * page_size
        end = start + page_size
        items = _payments_db[start:end]
        return {
            "items": items,
            "total": len(_payments_db),
            "page": page,
            "page_size": page_size,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: int):
    """Get a single payment by ID."""
    try:
        for p in _payments_db:
            if p["id"] == payment_id:
                return p
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=PaymentResponse, status_code=201)
async def create_payment(payment: PaymentCreate):
    """Create a new payment."""
    try:
        global _next_id
        now = datetime.utcnow().isoformat()
        new_payment = {
            "id": _next_id,
            **payment.model_dump(),
            "created_at": now,
            "updated_at": now,
        }
        _payments_db.append(new_payment)
        _next_id += 1
        return new_payment
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(payment_id: int, payment: PaymentUpdate):
    """Update an existing payment."""
    try:
        for i, p in enumerate(_payments_db -> PaymentResponse:
            if p["id"] == payment_id:
                updates = payment.model_dump(exclude_unset=True)
                _payments_db[i].update(updates)
                _payments_db[i]["updated_at"] = datetime.utcnow().isoformat()
                return _payments_db[i]
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{payment_id}", status_code=204)
async def delete_payment(payment_id: int):
    """Delete a payment by ID."""
    try:
        for i, p in enumerate(_payments_db -> None:
            if p["id"] == payment_id:
                _payments_db.pop(i)
                return
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
