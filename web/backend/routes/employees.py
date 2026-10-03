"""Employee CRUD API endpoints for APEX-OS Business Platform."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date

router = APIRouter(prefix="/api/employees", tags=["employees"])

# ── Synthetic in-memory data store ──────────────────────────────────────────

EMPLOYEES_DB: List[dict] = [
    {"id": 1, "first_name": "Alice", "last_name": "Johnson", "email": "alice.johnson@apex-os.com", "department": "Engineering", "position": "Senior Developer", "salary": 95000.00, "hire_date": "2022-03-15", "is_active": True},
    {"id": 2, "first_name": "Bob", "last_name": "Smith", "email": "bob.smith@apex-os.com", "department": "Marketing", "position": "Marketing Manager", "salary": 78000.00, "hire_date": "2021-07-01", "is_active": True},
    {"id": 3, "first_name": "Carol", "last_name": "Williams", "email": "carol.williams@apex-os.com", "department": "HR", "position": "HR Specialist", "salary": 65000.00, "hire_date": "2023-01-10", "is_active": False},
    {"id": 4, "first_name": "David", "last_name": "Brown", "email": "david.brown@apex-os.com", "department": "Engineering", "position": "DevOps Engineer", "salary": 88000.00, "hire_date": "2020-11-20", "is_active": True},
    {"id": 5, "first_name": "Eve", "last_name": "Davis", "email": "eve.davis@apex-os.com", "department": "Finance", "position": "Financial Analyst", "salary": 72000.00, "hire_date": "2022-09-05", "is_active": True},
]

_next_id = max(e["id"] for e in EMPLOYEES_DB) + 1


# ── Pydantic models ─────────────────────────────────────────────────────────

class EmployeeBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    department: str = Field(..., min_length=1, max_length=100)
    position: str = Field(..., min_length=1, max_length=100)
    salary: float = Field(..., gt=0)
    hire_date: date
    is_active: bool = True

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[EmailStr] = None
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    position: Optional[str] = Field(None, min_length=1, max_length=100)
    salary: Optional[float] = Field(None, gt=0)
    hire_date: Optional[date] = None
    is_active: Optional[bool] = None

class EmployeeResponse(EmployeeBase):
    id: int
    class Config:
        from_attributes = True

class PaginatedResponse(BaseModel):
    items: List[EmployeeResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse)
def list_employees(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100), department: Optional[str] = None, is_active: Optional[bool] = None):
    """List all employees with pagination and optional filters."""
    filtered = EMPLOYEES_DB
    if department:
        filtered = [e for e in filtered if e["department"].lower() == department.lower()]
    if is_active is not None:
        filtered = [e for e in filtered if e["is_active"] == is_active]
    total = len(filtered)
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    start = (page - 1) * page_size
    items = filtered[start:start + page_size]
    return PaginatedResponse(items=[EmployeeResponse(**e) for e in items], total=total, page=page, page_size=page_size, pages=pages)

@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(employee_id: int):
    """Get a single employee by ID."""
    for emp in EMPLOYEES_DB:
        if emp["id"] == employee_id:
            return EmployeeResponse(**emp)
    raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")

@router.post("", response_model=EmployeeResponse, status_code=201)
def create_employee(employee: EmployeeCreate):
    """Create a new employee."""
    global _next_id
    for emp in EMPLOYEES_DB:
        if emp["email"] == employee.email:
            raise HTTPException(status_code=409, detail=f"Employee with email {employee.email} already exists")
    new_emp = employee.model_dump()
    new_emp["id"] = _next_id
    _next_id += 1
    EMPLOYEES_DB.append(new_emp)
    return EmployeeResponse(**new_emp)

@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(employee_id: int, employee: EmployeeUpdate):
    """Update an existing employee (partial update)."""
    for idx, emp in enumerate(EMPLOYEES_DB):
        if emp["id"] == employee_id:
            update_data = employee.model_dump(exclude_unset=True)
            if "email" in update_data:
                for other in EMPLOYEES_DB:
                    if other["id"] != employee_id and other["email"] == update_data["email"]:
                        raise HTTPException(status_code=409, detail=f"Employee with email {update_data['email']} already exists")
            EMPLOYEES_DB[idx].update(update_data)
            return EmployeeResponse(**EMPLOYEES_DB[idx])
    raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")

@router.delete("/{employee_id}", status_code=204)
def delete_employee(employee_id: int):
    """Delete an employee by ID."""
    for idx, emp in enumerate(EMPLOYEES_DB):
        if emp["id"] == employee_id:
            EMPLOYEES_DB.pop(idx)
            return
    raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
