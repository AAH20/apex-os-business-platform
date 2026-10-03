"""Deepened accounting: multi-currency, recurring entries, statements, budget, tax."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional

D = Decimal
CENT = D("0.01")


def _d(v) -> Decimal:
    return D(str(v)).quantize(CENT, rounding=ROUND_HALF_UP)


# ── Multi-currency ──────────────────────────────────────────────────────────

@dataclass
class ExchangeRate:
    base: str
    quote: str
    rate: Decimal
    effective_date: date

    def convert(self, amount: Decimal, target: str) -> Decimal:
        if target == self.quote:
            return _d(amount * self.rate)
        if target == self.base:
            return _d(amount / self.rate)
        raise ValueError(f"Cannot convert via {self.base}/{self.quote} to {target}")


class CurrencyLedger:
    """Tracks balances per currency with exchange-rate history."""

    def __init__(self, base_currency: str = "USD"):
        self.base = base_currency
        self._rates: Dict[str, ExchangeRate] = {}  # pair → latest rate
        self._balances: Dict[str, Decimal] = {}

    def set_rate(self, base: str, quote: str, rate, effective_date: date = None):
        self._rates[f"{base}/{quote}"] = ExchangeRate(base, quote, _d(rate), effective_date or date.today())

    def post(self, currency: str, amount, rate_to_base: Decimal = None):
        amt = _d(amount)
        self._balances[currency] = self._balances.get(currency, D("0")) + amt
        if rate_to_base is not None and currency != self.base:
            self.set_rate(currency, self.base, rate_to_base)

    def balance(self, currency: str) -> Decimal:
        return self._balances.get(currency, D("0"))

    def balance_in_base(self, currency: str) -> Decimal:
        bal = self.balance(currency)
        if currency == self.base:
            return bal
        rate = self._rates.get(f"{currency}/{self.base}")
        if rate is None:
            raise ValueError(f"No exchange rate for {currency}→{self.base}")
        return rate.convert(bal, self.base)


# ── Recurring journal entries ────────────────────────────────────────────────

class Frequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class RecurringEntry:
    entry_id: str
    description: str
    lines: List[Dict]  # [{account, debit, credit, currency}]
    frequency: Frequency
    start_date: date
    end_date: Optional[date] = None
    last_posted: Optional[date] = None
    active: bool = True

    def next_due(self) -> Optional[date]:
        if not self.active:
            return None
        if self.end_date and date.today() > self.end_date:
            return None
        if self.last_posted is None:
            return self.start_date
        delta = {
            Frequency.DAILY: timedelta(days=1),
            Frequency.WEEKLY: timedelta(weeks=1),
            Frequency.MONTHLY: timedelta(days=30),
            Frequency.QUARTERLY: timedelta(days=90),
            Frequency.YEARLY: timedelta(days=365),
        }[self.frequency]
        return self.last_posted + delta

    def is_due(self) -> bool:
        nxt = self.next_due()
        return nxt is not None and nxt <= date.today()


# ── Financial statements ────────────────────────────────────────────────────

@dataclass
class Account:
    code: str
    name: str
    type: str  # asset, liability, equity, revenue, expense
    currency: str = "USD"


@dataclass
class JournalLine:
    account_code: str
    debit: Decimal = D("0")
    credit: Decimal = D("0")
    currency: str = "USD"


@dataclass
class JournalEntry:
    entry_id: str
    date: date
    lines: List[JournalLine]
    posted: bool = False


def generate_balance_sheet(accounts: List[Account], entries: List[JournalEntry],
                           currency: str = "USD") -> Dict:
    totals: Dict[str, Decimal] = {}
    for e in entries:
        if not e.posted:
            continue
        for ln in e.lines:
            if ln.currency != currency:
                continue
            acct = next((a for a in accounts if a.code == ln.account_code), None)
            if acct is None:
                continue
            totals[acct.type] = totals.get(acct.type, D("0")) + ln.debit - ln.credit
    assets = totals.get("asset", D("0"))
    liabilities = totals.get("liability", D("0"))
    equity = totals.get("equity", D("0"))
    return {
        "assets": _d(assets),
        "liabilities": _d(liabilities),
        "equity": _d(equity),
        "balanced": (assets == liabilities + equity),
    }


def generate_income_statement(accounts: List[Account], entries: List[JournalEntry],
                              start: date, end: date, currency: str = "USD") -> Dict:
    revenue = D("0")
    expenses = D("0")
    for e in entries:
        if not e.posted or not (start <= e.date <= end):
            continue
        for ln in e.lines:
            if ln.currency != currency:
                continue
            acct = next((a for a in accounts if a.code == ln.account_code), None)
            if acct is None:
                continue
            if acct.type == "revenue":
                revenue += ln.credit - ln.debit
            elif acct.type == "expense":
                expenses += ln.debit - ln.credit
    return {
        "revenue": _d(revenue),
        "expenses": _d(expenses),
        "net_income": _d(revenue - expenses),
    }


def generate_cash_flow(accounts: List[Account], entries: List[JournalEntry],
                       start: date, end: date, currency: str = "USD") -> Dict:
    operating = D("0")
    investing = D("0")
    financing = D("0")
    cash_accounts = {a.code for a in accounts if a.type == "asset" and "cash" in a.name.lower()}
    for e in entries:
        if not e.posted or not (start <= e.date <= end):
            continue
        for ln in e.lines:
            if ln.currency != currency:
                continue
            if ln.account_code in cash_accounts:
                operating += ln.debit - ln.credit
    return {
        "operating": _d(operating),
        "investing": _d(investing),
        "financing": _d(financing),
        "net_change": _d(operating + investing + financing),
    }


# ── Budget vs actual ────────────────────────────────────────────────────────

@dataclass
class BudgetLine:
    account_code: str
    period: str  # e.g. "2026-10"
    budgeted: Decimal


def budget_vs_actual(budget: List[BudgetLine], accounts: List[Account],
                     entries: List[JournalEntry], period: str) -> List[Dict]:
    actuals: Dict[str, Decimal] = {}
    for e in entries:
        if not e.posted:
            continue
        for ln in e.lines:
            actuals[ln.account_code] = actuals.get(ln.account_code, D("0")) + ln.debit - ln.credit
    results = []
    for bl in budget:
        if bl.period != period:
            continue
        actual = actuals.get(bl.account_code, D("0"))
        variance = actual - bl.budgeted
        pct = (variance / bl.budgeted * 100) if bl.budgeted != 0 else None
        results.append({
            "account_code": bl.account_code,
            "budgeted": _d(bl.budgeted),
            "actual": _d(actual),
            "variance": _d(variance),
            "variance_pct": _d(pct) if pct is not None else None,
        })
    return results


# ── Tax calculation engine ──────────────────────────────────────────────────

@dataclass
class TaxBracket:
    threshold: Decimal
    rate: Decimal


@dataclass
class TaxRule:
    name: str
    brackets: List[TaxBracket]
    standard_deduction: Decimal = D("0")
    credits: Decimal = D("0")


def calculate_tax(taxable_income, rule: TaxRule) -> Dict:
    income = _d(taxable_income) - rule.standard_deduction
    if income < 0:
        income = D("0")
    tax = D("0")
    prev = D("0")
    for bracket in rule.brackets:
        if income <= prev:
            break
        taxable_at_bracket = min(income, bracket.threshold) - prev
        if taxable_at_bracket > 0:
            tax += taxable_at_bracket * bracket.rate
        prev = bracket.threshold
    if income > prev:
        top_rate = rule.brackets[-1].rate if rule.brackets else D("0")
        tax += (income - prev) * top_rate
    tax -= rule.credits
    if tax < 0:
        tax = D("0")
    effective_rate = (tax / income * 100) if income > 0 else D("0")
    return {
        "taxable_income": _d(income),
        "tax_owed": _d(tax),
        "effective_rate": _d(effective_rate),
        "credits_applied": _d(rule.credits),
    }


# ── Convenience: process due recurring entries ───────────────────────────────

def process_recurring(entries: List[RecurringEntry], accounts: List[Account],
                      journal: List[JournalEntry]) -> List[JournalEntry]:
    generated = []
    for re_entry in entries:
        if re_entry.is_due():
            lines = [JournalLine(**ln) for ln in re_entry.lines]
            je = JournalEntry(
                entry_id=f"{re_entry.entry_id}-{re_entry.next_due().isoformat()}",
                date=re_entry.next_due(),
                lines=lines,
                posted=True,
            )
            journal.append(je)
            generated.append(je)
            re_entry.last_posted = re_entry.next_due()
    return generated
