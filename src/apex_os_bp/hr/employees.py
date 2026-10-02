"""Employee records and organisational structure."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class EmploymentStatus(str, Enum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


@dataclass
class Department:
    """A department within the organisation."""

    id: str
    name: str
    manager_id: Optional[str] = None
    cost_center: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Department id is required")
        if not self.name:
            raise ValueError("Department name is required")


@dataclass
class Employee:
    """Core employee record."""

    id: str
    first_name: str
    last_name: str
    email: str
    department_id: str
    job_title: str
    hire_date: date
    salary: float
    status: EmploymentStatus = EmploymentStatus.ACTIVE
    manager_id: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Employee id is required")
        if not self.first_name or not self.last_name:
            raise ValueError("First and last name are required")
        if "@" not in self.email:
            raise ValueError("Invalid email address")
        if self.salary < 0:
            raise ValueError("Salary cannot be negative")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def tenure_years(self) -> float:
        """Years of service rounded to one decimal."""
        delta = date.today() - self.hire_date
        return round(delta.days / 365.25, 1)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "email": self.email,
            "department_id": self.department_id,
            "job_title": self.job_title,
            "hire_date": self.hire_date.isoformat(),
            "salary": self.salary,
            "status": self.status.value,
            "manager_id": self.manager_id,
            "phone": self.phone,
            "address": self.address,
            "tenure_years": self.tenure_years,
        }


class EmployeeRepository:
    """In-memory repository for employee records."""

    def __init__(self) -> None:
        self._employees: dict[str, Employee] = {}
        self._departments: dict[str, Department] = {}

    # ── Department operations ────────────────────────────────────────

    def add_department(self, dept: Department) -> Department:
        if dept.id in self._departments:
            raise ValueError(f"Department {dept.id} already exists")
        self._departments[dept.id] = dept
        return dept

    def get_department(self, dept_id: str) -> Optional[Department]:
        return self._departments.get(dept_id)

    def list_departments(self) -> list[Department]:
        return list(self._departments.values())

    # ── Employee CRUD ────────────────────────────────────────────────

    def add_employee(self, emp: Employee) -> Employee:
        if emp.id in self._employees:
            raise ValueError(f"Employee {emp.id} already exists")
        if emp.department_id not in self._departments:
            raise ValueError(f"Department {emp.department_id} does not exist")
        self._employees[emp.id] = emp
        return emp

    def get_employee(self, emp_id: str) -> Optional[Employee]:
        return self._employees.get(emp_id)

    def update_employee(self, emp_id: str, **kwargs) -> Employee:
        emp = self._employees.get(emp_id)
        if emp is None:
            raise KeyError(f"Employee {emp_id} not found")
        for key, value in kwargs.items():
            if hasattr(emp, key):
                setattr(emp, key, value)
            else:
                raise AttributeError(f"Employee has no attribute {key}")
        return emp

    def remove_employee(self, emp_id: str) -> None:
        if emp_id not in self._employees:
            raise KeyError(f"Employee {emp_id} not found")
        del self._employees[emp_id]

    def list_employees(
        self,
        department_id: Optional[str] = None,
        status: Optional[EmploymentStatus] = None,
    ) -> list[Employee]:
        results = list(self._employees.values())
        if department_id:
            results = [e for e in results if e.department_id == department_id]
        if status:
            results = [e for e in results if e.status == status]
        return results

    def search(self, query: str) -> list[Employee]:
        """Search by name, email, or job title (case-insensitive)."""
        q = query.lower()
        return [
            e
            for e in self._employees.values()
            if q in e.full_name.lower()
            or q in e.email.lower()
            or q in e.job_title.lower()
        ]

    def get_subordinates(self, manager_id: str) -> list[Employee]:
        return [e for e in self._employees.values() if e.manager_id == manager_id]

    def count(self) -> int:
        return len(self._employees)
