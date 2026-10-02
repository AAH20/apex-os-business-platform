#!/usr/bin/env python3
"""HR Demo: employee creation, role assignment, payroll, attendance, reporting."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List


@dataclass
class Employee:
    id: int
    name: str
    role: str = "Unassigned"
    salary: float = 0.0
    attendance: List[str] = field(default_factory=list)


class HRSystem:
    def __init__(self):
        self.employees: List[Employee] = []
        self._next_id = 1

    def create_employee(self, name: str, salary: float) -> Employee:
        emp = Employee(id=self._next_id, name=name, salary=salary)
        self.employees.append(emp)
        self._next_id += 1
        print(f"[CREATE] Employee #{emp.id}: {name} (salary=${salary:,.2f})")
        return emp

    def assign_role(self, emp_id: int, role: str) -> None:
        emp = self._find(emp_id)
        emp.role = role
        print(f"[ROLE]   Employee #{emp_id} ({emp.name}) assigned role: {role}")

    def process_payroll(self, emp_id: int) -> float:
        emp = self._find(emp_id)
        net = emp.salary * 0.85  # 15% tax deduction
        print(f"[PAYROLL] Employee #{emp_id} ({emp.name}): gross=${emp.salary:,.2f}, net=${net:,.2f}")
        return net

    def track_attendance(self, emp_id: int, days: int = 5) -> None:
        emp = self._find(emp_id)
        today = date.today()
        emp.attendance = [(today - timedelta(days=i)).isoformat() for i in range(days)]
        print(f"[ATTEND] Employee #{emp_id} ({emp.name}): {days} days logged")

    def generate_report(self) -> None:
        print("\n" + "=" * 50)
        print("HR REPORT")
        print("=" * 50)
        for emp in self.employees:
            days_present = len(emp.attendance)
            print(f"  #{emp.id} {emp.name:<15} | Role: {emp.role:<12} | "
                  f"Days Present: {days_present}")
        print("=" * 50)
        print(f"Total employees: {len(self.employees)}")

    def _find(self, emp_id: int) -> Employee:
        for emp in self.employees:
            if emp.id == emp_id:
                return emp
        raise ValueError(f"Employee #{emp_id} not found")


def main():
    hr = HRSystem()

    # 1. Create employees
    alice = hr.create_employee("Alice Chen", 75000.0)
    bob = hr.create_employee("Bob Martinez", 62000.0)

    # 2. Assign roles
    hr.assign_role(alice.id, "Senior Engineer")
    hr.assign_role(bob.id, "Product Manager")

    # 3. Process payroll
    hr.process_payroll(alice.id)
    hr.process_payroll(bob.id)

    # 4. Track attendance
    hr.track_attendance(alice.id, days=5)
    hr.track_attendance(bob.id, days=4)

    # 5. Generate report
    hr.generate_report()


if __name__ == "__main__":
    main()
