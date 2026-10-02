"""HR Management System for APEX-OS Business Platform.

Modules:
    employees    – Employee records & org structure
    leave        – Leave requests, balances, approvals
    payroll      – Salary calculation, payslips, deductions
    performance  – Reviews, goals, ratings
    recruitment  – Job postings, candidates, applications
"""

from .employees import Employee, EmployeeRepository, Department
from .leave import LeaveRequest, LeaveType, LeaveBalance, LeaveManager
from .payroll import PayrollRecord, Payslip, PayrollCalculator, Deduction
from .performance import PerformanceReview, Goal, ReviewCycle, Rating
from .recruitment import JobPosting, Candidate, Application, ApplicationStage

__all__ = [
    "Employee",
    "EmployeeRepository",
    "Department",
    "LeaveRequest",
    "LeaveType",
    "LeaveBalance",
    "LeaveManager",
    "PayrollRecord",
    "Payslip",
    "PayrollCalculator",
    "Deduction",
    "PerformanceReview",
    "Goal",
    "ReviewCycle",
    "Rating",
    "JobPosting",
    "Candidate",
    "Application",
    "ApplicationStage",
]
