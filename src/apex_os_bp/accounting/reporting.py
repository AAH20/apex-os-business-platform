"""Financial reporting: P&L, Balance Sheet, and Cash Flow statements."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from apex_os_bp.accounting.models import AccountType, JournalEntry, Transaction


@dataclass(frozen=True)
class ReportPeriod:
    """An inclusive date range for a financial report."""

    start_date: date
    end_date: date
    label: str = ""

    def __post_init__(self) -> None:
        if self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date")

    @property
    def display_label(self) -> str:
        """Human-readable period label."""
        if self.label:
            return self.label
        return f"{self.start_date.isoformat()} → {self.end_date.isoformat()}"

    def contains(self, d: date) -> bool:
        """Return True if *d* falls within the period."""
        return self.start_date <= d <= self.end_date


@dataclass
class ReportLineItem:
    """A single line on a financial statement."""

    account_id: str
    account_name: str
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if isinstance(self.amount, (int, float)):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))


@dataclass
class FinancialReport:
    """Base class for financial statements."""

    period: ReportPeriod
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: date = field(default_factory=date.today)
    currency: str = "USD"
    line_items: list[ReportLineItem] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        """Sum of all line-item amounts."""
        return sum(item.amount for item in self.line_items)


@dataclass
class ProfitAndLoss(FinancialReport):
    """Income statement: revenue minus expenses."""

    @property
    def total_revenue(self) -> Decimal:
        """Sum of all revenue line items."""
        return sum(
            item.amount for item in self.line_items
            if item.account_id.startswith("REV")
        )

    @property
    def total_expenses(self) -> Decimal:
        """Sum of all expense line items (as a positive number)."""
        return -sum(
            item.amount for item in self.line_items
            if item.account_id.startswith("EXP")
        )

    @property
    def gross_profit(self) -> Decimal:
        """Revenue minus cost of goods sold (if COGS accounts exist)."""
        cogs = sum(
            item.amount for item in self.line_items
            if item.account_id.startswith("COGS")
        )
        return self.total_revenue + cogs  # cogs amounts are negative

    @property
    def net_income(self) -> Decimal:
        """Bottom-line profit (revenue + expenses, expenses are negative)."""
        return self.total_revenue - self.total_expenses

    @property
    def is_profitable(self) -> bool:
        """True if net income is positive."""
        return self.net_income > 0

    @property
    def profit_margin(self) -> Optional[Decimal]:
        """Net income as a percentage of revenue, or None if no revenue."""
        if self.total_revenue == 0:
            return None
        return (self.net_income / self.total_revenue * Decimal("100")).quantize(
            Decimal("0.01")
        )


@dataclass
class BalanceSheet(FinancialReport):
    """Statement of financial position: assets = liabilities + equity."""

    @property
    def total_assets(self) -> Decimal:
        """Sum of all asset line items."""
        return sum(
            item.amount for item in self.line_items
            if item.account_id.startswith("AST")
        )

    @property
    def total_liabilities(self) -> Decimal:
        """Sum of all liability line items (as a positive number)."""
        return -sum(
            item.amount for item in self.line_items
            if item.account_id.startswith("LIA")
        )

    @property
    def total_equity(self) -> Decimal:
        """Sum of all equity line items."""
        return sum(
            item.amount for item in self.line_items
            if item.account_id.startswith("EQY")
        )

    @property
    def is_balanced(self) -> bool:
        """True if assets = liabilities + equity."""
        return self.total_assets == (self.total_liabilities + self.total_equity)

    @property
    def working_capital(self) -> Decimal:
        """Current assets minus current liabilities (approximation)."""
        return self.total_assets - self.total_liabilities

    @property
    def debt_to_equity(self) -> Optional[Decimal]:
        """Liabilities / equity ratio, or None if equity is zero."""
        if self.total_equity == 0:
            return None
        return (self.total_liabilities / self.total_equity).quantize(Decimal("0.01"))

    @property
    def current_ratio(self) -> Optional[Decimal]:
        """Assets / liabilities ratio, or None if liabilities are zero."""
        if self.total_liabilities == 0:
            return None
        return (self.total_assets / self.total_liabilities).quantize(Decimal("0.01"))


@dataclass
class CashFlowStatement(FinancialReport):
    """Statement of cash flows: operating, investing, financing."""

    @property
    def operating_cash_flow(self) -> Decimal:
        """Net cash from operating activities."""
        return sum(
            item.amount for item in self.line_items
            if item.account_id.startswith("OCF")
        )

    @property
    def investing_cash_flow(self) -> Decimal:
        """Net cash from investing activities."""
        return sum(
            item.amount for item in self.line_items
            if item.account_id.startswith("ICF")
        )

    @property
    def financing_cash_flow(self) -> Decimal:
        """Net cash from financing activities."""
        return sum(
            item.amount for item in self.line_items
            if item.account_id.startswith("FCF")
        )

    @property
    def net_cash_flow(self) -> Decimal:
        """Total change in cash across all activities."""
        return self.operating_cash_flow + self.investing_cash_flow + self.financing_cash_flow

    @property
    def is_cash_positive(self) -> bool:
        """True if net cash flow is positive."""
        return self.net_cash_flow > 0

    @property
    def free_cash_flow(self) -> Decimal:
        """Operating cash flow minus capital expenditures (approximation)."""
        capex = sum(
            item.amount for item in self.line_items
            if item.account_id.startswith("CAPEX")
        )
        return self.operating_cash_flow + capex  # capex amounts are negative


class ReportGenerator:
    """Generate financial reports from journal entries."""

    def __init__(self, currency: str = "USD") -> None:
        self.currency = currency
        self._entries: list[JournalEntry] = []

    def add_entry(self, entry: JournalEntry) -> None:
        """Add a journal entry."""
        self._entries.append(entry)

    def add_entries(self, entries: list[JournalEntry]) -> None:
        """Bulk-add journal entries."""
        self._entries.extend(entries)

    def _filter_entries(self, period: ReportPeriod) -> list[JournalEntry]:
        """Return entries whose date falls within *period*."""
        return [e for e in self._entries if period.contains(e.date)]

    def _aggregate_by_account(
        self,
        entries: list[JournalEntry],
        account_prefix: str,
    ) -> list[ReportLineItem]:
        """Sum transactions by account, filtered by ID prefix."""
        totals: dict[str, Decimal] = {}
        names: dict[str, str] = {}
        for entry in entries:
            for txn in entry.transactions:
                if txn.account_id.startswith(account_prefix):
                    totals[txn.account_id] = totals.get(txn.account_id, Decimal("0")) + txn.amount
                    names[txn.account_id] = txn.account_id  # fallback name
        return [
            ReportLineItem(
                account_id=acct_id,
                account_name=names.get(acct_id, acct_id),
                amount=amount,
                currency=self.currency,
            )
            for acct_id, amount in sorted(totals.items())
        ]

    def generate_profit_and_loss(self, period: ReportPeriod) -> ProfitAndLoss:
        """Generate a P&L statement for *period*."""
        entries = self._filter_entries(period)
        line_items: list[ReportLineItem] = []

        # Revenue accounts (credit balances → negative in double-entry)
        revenue_items = self._aggregate_by_account(entries, "REV")
        for item in revenue_items:
            line_items.append(ReportLineItem(
                account_id=item.account_id,
                account_name=item.account_name,
                amount=-item.amount,  # flip sign: credits are negative
                currency=self.currency,
            ))

        # Expense accounts (debit balances → positive in double-entry)
        expense_items = self._aggregate_by_account(entries, "EXP")
        for item in expense_items:
            line_items.append(ReportLineItem(
                account_id=item.account_id,
                account_name=item.account_name,
                amount=-item.amount,  # flip sign: debits are positive
                currency=self.currency,
            ))

        return ProfitAndLoss(
            period=period,
            currency=self.currency,
            line_items=line_items,
        )

    def generate_balance_sheet(self, period: ReportPeriod) -> BalanceSheet:
        """Generate a balance sheet as of *period.end_date*."""
        # Balance sheet uses all entries up to the end date
        entries = [e for e in self._entries if e.date <= period.end_date]
        line_items: list[ReportLineItem] = []

        for prefix, sign in (("AST", 1), ("LIA", 1), ("EQY", -1)):
            items = self._aggregate_by_account(entries, prefix)
            for item in items:
                line_items.append(ReportLineItem(
                    account_id=item.account_id,
                    account_name=item.account_name,
                    amount=item.amount * sign,
                    currency=self.currency,
                ))

        return BalanceSheet(
            period=period,
            currency=self.currency,
            line_items=line_items,
        )

    def generate_cash_flow(self, period: ReportPeriod) -> CashFlowStatement:
        """Generate a cash flow statement for *period*."""
        entries = self._filter_entries(period)
        line_items: list[ReportLineItem] = []

        for prefix in ("OCF", "ICF", "FCF", "CAPEX"):
            items = self._aggregate_by_account(entries, prefix)
            for item in items:
                line_items.append(ReportLineItem(
                    account_id=item.account_id,
                    account_name=item.account_name,
                    amount=item.amount,
                    currency=self.currency,
                ))

        return CashFlowStatement(
            period=period,
            currency=self.currency,
            line_items=line_items,
        )

    def generate_all(
        self,
        period: ReportPeriod,
    ) -> tuple[ProfitAndLoss, BalanceSheet, CashFlowStatement]:
        """Generate all three statements for *period*."""
        return (
            self.generate_profit_and_loss(period),
            self.generate_balance_sheet(period),
            self.generate_cash_flow(period),
        )
