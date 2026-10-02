"""Core accounting data models."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class AccountType(str, Enum):
    """Classification of general-ledger accounts."""

    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


@dataclass
class Account:
    """A general-ledger account."""

    name: str
    account_type: AccountType
    account_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    currency: str = "USD"
    parent_id: Optional[str] = None
    is_active: bool = True

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Account name cannot be empty")
        if not isinstance(self.account_type, AccountType):
            raise TypeError("account_type must be an AccountType enum")


@dataclass
class Transaction:
    """A single debit or credit against an account."""

    account_id: str
    amount: Decimal
    currency: str = "USD"
    description: str = ""
    transaction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: date = field(default_factory=date.today)
    reference: Optional[str] = None

    def __post_init__(self) -> None:
        if self.amount == 0:
            raise ValueError("Transaction amount cannot be zero")
        if not self.account_id:
            raise ValueError("account_id is required")


@dataclass
class JournalEntry:
    """A balanced double-entry journal entry."""

    transactions: list[Transaction]
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: date = field(default_factory=date.today)
    description: str = ""
    reference: Optional[str] = None

    def __post_init__(self) -> None:
        if len(self.transactions) < 2:
            raise ValueError("Journal entry must have at least two transactions")
        if not self.is_balanced():
            raise ValueError("Journal entry is not balanced (debits != credits)")

    def is_balanced(self) -> bool:
        """Return True if total debits equal total credits."""
        total = sum(t.amount for t in self.transactions)
        return total == 0

    def total_debits(self) -> Decimal:
        """Sum of all positive (debit) amounts."""
        return sum(t.amount for t in self.transactions if t.amount > 0)

    def total_credits(self) -> Decimal:
        """Sum of all negative (credit) amounts, returned as positive."""
        return -sum(t.amount for t in self.transactions if t.amount < 0)


@dataclass
class InvoiceLineItem:
    """A single line item on an invoice."""

    description: str
    quantity: Decimal
    unit_price: Decimal
    currency: str = "USD"
    discount_percent: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative")
        if self.discount_percent < 0 or self.discount_percent > 100:
            raise ValueError("Discount percent must be between 0 and 100")
        if self.tax_rate < 0:
            raise ValueError("Tax rate cannot be negative")

    @property
    def subtotal(self) -> Decimal:
        """Line total before discount and tax."""
        return self.quantity * self.unit_price

    @property
    def discount_amount(self) -> Decimal:
        """Discount applied to this line."""
        return self.subtotal * (self.discount_percent / Decimal("100"))

    @property
    def net_amount(self) -> Decimal:
        """Amount after discount, before tax."""
        return self.subtotal - self.discount_amount

    @property
    def tax_amount(self) -> Decimal:
        """Tax charged on this line."""
        return self.net_amount * (self.tax_rate / Decimal("100"))

    @property
    def total(self) -> Decimal:
        """Final line total including tax."""
        return self.net_amount + self.tax_amount


@dataclass
class Invoice:
    """A customer or vendor invoice."""

    customer_id: str
    line_items: list[InvoiceLineItem]
    invoice_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    issue_date: date = field(default_factory=date.today)
    due_date: Optional[date] = None
    currency: str = "USD"
    status: str = "draft"  # draft, sent, paid, overdue, cancelled
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.customer_id:
            raise ValueError("customer_id is required")
        if not self.line_items:
            raise ValueError("Invoice must have at least one line item")

    @property
    def subtotal(self) -> Decimal:
        """Sum of all line-item net amounts."""
        return sum(item.net_amount for item in self.line_items)

    @property
    def total_discount(self) -> Decimal:
        """Total discount across all line items."""
        return sum(item.discount_amount for item in self.line_items)

    @property
    def total_tax(self) -> Decimal:
        """Total tax across all line items."""
        return sum(item.tax_amount for item in self.line_items)

    @property
    def total(self) -> Decimal:
        """Grand total including tax."""
        return sum(item.total for item in self.line_items)

    @property
    def amount_due(self) -> Decimal:
        """Amount still outstanding."""
        if self.status == "paid":
            return Decimal("0")
        return self.total
