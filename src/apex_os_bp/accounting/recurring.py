"""Recurring invoice scheduler: patterns, templates, and generation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Optional

from apex_os_bp.accounting.models import Invoice, InvoiceLineItem


class RecurrencePattern(str, Enum):
    """Supported recurrence frequencies."""

    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    YEARLY = "yearly"


_PATTERN_INTERVALS: dict[RecurrencePattern, int] = {
    RecurrencePattern.DAILY: 1,          # days
    RecurrencePattern.WEEKLY: 7,         # days
    RecurrencePattern.BIWEEKLY: 14,      # days
    RecurrencePattern.MONTHLY: 1,        # months
    RecurrencePattern.QUARTERLY: 3,      # months
    RecurrencePattern.SEMIANNUAL: 6,     # months
    RecurrencePattern.YEARLY: 12,        # months
}


def _add_months(d: date, months: int) -> date:
    """Return *d* shifted forward by *months*, clamping the day."""
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    # Clamp day to the last valid day of the target month.
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)
    last_day = (next_month_first - timedelta(days=1)).day
    day = min(d.day, last_day)
    return date(year, month, day)


@dataclass
class RecurringInvoiceTemplate:
    """A template that generates invoices on a schedule."""

    customer_id: str
    line_items: list[InvoiceLineItem]
    pattern: RecurrencePattern
    template_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_date: date = field(default_factory=date.today)
    end_date: Optional[date] = None
    max_occurrences: Optional[int] = None
    currency: str = "USD"
    notes: str = ""
    is_active: bool = True
    day_of_month: Optional[int] = None  # override for monthly+ patterns

    def __post_init__(self) -> None:
        if not self.customer_id:
            raise ValueError("customer_id is required")
        if not self.line_items:
            raise ValueError("Template must have at least one line item")
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        if self.max_occurrences is not None and self.max_occurrences < 1:
            raise ValueError("max_occurrences must be at least 1")
        if self.day_of_month is not None and not (1 <= self.day_of_month <= 31):
            raise ValueError("day_of_month must be between 1 and 31")

    @property
    def interval_days(self) -> Optional[int]:
        """Interval in days for day-based patterns, None for month-based."""
        if self.pattern in (
            RecurrencePattern.MONTHLY,
            RecurrencePattern.QUARTERLY,
            RecurrencePattern.SEMIANNUAL,
            RecurrencePattern.YEARLY,
        ):
            return None
        return _PATTERN_INTERVALS[self.pattern]

    @property
    def interval_months(self) -> Optional[int]:
        """Interval in months for month-based patterns, None for day-based."""
        if self.pattern in (
            RecurrencePattern.MONTHLY,
            RecurrencePattern.QUARTERLY,
            RecurrencePattern.SEMIANNUAL,
            RecurrencePattern.YEARLY,
        ):
            return _PATTERN_INTERVALS[self.pattern]
        return None

    def next_occurrence(self, after: date) -> Optional[date]:
        """Compute the next occurrence strictly after *after*.

        Returns ``None`` if the template has ended or reached its
        occurrence limit.
        """
        if not self.is_active:
            return None
        if self.end_date and after >= self.end_date:
            return None

        if self.interval_days is not None:
            # Day-based pattern
            delta = timedelta(days=self.interval_days)
            candidate = self.start_date
            while candidate <= after:
                candidate += delta
        else:
            # Month-based pattern
            months = self.interval_months or 1
            candidate = self.start_date
            while candidate <= after:
                candidate = _add_months(candidate, months)

        if self.end_date and candidate > self.end_date:
            return None
        return candidate

    def occurrences_between(self, start: date, end: date) -> list[date]:
        """Return all occurrence dates in [start, end]."""
        if not self.is_active:
            return []
        if self.end_date and start > self.end_date:
            return []

        effective_end = min(end, self.end_date) if self.end_date else end
        results: list[date] = []
        current = self.start_date
        count = 0

        while current <= effective_end:
            if current >= start:
                results.append(current)
                count += 1
                if self.max_occurrences and count >= self.max_occurrences:
                    break
            # Advance
            if self.interval_days is not None:
                current += timedelta(days=self.interval_days)
            else:
                current = _add_months(current, self.interval_months or 1)

        return results


@dataclass
class RecurringInvoiceScheduler:
    """Generates invoices from recurring templates."""

    def __init__(self) -> None:
        self._templates: dict[str, RecurringInvoiceTemplate] = {}

    def add_template(self, template: RecurringInvoiceTemplate) -> None:
        """Register a template."""
        self._templates[template.template_id] = template

    def remove_template(self, template_id: str) -> None:
        """Remove a template by ID."""
        self._templates.pop(template_id, None)

    def get_template(self, template_id: str) -> RecurringInvoiceTemplate:
        """Retrieve a template by ID."""
        if template_id not in self._templates:
            raise KeyError(f"Template '{template_id}' not found")
        return self._templates[template_id]

    @property
    def templates(self) -> list[RecurringInvoiceTemplate]:
        """All registered templates."""
        return list(self._templates.values())

    def generate_invoice(
        self,
        template_id: str,
        occurrence_date: Optional[date] = None,
    ) -> Invoice:
        """Generate a single invoice from a template."""
        template = self.get_template(template_id)
        issue_date = occurrence_date or date.today()
        return Invoice(
            customer_id=template.customer_id,
            line_items=[
                InvoiceLineItem(
                    description=li.description,
                    quantity=li.quantity,
                    unit_price=li.unit_price,
                    currency=template.currency,
                    discount_percent=li.discount_percent,
                    tax_rate=li.tax_rate,
                )
                for li in template.line_items
            ],
            issue_date=issue_date,
            currency=template.currency,
            status="draft",
            notes=template.notes,
        )

    def generate_up_to(
        self,
        template_id: str,
        up_to_date: date,
    ) -> list[Invoice]:
        """Generate all invoices due on or before *up_to_date*."""
        template = self.get_template(template_id)
        occurrences = template.occurrences_between(template.start_date, up_to_date)
        return [self.generate_invoice(template_id, d) for d in occurrences]

    def generate_all_up_to(self, up_to_date: date) -> list[Invoice]:
        """Generate invoices from all active templates up to *up_to_date*."""
        invoices: list[Invoice] = []
        for template in self._templates.values():
            if template.is_active:
                invoices.extend(self.generate_up_to(template.template_id, up_to_date))
        return invoices
