"""Customer CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/customers", tags=["customers"])


class CustomerCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None


class CustomerResponse(CustomerCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


_customers = [
    {"id": 1, "name": "Alice Johnson", "email": "alice@example.com",
     "phone": "555-0101", "company": "Acme Corp", "created_at": datetime(2024, 1, 15)},
    {"id": 2, "name": "Bob Smith", "email": "bob@example.com",
     "phone": "555-0102", "company": "Globex", "created_at": datetime(2024, 2, 20)},
    {"id": 3, "name": "Carol White", "email": "carol@example.com",
     "phone": "555-0103", "company": "Initech", "created_at": datetime(2024, 3, 10)},
]
_next_id = 4


@router.get("/", response_model=list[CustomerResponse])
def list_customers(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)) -> List[CustomerResponse]:
    """List all customers with pagination."""
    try:
        return _customers[skip : skip + limit]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int) -> CustomerResponse:
    """Get a single customer by ID."""
    try:
        for c in _customers:
            if c["id"] == customer_id:
                return c
        raise HTTPException(status_code=404, detail="Customer not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=CustomerResponse, status_code=201)
def create_customer(customer: CustomerCreate) -> CustomerResponse:
    """Create a new customer."""
    try:
        global _next_id
        new_customer = {"id": _next_id, **customer.model_dump(), "created_at": datetime.now()}
        _customers.append(new_customer)
        _next_id += 1
        return new_customer
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: int, customer: CustomerUpdate) -> CustomerResponse:
    """Update an existing customer."""
    try:
        for i, c in enumerate(_customers):
            if c["id"] == customer_id:
                for field, value in customer.model_dump(exclude_unset=True).items( -> CustomerResponse:
                    _customers[i][field] = value
                return _customers[i]
        raise HTTPException(status_code=404, detail="Customer not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{customer_id}", status_code=204)
def delete_customer(customer_id: int) -> None:
    """Delete a customer by ID."""
    try:
        for i, c in enumerate(_customers -> None:
            if c["id"] == customer_id:
                _customers.pop(i)
                return
        raise HTTPException(status_code=404, detail="Customer not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
