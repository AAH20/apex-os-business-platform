"""HR module CRUD API endpoints for APEX-OS Business Platform."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date

router = APIRouter(prefix="/api/hr", tags=["hr"])

# ── In-memory data stores ───────────────────────────────────────────────────

DEPARTMENTS_DB: List[dict] = [
    {"id": 1, "name": "Engineering", "head": "Alice Johnson", "budget": 500000.00},
    {"id": 2, "name": "Marketing", "head": "Bob Smith", "budget": 250000.00},
    {"id": 3, "name": "HR", "head": "Carol Williams", "budget": 150000.00},
    {"id": 4, "name": "Finance", "head": "Eve Davis", "budget": 300000.00},
    {"id": 5, "name": "Operations", "head": "Frank Miller", "budget": 200000.00},
]

POSITIONS_DB: List[dict] = [
    {"id": 1, "title": "Senior Developer", "department_id": 1, "level": "senior", "salary_min": 80000.00, "salary_max": 120000.00},
    {"id": 2, "title": "DevOps Engineer", "department_id": 1, "level": "mid", "salary_min": 70000.00, "salary_max": 100000.00},
    {"id": 3, "title": "Marketing Manager", "department_id": 2, "level": "manager", "salary_min": 65000.00, "salary_max": 90000.00},
    {"id": 4, "title": "HR Specialist", "department_id": 3, "level": "mid", "salary_min": 50000.00, "salary_max": 75000.00},
    {"id": 5, "title": "Financial Analyst", "department_id": 4, "level": "mid", "salary_min": 60000.00, "salary_max": 85000.00},
]

EMPLOYEES_DB: List[dict] = [
    {"id": 1, "first_name": "Alice", "last_name": "Johnson", "email": "alice.johnson@apex-os.com",
     "department_id": 1, "position_id": 1, "salary": 95000.00, "hire_date": "2022-03-15", "is_active": True},
    {"id": 2, "first_name": "Bob", "last_name": "Smith", "email": "bob.smith@apex-os.com",
     "department_id": 2, "position_id": 3, "salary": 78000.00, "hire_date": "2021-07-01", "is_active": True},
    {"id": 3, "first_name": "Carol", "last_name": "Williams", "email": "carol.williams@apex-os.com",
     "department_id": 3, "position_id": 4, "salary": 65000.00, "hire_date": "2023-01-10", "is_active": False},
    {"id": 4, "first_name": "David", "last_name": "Brown", "email": "david.brown@apex-os.com",
     "department_id": 1, "position_id": 2, "salary": 88000.00, "hire_date": "2020-11-20", "is_active": True},
    {"id": 5, "first_name": "Eve", "last_name": "Davis", "email": "eve.davis@apex-os.com",
     "department_id": 4, "position_id": 5, "salary": 72000.00, "hire_date": "2022-09-05", "is_active": True},
]

LEAVE_REQUESTS_DB: List[dict] = [
    {"id": 1, "employee_id": 1, "leave_type": "vacation", "start_date": "2026-11-01", "end_date": "2026-11-05",
     "status": "pending", "reason": "Family vacation"},
    {"id": 2, "employee_id": 2, "leave_type": "sick", "start_date": "2026-10-10", "end_date": "2026-10-12",
     "status": "approved", "reason": "Medical appointment"},
    {"id": 3, "employee_id": 4, "leave_type": "personal", "start_date": "2026-12-20", "end_date": "2026-12-22",
     "status": "pending", "reason": "Personal matters"},
]

PERFORMANCE_REVIEWS_DB: List[dict] = [
    {"id": 1, "employee_id": 1, "review_date": "2026-06-01", "reviewer_id": 2,
     "rating": 4.5, "goals_met": True, "comments": "Excellent performance on Q2 project delivery."},
    {"id": 2, "employee_id": 2, "review_date": "2026-06-15", "reviewer_id": 3,
     "rating": 3.8, "goals_met": True, "comments": "Good leadership on marketing campaigns."},
    {"id": 3, "employee_id": 4, "review_date": "2026-07-01", "reviewer_id": 1,
     "rating": 4.2, "goals_met": False, "comments": "Strong technical skills, needs improvement in documentation."},
]

_next_ids = {
    "departments": max(d["id"] for d in DEPARTMENTS_DB) + 1,
    "positions": max(p["id"] for p in POSITIONS_DB) + 1,
    "employees": max(e["id"] for e in EMPLOYEES_DB) + 1,
    "leave_requests": max(l["id"] for l in LEAVE_REQUESTS_DB) + 1,
    "performance_reviews": max(r["id"] for r in PERFORMANCE_REVIEWS_DB) + 1,
}


# ── Pydantic models ─────────────────────────────────────────────────────────

class DepartmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    head: str = Field(..., min_length=1, max_length=100)
    budget: float = Field(..., gt=0)

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    head: Optional[str] = Field(None, min_length=1, max_length=100)
    budget: Optional[float] = Field(None, gt=0)

class DepartmentResponse(DepartmentBase):
    id: int
    class Config:
        from_attributes = True


class PositionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    department_id: int
    level: str = Field(..., min_length=1, max_length=50)
    salary_min: float = Field(..., gt=0)
    salary_max: float = Field(..., gt=0)

class PositionCreate(PositionBase):
    pass

class PositionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    department_id: Optional[int] = None
    level: Optional[str] = Field(None, min_length=1, max_length=50)
    salary_min: Optional[float] = Field(None, gt=0)
    salary_max: Optional[float] = Field(None, gt=0)

class PositionResponse(PositionBase):
    id: int
    class Config:
        from_attributes = True


class EmployeeBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    department_id: int
    position_id: int
    salary: float = Field(..., gt=0)
    hire_date: date
    is_active: bool = True

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[EmailStr] = None
    department_id: Optional[int] = None
    position_id: Optional[int] = None
    salary: Optional[float] = Field(None, gt=0)
    hire_date: Optional[date] = None
    is_active: Optional[bool] = None

class EmployeeResponse(EmployeeBase):
    id: int
    class Config:
        from_attributes = True


class LeaveRequestBase(BaseModel):
    employee_id: int
    leave_type: str = Field(..., min_length=1, max_length=50)
    start_date: date
    end_date: date
    status: str = Field(default="pending", pattern="^(pending|approved|rejected)$")
    reason: Optional[str] = None

class LeaveRequestCreate(LeaveRequestBase):
    pass

class LeaveRequestUpdate(BaseModel):
    leave_type: Optional[str] = Field(None, min_length=1, max_length=50)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = Field(None, pattern="^(pending|approved|rejected)$")
    reason: Optional[str] = None

class LeaveRequestResponse(LeaveRequestBase):
    id: int
    class Config:
        from_attributes = True


class PerformanceReviewBase(BaseModel):
    employee_id: int
    review_date: date
    reviewer_id: int
    rating: float = Field(..., ge=0, le=5)
    goals_met: bool
    comments: Optional[str] = None

class PerformanceReviewCreate(PerformanceReviewBase):
    pass

class PerformanceReviewUpdate(BaseModel):
    review_date: Optional[date] = None
    reviewer_id: Optional[int] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    goals_met: Optional[bool] = None
    comments: Optional[str] = None

class PerformanceReviewResponse(PerformanceReviewBase):
    id: int
    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int
    pages: int


# ── Helper ──────────────────────────────────────────────────────────────────

def _paginate(items: list, page: int, page_size: int) -> PaginatedResponse:
    total = len(items)
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    start = (page - 1) * page_size
    return PaginatedResponse(
        items=items[start:start + page_size],
        total=total, page=page, page_size=page_size, pages=pages,
    )


# ── Department endpoints ────────────────────────────────────────────────────

@router.get("/departments", response_model=PaginatedResponse)
def list_departments(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    return _paginate(DEPARTMENTS_DB, page, page_size)

@router.get("/departments/{department_id}", response_model=DepartmentResponse)
def get_department(department_id: int):
    for d in DEPARTMENTS_DB:
        if d["id"] == department_id:
            return DepartmentResponse(**d)
    raise HTTPException(status_code=404, detail=f"Department {department_id} not found")

@router.post("/departments", response_model=DepartmentResponse, status_code=201)
def create_department(department: DepartmentCreate):
    global _next_ids
    new = department.model_dump()
    new["id"] = _next_ids["departments"]
    _next_ids["departments"] += 1
    DEPARTMENTS_DB.append(new)
    return DepartmentResponse(**new)

@router.put("/departments/{department_id}", response_model=DepartmentResponse)
def update_department(department_id: int, department: DepartmentUpdate):
    for idx, d in enumerate(DEPARTMENTS_DB):
        if d["id"] == department_id:
            DEPARTMENTS_DB[idx].update(department.model_dump(exclude_unset=True))
            return DepartmentResponse(**DEPARTMENTS_DB[idx])
    raise HTTPException(status_code=404, detail=f"Department {department_id} not found")

@router.delete("/departments/{department_id}", status_code=204)
def delete_department(department_id: int):
    for idx, d in enumerate(DEPARTMENTS_DB):
        if d["id"] == department_id:
            DEPARTMENTS_DB.pop(idx)
            return
    raise HTTPException(status_code=404, detail=f"Department {department_id} not found")


# ── Position endpoints ──────────────────────────────────────────────────────

@router.get("/positions", response_model=PaginatedResponse)
def list_positions(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    return _paginate(POSITIONS_DB, page, page_size)

@router.get("/positions/{position_id}", response_model=PositionResponse)
def get_position(position_id: int):
    for p in POSITIONS_DB:
        if p["id"] == position_id:
            return PositionResponse(**p)
    raise HTTPException(status_code=404, detail=f"Position {position_id} not found")

@router.post("/positions", response_model=PositionResponse, status_code=201)
def create_position(position: PositionCreate):
    global _next_ids
    new = position.model_dump()
    new["id"] = _next_ids["positions"]
    _next_ids["positions"] += 1
    POSITIONS_DB.append(new)
    return PositionResponse(**new)

@router.put("/positions/{position_id}", response_model=PositionResponse)
def update_position(position_id: int, position: PositionUpdate):
    for idx, p in enumerate(POSITIONS_DB):
        if p["id"] == position_id:
            POSITIONS_DB[idx].update(position.model_dump(exclude_unset=True))
            return PositionResponse(**POSITIONS_DB[idx])
    raise HTTPException(status_code=404, detail=f"Position {position_id} not found")

@router.delete("/positions/{position_id}", status_code=204)
def delete_position(position_id: int):
    for idx, p in enumerate(POSITIONS_DB):
        if p["id"] == position_id:
            POSITIONS_DB.pop(idx)
            return
    raise HTTPException(status_code=404, detail=f"Position {position_id} not found")


# ── Employee endpoints ──────────────────────────────────────────────────────

@router.get("/employees", response_model=PaginatedResponse)
def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    department_id: Optional[int] = None,
    is_active: Optional[bool] = None,
):
    filtered = EMPLOYEES_DB
    if department_id is not None:
        filtered = [e for e in filtered if e["department_id"] == department_id]
    if is_active is not None:
        filtered = [e for e in filtered if e["is_active"] == is_active]
    return _paginate(filtered, page, page_size)

@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
def get_employee(employee_id: int):
    for e in EMPLOYEES_DB:
        if e["id"] == employee_id:
            return EmployeeResponse(**e)
    raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")

@router.post("/employees", response_model=EmployeeResponse, status_code=201)
def create_employee(employee: EmployeeCreate):
    global _next_ids
    for e in EMPLOYEES_DB:
        if e["email"] == employee.email:
            raise HTTPException(status_code=409, detail=f"Employee with email {employee.email} already exists")
    new = employee.model_dump()
    new["id"] = _next_ids["employees"]
    _next_ids["employees"] += 1
    EMPLOYEES_DB.append(new)
    return EmployeeResponse(**new)

@router.put("/employees/{employee_id}", response_model=EmployeeResponse)
def update_employee(employee_id: int, employee: EmployeeUpdate):
    for idx, e in enumerate(EMPLOYEES_DB):
        if e["id"] == employee_id:
            update_data = employee.model_dump(exclude_unset=True)
            if "email" in update_data:
                for other in EMPLOYEES_DB:
                    if other["id"] != employee_id and other["email"] == update_data["email"]:
                        raise HTTPException(status_code=409, detail=f"Email {update_data['email']} already exists")
            EMPLOYEES_DB[idx].update(update_data)
            return EmployeeResponse(**EMPLOYEES_DB[idx])
    raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")

@router.delete("/employees/{employee_id}", status_code=204)
def delete_employee(employee_id: int):
    for idx, e in enumerate(EMPLOYEES_DB):
        if e["id"] == employee_id:
            EMPLOYEES_DB.pop(idx)
            return
    raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")


# ── Leave Request endpoints ─────────────────────────────────────────────────

@router.get("/leave-requests", response_model=PaginatedResponse)
def list_leave_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    employee_id: Optional[int] = None,
    status: Optional[str] = None,
):
    filtered = LEAVE_REQUESTS_DB
    if employee_id is not None:
        filtered = [l for l in filtered if l["employee_id"] == employee_id]
    if status:
        filtered = [l for l in filtered if l["status"] == status]
    return _paginate(filtered, page, page_size)

@router.get("/leave-requests/{leave_id}", response_model=LeaveRequestResponse)
def get_leave_request(leave_id: int):
    for l in LEAVE_REQUESTS_DB:
        if l["id"] == leave_id:
            return LeaveRequestResponse(**l)
    raise HTTPException(status_code=404, detail=f"Leave request {leave_id} not found")

@router.post("/leave-requests", response_model=LeaveRequestResponse, status_code=201)
def create_leave_request(leave: LeaveRequestCreate):
    global _next_ids
    new = leave.model_dump()
    new["id"] = _next_ids["leave_requests"]
    _next_ids["leave_requests"] += 1
    LEAVE_REQUESTS_DB.append(new)
    return LeaveRequestResponse(**new)

@router.put("/leave-requests/{leave_id}", response_model=LeaveRequestResponse)
def update_leave_request(leave_id: int, leave: LeaveRequestUpdate):
    for idx, l in enumerate(LEAVE_REQUESTS_DB):
        if l["id"] == leave_id:
            LEAVE_REQUESTS_DB[idx].update(leave.model_dump(exclude_unset=True))
            return LeaveRequestResponse(**LEAVE_REQUESTS_DB[idx])
    raise HTTPException(status_code=404, detail=f"Leave request {leave_id} not found")

@router.delete("/leave-requests/{leave_id}", status_code=204)
def delete_leave_request(leave_id: int):
    for idx, l in enumerate(LEAVE_REQUESTS_DB):
        if l["id"] == leave_id:
            LEAVE_REQUESTS_DB.pop(idx)
            return
    raise HTTPException(status_code=404, detail=f"Leave request {leave_id} not found")


# ── Performance Review endpoints ────────────────────────────────────────────

@router.get("/performance-reviews", response_model=PaginatedResponse)
def list_performance_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    employee_id: Optional[int] = None,
):
    filtered = PERFORMANCE_REVIEWS_DB
    if employee_id is not None:
        filtered = [r for r in filtered if r["employee_id"] == employee_id]
    return _paginate(filtered, page, page_size)

@router.get("/performance-reviews/{review_id}", response_model=PerformanceReviewResponse)
def get_performance_review(review_id: int):
    for r in PERFORMANCE_REVIEWS_DB:
        if r["id"] == review_id:
            return PerformanceReviewResponse(**r)
    raise HTTPException(status_code=404, detail=f"Performance review {review_id} not found")

@router.post("/performance-reviews", response_model=PerformanceReviewResponse, status_code=201)
def create_performance_review(review: PerformanceReviewCreate):
    global _next_ids
    new = review.model_dump()
    new["id"] = _next_ids["performance_reviews"]
    _next_ids["performance_reviews"] += 1
    PERFORMANCE_REVIEWS_DB.append(new)
    return PerformanceReviewResponse(**new)

@router.put("/performance-reviews/{review_id}", response_model=PerformanceReviewResponse)
def update_performance_review(review_id: int, review: PerformanceReviewUpdate):
    for idx, r in enumerate(PERFORMANCE_REVIEWS_DB):
        if r["id"] == review_id:
            PERFORMANCE_REVIEWS_DB[idx].update(review.model_dump(exclude_unset=True))
            return PerformanceReviewResponse(**PERFORMANCE_REVIEWS_DB[idx])
    raise HTTPException(status_code=404, detail=f"Performance review {review_id} not found")

@router.delete("/performance-reviews/{review_id}", status_code=204)
def delete_performance_review(review_id: int):
    for idx, r in enumerate(PERFORMANCE_REVIEWS_DB):
        if r["id"] == review_id:
            PERFORMANCE_REVIEWS_DB.pop(idx)
            return
    raise HTTPException(status_code=404, detail=f"Performance review {review_id} not found")
