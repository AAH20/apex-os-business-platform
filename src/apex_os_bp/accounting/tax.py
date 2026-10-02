"""Tax calculation engine: rates, rules, and line-item tax computation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional


class TaxType(str, Enum):
    """Common tax categories."""

    VAT = "vat"
    SALES_TAX = "sales_tax"
    GST = "gst"
    INCOME_TAX = "income_tax"
    CORPORATE_TAX = "corporate_tax"
    WITHHOLDING = "withholding"
    CUSTOMS_DUTY = "customs_duty"
    EXCISE = "excise"
    OTHER = "other"


@dataclass
class TaxRate:
    """A named tax rate within a jurisdiction."""

    name: str
    rate: Decimal
    tax_type: TaxType
    jurisdiction: str
    rate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    is_active: bool = True
    description: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.rate, (int, float)):
            object.__setattr__(self, "rate", Decimal(str(self.rate)))
        if self.rate < 0:
            raise ValueError("Tax rate cannot be negative")
        if not self.name or not self.name.strip():
            raise ValueError("Tax rate name cannot be empty")
        if not self.jurisdiction or not self.jurisdiction.strip():
            raise ValueError("Jurisdiction cannot be empty")

    def is_effective_on(self, on_date: date) -> bool:
        """Return True if this rate is effective on *on_date*."""
        if self.effective_from and on_date < self.effective_from:
            return False
        if self.effective_to and on_date > self.effective_to:
            return False
        return self.is_active

    def apply(self, amount: Decimal) -> Decimal:
        """Return the tax on *amount* at this rate."""
        return (amount * self.rate / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )


@dataclass
class TaxRule:
    """A conditional rule that selects a tax rate."""

    name: str
    tax_rate: TaxRate
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    product_category: Optional[str] = None
    customer_category: Optional[str] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    priority: int = 0
    is_active: bool = True

    def matches(
        self,
        amount: Decimal,
        product_category: Optional[str] = None,
        customer_category: Optional[str] = None,
    ) -> bool:
        """Return True if this rule applies to the given context."""
        if not self.is_active:
            return False
        if self.product_category and product_category != self.product_category:
            return False
        if self.customer_category and customer_category != self.customer_category:
            return False
        if self.min_amount is not None and amount < self.min_amount:
            return False
        if self.max_amount is not None and amount > self.max_amount:
            return False
        return True


@dataclass
class TaxLineItem:
    """Tax breakdown for a single invoice line."""

    line_description: str
    taxable_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    tax_name: str = ""
    tax_type: TaxType = TaxType.OTHER
    jurisdiction: str = ""

    @property
    def total_with_tax(self) -> Decimal:
        """Taxable amount plus tax."""
        return self.taxable_amount + self.tax_amount


class TaxEngine:
    """Calculate tax on amounts using registered rates and rules."""

    def __init__(self) -> None:
        self._rates: dict[str, TaxRate] = {}
        self._rules: list[TaxRule] = []

    # -- registration -------------------------------------------------------

    def register_rate(self, rate: TaxRate) -> None:
        """Add a tax rate to the engine."""
        self._rates[rate.rate_id] = rate

    def register_rule(self, rule: TaxRule) -> None:
        """Add a tax rule to the engine."""
        self._rules.append(rule)

    def remove_rate(self, rate_id: str) -> None:
        """Remove a tax rate by ID."""
        self._rates.pop(rate_id, None)

    def remove_rule(self, rule_id: str) -> None:
        """Remove a tax rule by ID."""
        self._rules = [r for r in self._rules if r.rule_id != rule_id]

    @property
    def rates(self) -> list[TaxRate]:
        """All registered tax rates."""
        return list(self._rates.values())

    @property
    def rules(self) -> list[TaxRule]:
        """All registered tax rules."""
        return list(self._rules)

    # -- lookup -------------------------------------------------------------

    def get_rate(self, rate_id: str) -> TaxRate:
        """Retrieve a tax rate by ID."""
        if rate_id not in self._rates:
            raise KeyError(f"Tax rate '{rate_id}' not found")
        return self._rates[rate_id]

    def find_rates(
        self,
        jurisdiction: Optional[str] = None,
        tax_type: Optional[TaxType] = None,
        on_date: Optional[date] = None,
    ) -> list[TaxRate]:
        """Find rates matching the given filters."""
        results: list[TaxRate] = []
        for rate in self._rates.values():
            if jurisdiction and rate.jurisdiction != jurisdiction:
                continue
            if tax_type and rate.tax_type != tax_type:
                continue
            if on_date and not rate.is_effective_on(on_date):
                continue
            results.append(rate)
        return results

    # -- calculation --------------------------------------------------------

    def calculate_tax(
        self,
        amount: Decimal,
        rate_id: str,
    ) -> TaxLineItem:
        """Calculate tax on *amount* using a specific rate."""
        rate = self.get_rate(rate_id)
        tax_amount = rate.apply(amount)
        return TaxLineItem(
            line_description=f"Tax at {rate.name}",
            taxable_amount=amount,
            tax_rate=rate.rate,
            tax_amount=tax_amount,
            tax_name=rate.name,
            tax_type=rate.tax_type,
            jurisdiction=rate.jurisdiction,
        )

    def calculate_with_rules(
        self,
        amount: Decimal,
        product_category: Optional[str] = None,
        customer_category: Optional[str] = None,
        on_date: Optional[date] = None,
    ) -> list[TaxLineItem]:
        """Calculate tax by applying all matching rules.

        Rules are evaluated in priority order (highest first).  Each
        matching rule contributes a :class:`TaxLineItem`.
        """
        if on_date is None:
            on_date = date.today()

        matching = [
            r for r in self._rules
            if r.matches(amount, product_category, customer_category)
            and r.tax_rate.is_effective_on(on_date)
        ]
        matching.sort(key=lambda r: r.priority, reverse=True)

        results: list[TaxLineItem] = []
        for rule in matching:
            tax_amount = rule.tax_rate.apply(amount)
            results.append(
                TaxLineItem(
                    line_description=f"Tax via rule '{rule.name}'",
                    taxable_amount=amount,
                    tax_rate=rule.tax_rate.rate,
                    tax_amount=tax_amount,
                    tax_name=rule.tax_rate.name,
                    tax_type=rule.tax_rate.tax_type,
                    jurisdiction=rule.tax_rate.jurisdiction,
                )
            )
        return results

    def calculate_total_tax(
        self,
        amount: Decimal,
        rate_id: str,
    ) -> Decimal:
        """Return only the tax amount for *amount* at *rate_id*."""
        return self.calculate_tax(amount, rate_id).tax_amount

    def calculate_with_tax(
        self,
        amount: Decimal,
        rate_id: str,
    ) -> Decimal:
        """Return *amount* plus tax."""
        line = self.calculate_tax(amount, rate_id)
        return line.total_with_tax

    def reverse_calculate(
        self,
        total_with_tax: Decimal,
        rate_id: str,
    ) -> tuple[Decimal, Decimal]:
        """Given a gross amount, return (net, tax).

        Useful when the quoted price already includes tax.
        """
        rate = self.get_rate(rate_id)
        # net = gross / (1 + rate/100)
        net = (total_with_tax / (Decimal("1") + rate.rate / Decimal("100"))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        tax = (total_with_tax - net).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return net, tax
