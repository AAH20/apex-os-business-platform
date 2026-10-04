"""Accounting module CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

# Synthetic in-memory data store
_accounts_db = [
    {"id": 1, "name": "Cash", "type": "asset", "code": "1000", "balance": 50000.00,
     "currency": "USD", "is_active": True, "created_at": "2024-01-01T00:00:00"},
    {"id": 2, "name": "Accounts Receivable", "type": "asset", "code": "1100", "balance": 25000.00,
     "currency": "USD", "is_active": True, "created_at": "2024-01-01T00:00:00"},
    {"id": 3, "name": "Accounts Payable", "type": "liability", "code": "2000", "balance": 15000.00,
     "currency": "USD", "is_active": True, "created_at": "2024-01-01T00:00:00"},
    {"id": 4, "name": "Revenue", "type": "revenue", "code": "4000", "balance": 100000.00,
     "currency": "USD", "is_active": True, "created_at": "2024-01-01T00:00:00"},
    {"id": 5, "name": "Expenses", "type": "expense", "code": "5000", "balance": 75000.00,
     "currency": "USD", "is_active": True, "created_at": "2024-01-01T00:00:00"},
]
_next_id = 6


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(asset|liability|equity|revenue|expense)$")
    code: str = Field(..., min_length=1, max_length=20)
    balance: float = 0.0
    currency: str = "USD"
    is_active: bool = True


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[str] = Field(None, pattern="^(asset|liability|equity|revenue|expense)$")
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    balance: Optional[float] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


class AccountResponse(BaseModel):
    id: int
    name: str
    type: str
    code: str
    balance: float
    currency: str
    is_active: bool
    created_at: str


@router.get("/", response_model=List[AccountResponse])
async def list_accounts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    """List all accounts with pagination and optional filters."""
    results = _accounts_db
    if type:
        results = [a for a in results if a["type"] == type]
    if is_active is not None:
        results = [a for a in results if a["is_active"] == is_active]
    return results[skip : skip + limit]


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int):
    """Get a single account by ID."""
    for account in _accounts_db:
        if account["id"] == account_id:
            return account
    raise HTTPException(status_code=404, detail=f"Account {account_id} not found")


@router.post("", response_model=AccountResponse, status_code=201)
async def create_account(account: AccountCreate):
    """Create a new account."""
    global _next_id
    new_account = {
        "id": _next_id,
        **account.model_dump(),
        "created_at": datetime.utcnow().isoformat(),
    }
    _accounts_db.append(new_account)
    _next_id += 1
    return new_account


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(account_id: int, account: AccountUpdate):
    """Update an existing account."""
    for i, existing in enumerate(_accounts_db):
        if existing["id"] == account_id:
            updated = {**existing, **account.model_dump(exclude_unset=True)}
            _accounts_db[i] = updated
            return updated
    raise HTTPException(status_code=404, detail=f"Account {account_id} not found")


@router.delete("/{account_id}", status_code=204)
async def delete_account(account_id: int):
    """Delete an account."""
    for i, account in enumerate(_accounts_db):
        if account["id"] == account_id:
            _accounts_db.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
