"""Invoice CRUD API endpoints for APEX-OS Business Platform."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
import uuid

router = APIRouter(prefix="/api/invoices", tags=["invoices"])

# ── Synthetic in-memory store ──────────────────────────────────────────────
_invoices: dict[str, dict] = {}


def _seed():
    """Populate with sample invoices."""
    for i in range(1, 6):
        inv_id = f"INV-{1000 + i}"
        _invoices[inv_id] = {
            "id": inv_id,
            "customer_name": f"Customer {i}",
            "customer_email": f"customer{i}@example.com",
            "amount": 100.0 * i + 25.50,
            "currency": "USD",
            "status": ["draft", "sent", "paid", "overdue", "cancelled"][i - 1],
            "issue_date": date(2025, 1, i).isoformat(),
            "due_date": date(2025, 2, i).isoformat(),
            "description": f"Invoice for project deliverable {i}",
            "created_at": datetime(2025, 1, i, 10, 0, 0).isoformat(),
            "updated_at": datetime(2025, 1, i, 10, 0, 0).isoformat(),
        }


_seed()


# ── Pydantic models ────────────────────────────────────────────────────────
class InvoiceCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=200)
    customer_email: str = Field(..., min_length=3, max_length=200)
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    status: str = Field(default="draft")
    issue_date: date
    due_date: date
    description: Optional[str] = Field(default=None, max_length=1000)


class InvoiceUpdate(BaseModel):
    customer_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    customer_email: Optional[str] = Field(default=None, min_length=3, max_length=200)
    amount: Optional[float] = Field(default=None, gt=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    status: Optional[str] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    description: Optional[str] = Field(default=None, max_length=1000)


class InvoiceResponse(BaseModel):
    id: str
    customer_name: str
    customer_email: str
    amount: float
    currency: str
    status: str
    issue_date: str
    due_date: str
    description: Optional[str] = None
    created_at: str
    updated_at: str


class InvoiceListResponse(BaseModel):
    data: List[InvoiceResponse]
    total: int
    page: int
    page_size: int


# ── Cache ──────────────────────────────────────────────────────────────────
_list_cache: Optional[InvoiceListResponse] = None
_list_cache_key: Optional[tuple] = None


def _invalidate_cache():
    global _list_cache, _list_cache_key
    _list_cache = None
    _list_cache_key = None


# ── Endpoints ──────────────────────────────────────────────────────────────
@router.get("", response_model=InvoiceListResponse)
def list_invoices(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    status_filter: Optional[str] = Query(default=None, alias="status"),
):
    """List all invoices with pagination and optional status filter."""
    global _list_cache, _list_cache_key

    cache_key = (page, page_size, status_filter)
    if _list_cache is not None and _list_cache_key == cache_key:
        return _list_cache

    items = list(_invoices.values())
    if status_filter:
        items = [i for i in items if i["status"] == status_filter]
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    result = InvoiceListResponse(
        data=items[start:end], total=total, page=page, page_size=page_size
    )
    _list_cache = result
    _list_cache_key = cache_key
    return result


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: str):
    """Get a single invoice by ID."""
    if invoice_id not in _invoices:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    return _invoices[invoice_id]


@router.post("", response_model=InvoiceResponse, status_code=201)
def create_invoice(payload: InvoiceCreate):
    """Create a new invoice."""
    inv_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.utcnow().isoformat()
    invoice = {
        "id": inv_id,
        **payload.model_dump(),
        "issue_date": payload.issue_date.isoformat(),
        "due_date": payload.due_date.isoformat(),
        "created_at": now,
        "updated_at": now,
    }
    _invoices[inv_id] = invoice
    _invalidate_cache()
    return invoice


@router.put("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(invoice_id: str, payload: InvoiceUpdate):
    """Update an existing invoice."""
    if invoice_id not in _invoices:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    stored = _invoices[invoice_id]
    for field, value in payload.model_dump(exclude_unset=True).items():
        stored[field] = value.isoformat() if isinstance(value, date) else value
    stored["updated_at"] = datetime.utcnow().isoformat()
    _invalidate_cache()
    return stored


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: str):
    """Delete an invoice by ID."""
    if invoice_id not in _invoices:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    del _invoices[invoice_id]
    _invalidate_cache()
