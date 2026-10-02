"""Leave management: requests, balances, approvals."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Optional


class LeaveType(str, Enum):
    ANNUAL = "annual"
    SICK = "sick"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    UNPAID = "unpaid"
    BEREAVEMENT = "bereavement"


class LeaveStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class LeaveBalance:
    """Tracks remaining leave days per type for an employee."""

    employee_id: str
    year: int
    balances: dict[LeaveType, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Default annual entitlement if not specified
        if LeaveType.ANNUAL not in self.balances:
            self.balances[LeaveType.ANNUAL] = 20.0
        if LeaveType.SICK not in self.balances:
            self.balances[LeaveType.SICK] = 10.0

    def get_balance(self, leave_type: LeaveType) -> float:
        return self.balances.get(leave_type, 0.0)

    def deduct(self, leave_type: LeaveType, days: float) -> None:
        current = self.get_balance(leave_type)
        if days > current:
            raise ValueError(
                f"Insufficient {leave_type.value} leave: {current} available, {days} requested"
            )
        self.balances[leave_type] = current - days

    def add(self, leave_type: LeaveType, days: float) -> None:
        current = self.get_balance(leave_type)
        self.balances[leave_type] = current + days


@dataclass
class LeaveRequest:
    """A single leave request."""

    id: str
    employee_id: str
    leave_type: LeaveType
    start_date: date
    end_date: date
    status: LeaveStatus = LeaveStatus.PENDING
    reason: Optional[str] = None
    approver_id: Optional[str] = None
    approved_date: Optional[date] = None

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date")

    @property
    def duration_days(self) -> int:
        """Business days (Mon–Fri) between start and end inclusive."""
        days = 0
        current = self.start_date
        while current <= self.end_date:
            if current.weekday() < 5:  # Mon=0 … Fri=4
                days += 1
            current += timedelta(days=1)
        return days

    def approve(self, approver_id: str) -> None:
        self.status = LeaveStatus.APPROVED
        self.approver_id = approver_id
        self.approved_date = date.today()

    def reject(self, approver_id: str) -> None:
        self.status = LeaveStatus.REJECTED
        self.approver_id = approver_id

    def cancel(self) -> None:
        if self.status == LeaveStatus.APPROVED:
            raise ValueError("Cannot cancel an approved leave request")
        self.status = LeaveStatus.CANCELLED

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "leave_type": self.leave_type.value,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "duration_days": self.duration_days,
            "status": self.status.value,
            "reason": self.reason,
            "approver_id": self.approver_id,
            "approved_date": self.approved_date.isoformat() if self.approved_date else None,
        }


class LeaveManager:
    """Manages leave requests and balances."""

    def __init__(self) -> None:
        self._requests: dict[str, LeaveRequest] = {}
        self._balances: dict[tuple[str, int], LeaveBalance] = {}

    def _get_balance(self, employee_id: str, year: int) -> LeaveBalance:
        key = (employee_id, year)
        if key not in self._balances:
            self._balances[key] = LeaveBalance(employee_id=employee_id, year=year)
        return self._balances[key]

    def get_balance(self, employee_id: str, year: Optional[int] = None) -> LeaveBalance:
        if year is None:
            year = date.today().year
        return self._get_balance(employee_id, year)

    def set_entitlement(
        self, employee_id: str, leave_type: LeaveType, days: float, year: Optional[int] = None
    ) -> None:
        if year is None:
            year = date.today().year
        bal = self._get_balance(employee_id, year)
        bal.balances[leave_type] = days

    def submit_request(self, request: LeaveRequest) -> LeaveRequest:
        if request.id in self._requests:
            raise ValueError(f"Leave request {request.id} already exists")
        # Check balance for the year of the start date
        bal = self._get_balance(request.employee_id, request.start_date.year)
        if request.leave_type != LeaveType.UNPAID:
            if request.duration_days > bal.get_balance(request.leave_type):
                raise ValueError(
                    f"Insufficient {request.leave_type.value} leave balance"
                )
        self._requests[request.id] = request
        return request

    def approve_request(self, request_id: str, approver_id: str) -> LeaveRequest:
        req = self._requests.get(request_id)
        if req is None:
            raise KeyError(f"Leave request {request_id} not found")
        req.approve(approver_id)
        # Deduct balance
        if req.leave_type != LeaveType.UNPAID:
            bal = self._get_balance(req.employee_id, req.start_date.year)
            bal.deduct(req.leave_type, req.duration_days)
        return req

    def reject_request(self, request_id: str, approver_id: str) -> LeaveRequest:
        req = self._requests.get(request_id)
        if req is None:
            raise KeyError(f"Leave request {request_id} not found")
        req.reject(approver_id)
        return req

    def cancel_request(self, request_id: str) -> LeaveRequest:
        req = self._requests.get(request_id)
        if req is None:
            raise KeyError(f"Leave request {request_id} not found")
        req.cancel()
        return req

    def get_request(self, request_id: str) -> Optional[LeaveRequest]:
        return self._requests.get(request_id)

    def list_requests(
        self,
        employee_id: Optional[str] = None,
        status: Optional[LeaveStatus] = None,
    ) -> list[LeaveRequest]:
        results = list(self._requests.values())
        if employee_id:
            results = [r for r in results if r.employee_id == employee_id]
        if status:
            results = [r for r in results if r.status == status]
        return results

    def get_pending_requests(self) -> list[LeaveRequest]:
        return self.list_requests(status=LeaveStatus.PENDING)
