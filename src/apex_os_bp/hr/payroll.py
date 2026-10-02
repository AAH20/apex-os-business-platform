"""Payroll: salary calculation, payslips, deductions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class PayFrequency(str, Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


@dataclass
class Deduction:
    """A single deduction line item."""

    name: str
    amount: float
    is_percentage: bool = False
    is_pretax: bool = True

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Deduction amount cannot be negative")


@dataclass
class Payslip:
    """A payslip for one pay period."""

    employee_id: str
    period_start: date
    period_end: date
    gross_pay: float
    deductions: list[Deduction] = field(default_factory=list)
    net_pay: float = 0.0
    pay_date: Optional[date] = None

    def __post_init__(self) -> None:
        if self.period_end < self.period_start:
            raise ValueError("Period end cannot be before period start")
        if not self.net_pay:
            self.net_pay = self.calculate_net()

    def calculate_net(self) -> float:
        total_deductions = sum(d.amount for d in self.deductions)
        return round(self.gross_pay - total_deductions, 2)

    def to_dict(self) -> dict:
        return {
            "employee_id": self.employee_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "gross_pay": self.gross_pay,
            "deductions": [
                {
                    "name": d.name,
                    "amount": d.amount,
                    "is_percentage": d.is_percentage,
                    "is_pretax": d.is_pretax,
                }
                for d in self.deductions
            ],
            "net_pay": self.net_pay,
            "pay_date": self.pay_date.isoformat() if self.pay_date else None,
        }


class PayrollCalculator:
    """Calculates gross pay, deductions, and net pay."""

    # Default tax brackets (simplified progressive)
    TAX_BRACKETS: list[tuple[float, float]] = [
        (0, 12_570, 0.0),
        (12_570, 50_270, 0.20),
        (50_270, 125_140, 0.40),
        (125_140, float("inf"), 0.45),
    ]

    NI_RATE = 0.08  # Simplified National Insurance rate
    PENSION_RATE = 0.05  # Employee pension contribution

    def __init__(self) -> None:
        self._payslips: dict[str, list[Payslip]] = {}

    def calculate_income_tax(self, annual_salary: float) -> float:
        """Calculate annual income tax using progressive brackets."""
        tax = 0.0
        remaining = annual_salary
        for lower, upper, rate in self.TAX_BRACKETS:
            taxable = min(remaining, upper - lower)
            if taxable <= 0:
                break
            tax += taxable * rate
            remaining -= taxable
        return round(tax, 2)

    def calculate_ni(self, gross_pay: float) -> float:
        """National Insurance contribution per pay period."""
        return round(gross_pay * self.NI_RATE, 2)

    def calculate_pension(self, gross_pay: float) -> float:
        """Employee pension contribution per pay period."""
        return round(gross_pay * self.PENSION_RATE, 2)

    def gross_per_period(self, annual_salary: float, frequency: PayFrequency) -> float:
        """Gross pay for one pay period."""
        periods = {
            PayFrequency.WEEKLY: 52,
            PayFrequency.BIWEEKLY: 26,
            PayFrequency.MONTHLY: 12,
        }
        return round(annual_salary / periods[frequency], 2)

    def generate_payslip(
        self,
        employee_id: str,
        annual_salary: float,
        period_start: date,
        period_end: date,
        frequency: PayFrequency = PayFrequency.MONTHLY,
        extra_deductions: Optional[list[Deduction]] = None,
        pay_date: Optional[date] = None,
    ) -> Payslip:
        """Generate a payslip with standard deductions."""
        gross = self.gross_per_period(annual_salary, frequency)

        # Income tax per period
        annual_tax = self.calculate_income_tax(annual_salary)
        periods = {PayFrequency.WEEKLY: 52, PayFrequency.BIWEEKLY: 26, PayFrequency.MONTHLY: 12}
        tax_per_period = round(annual_tax / periods[frequency], 2)

        ni = self.calculate_ni(gross)
        pension = self.calculate_pension(gross)

        deductions: list[Deduction] = [
            Deduction(name="Income Tax", amount=tax_per_period),
            Deduction(name="National Insurance", amount=ni),
            Deduction(name="Pension", amount=pension),
        ]
        if extra_deductions:
            deductions.extend(extra_deductions)

        payslip = Payslip(
            employee_id=employee_id,
            period_start=period_start,
            period_end=period_end,
            gross_pay=gross,
            deductions=deductions,
            pay_date=pay_date,
        )

        # Store
        if employee_id not in self._payslips:
            self._payslips[employee_id] = []
        self._payslips[employee_id].append(payslip)

        return payslip

    def get_payslips(self, employee_id: str) -> list[Payslip]:
        return self._payslips.get(employee_id, [])

    def get_latest_payslip(self, employee_id: str) -> Optional[Payslip]:
        slips = self._payslips.get(employee_id, [])
        return slips[-1] if slips else None

    def ytd_gross(self, employee_id: str) -> float:
        """Year-to-date gross pay."""
        return round(sum(s.gross_pay for s in self._payslips.get(employee_id, [])), 2)

    def ytd_tax(self, employee_id: str) -> float:
        """Year-to-date tax deducted."""
        total = 0.0
        for slip in self._payslips.get(employee_id, []):
            for d in slip.deductions:
                if d.name == "Income Tax":
                    total += d.amount
        return round(total, 2)

    def ytd_net(self, employee_id: str) -> float:
        """Year-to-date net pay."""
        return round(sum(s.net_pay for s in self._payslips.get(employee_id, [])), 2)


@dataclass
class PayrollRecord:
    """Summary record for a payroll run."""

    run_date: date
    total_gross: float
    total_tax: float
    total_ni: float
    total_net: float
    employee_count: int

    def to_dict(self) -> dict:
        return {
            "run_date": self.run_date.isoformat(),
            "total_gross": self.total_gross,
            "total_tax": self.total_tax,
            "total_ni": self.total_ni,
            "total_net": self.total_net,
            "employee_count": self.employee_count,
        }
