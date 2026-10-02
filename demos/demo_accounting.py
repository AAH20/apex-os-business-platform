#!/usr/bin/env python3
"""
APEX-OS Business Platform — Accounting Demo
============================================
Demonstrates double-entry bookkeeping with sample transactions.

Shows:
  • Chart of accounts setup
  • Recording transactions (debits = credits)
  • Trial balance generation
  • Income statement and balance sheet summaries

Usage:
    python demo_accounting.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Account:
    """A single account in the chart of accounts."""
    code: str
    name: str
    account_type: str  # 'asset', 'liability', 'equity', 'revenue', 'expense'
    balance: Decimal = Decimal("0.00")


@dataclass
class JournalEntry:
    """A double-entry journal entry: total debits must equal total credits."""
    date: date
    description: str
    lines: List[tuple]  # list of (account_code, debit, credit)


@dataclass
class GeneralLedger:
    """The general ledger — collection of accounts and journal entries."""
    accounts: Dict[str, Account] = field(default_factory=dict)
    entries: List[JournalEntry] = field(default_factory=list)

    def add_account(self, code: str, name: str, account_type: str) -> None:
        """Add an account to the chart of accounts."""
        self.accounts[code] = Account(code=code, name=name, account_type=account_type)

    def post_entry(self, entry: JournalEntry) -> None:
        """Post a journal entry, updating account balances."""
        total_debits = sum(Decimal(str(d)) for _, d, _ in entry.lines)
        total_credits = sum(Decimal(str(c)) for _, _, c in entry.lines)
        if total_debits != total_credits:
            raise ValueError(
                f"Unbalanced entry: debits={total_debits}, credits={total_credits}"
            )
        for code, debit, credit in entry.lines:
            if code not in self.accounts:
                raise KeyError(f"Unknown account: {code}")
            acct = self.accounts[code]
            # Debits increase assets/expenses; credits increase liabilities/equity/revenue
            if acct.account_type in ("asset", "expense"):
                acct.balance += Decimal(str(debit)) - Decimal(str(credit))
            else:
                acct.balance += Decimal(str(credit)) - Decimal(str(debit))
        self.entries.append(entry)

    def trial_balance(self) -> Dict[str, Decimal]:
        """Return a trial balance: {account_code: net_balance}."""
        return {code: acct.balance for code, acct in self.accounts.items()}

    def income_statement(self) -> Dict[str, Decimal]:
        """Return revenue and expense totals."""
        revenue = sum(
            acct.balance for acct in self.accounts.values()
            if acct.account_type == "revenue"
        )
        expenses = sum(
            acct.balance for acct in self.accounts.values()
            if acct.account_type == "expense"
        )
        return {"total_revenue": revenue, "total_expenses": expenses, "net_income": revenue - expenses}

    def balance_sheet(self) -> Dict[str, Decimal]:
        """Return asset, liability, and equity totals."""
        assets = sum(
            acct.balance for acct in self.accounts.values()
            if acct.account_type == "asset"
        )
        liabilities = sum(
            acct.balance for acct in self.accounts.values()
            if acct.account_type == "liability"
        )
        equity = sum(
            acct.balance for acct in self.accounts.values()
            if acct.account_type == "equity"
        )
        return {"total_assets": assets, "total_liabilities": liabilities, "total_equity": equity}


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def run_demo() -> None:
    """Run the accounting demonstration."""
    print("=" * 70)
    print("  APEX-OS Business Platform — Accounting Demo")
    print("  Double-Entry Bookkeeping with Sample Transactions")
    print("=" * 70)

    # 1. Set up chart of accounts
    print("\n📋 STEP 1: Chart of Accounts")
    print("-" * 40)
    gl = GeneralLedger()
    accounts = [
        ("1000", "Cash", "asset"),
        ("1100", "Accounts Receivable", "asset"),
        ("1200", "Inventory", "asset"),
        ("1500", "Equipment", "asset"),
        ("2000", "Accounts Payable", "liability"),
        ("2100", "Notes Payable", "liability"),
        ("3000", "Owner's Equity", "equity"),
        ("4000", "Sales Revenue", "revenue"),
        ("5000", "Cost of Goods Sold", "expense"),
        ("5100", "Rent Expense", "expense"),
        ("5200", "Salaries Expense", "expense"),
    ]
    for code, name, atype in accounts:
        gl.add_account(code, name, atype)
        print(f"  {code:>6}  {name:<25}  ({atype})")

    # 2. Record sample transactions
    print("\n📒 STEP 2: Recording Transactions")
    print("-" * 40)

    transactions = [
        JournalEntry(
            date=date(2026, 1, 1),
            description="Owner invests $50,000 cash",
            lines=[("1000", 50000, 0), ("3000", 0, 50000)],
        ),
        JournalEntry(
            date=date(2026, 1, 5),
            description="Purchase equipment for $12,000 cash",
            lines=[("1500", 12000, 0), ("1000", 0, 12000)],
        ),
        JournalEntry(
            date=date(2026, 1, 10),
            description="Purchase inventory $8,000 on account",
            lines=[("1200", 8000, 0), ("2000", 0, 8000)],
        ),
        JournalEntry(
            date=date(2026, 1, 15),
            description="Sell goods for $15,000 cash (COGS $6,000)",
            lines=[("1000", 15000, 0), ("4000", 0, 15000),
                   ("5000", 6000, 0), ("1200", 0, 6000)],
        ),
        JournalEntry(
            date=date(2026, 1, 20),
            description="Sell goods on account $10,000 (COGS $4,000)",
            lines=[("1100", 10000, 0), ("4000", 0, 10000),
                   ("5000", 4000, 0), ("1200", 0, 4000)],
        ),
        JournalEntry(
            date=date(2026, 1, 25),
            description="Pay rent $2,500",
            lines=[("5100", 2500, 0), ("1000", 0, 2500)],
        ),
        JournalEntry(
            date=date(2026, 1, 28),
            description="Pay salaries $5,000",
            lines=[("5200", 5000, 0), ("1000", 0, 5000)],
        ),
        JournalEntry(
            date=date(2026, 1, 30),
            description="Pay supplier $3,000",
            lines=[("2000", 3000, 0), ("1000", 0, 3000)],
        ),
        JournalEntry(
            date=date(2026, 1, 31),
            description="Collect $7,000 from customer",
            lines=[("1000", 7000, 0), ("1100", 0, 7000)],
        ),
    ]

    for entry in transactions:
        gl.post_entry(entry)
        print(f"  {entry.date}  {entry.description}")
        for code, debit, credit in entry.lines:
            acct = gl.accounts[code]
            print(f"           {code} {acct.name:<25}  Dr ${debit:>10,.2f}  Cr ${credit:>10,.2f}")

    # 3. Trial balance
    print("\n📊 STEP 3: Trial Balance")
    print("-" * 40)
    print(f"  {'Account':<30} {'Debit':>12} {'Credit':>12}")
    print(f"  {'-'*30} {'-'*12} {'-'*12}")
    total_dr = Decimal("0")
    total_cr = Decimal("0")
    for code, acct in sorted(gl.accounts.items()):
        if acct.balance == 0:
            continue
        if acct.balance > 0:
            if acct.account_type in ("asset", "expense"):
                print(f"  {code} {acct.name:<25} ${acct.balance:>10,.2f} {'':>12}")
                total_dr += acct.balance
            else:
                print(f"  {code} {acct.name:<25} {'':>12} ${acct.balance:>10,.2f}")
                total_cr += acct.balance
        else:
            if acct.account_type in ("asset", "expense"):
                print(f"  {code} {acct.name:<25} {'':>12} ${abs(acct.balance):>10,.2f}")
                total_cr += abs(acct.balance)
            else:
                print(f"  {code} {acct.name:<25} ${abs(acct.balance):>10,.2f} {'':>12}")
                total_dr += abs(acct.balance)
    print(f"  {'-'*30} {'-'*12} {'-'*12}")
    print(f"  {'TOTALS':<30} ${total_dr:>10,.2f} ${total_cr:>10,.2f}")
    assert total_dr == total_cr, "Trial balance is out of balance!"
    print("  ✅ Trial balance is in balance.")

    # 4. Income statement
    print("\n📈 STEP 4: Income Statement (January 2026)")
    print("-" * 40)
    inc = gl.income_statement()
    print(f"  Revenue:       ${inc['total_revenue']:>12,.2f}")
    print(f"  Expenses:      ${inc['total_expenses']:>12,.2f}")
    print(f"  {'─'*40}")
    print(f"  Net Income:    ${inc['net_income']:>12,.2f}")

    # 5. Close the books (transfer net income to equity)
    print("\n🔒 STEP 5: Closing Entry")
    print("-" * 40)
    inc = gl.income_statement()
    net = inc['net_income']
    closing = JournalEntry(
        date=date(2026, 1, 31),
        description="Close revenue and expense accounts",
        lines=[
            ("4000", inc['total_revenue'], 0),
            ("5000", 0, inc['total_expenses']),
            ("3000", 0, net),
        ],
    )
    gl.post_entry(closing)
    print(f"  Close revenue  → Dr ${inc['total_revenue']:>10,.2f}")
    print(f"  Close expenses → Cr ${inc['total_expenses']:>10,.2f}")
    print(f"  Net income     → Cr ${net:>10,.2f} (to Owner's Equity)")

    # 6. Balance sheet
    print("\n📉 STEP 6: Balance Sheet (as of Jan 31, 2026)")
    print("-" * 40)
    bs = gl.balance_sheet()
    print(f"  Assets:        ${bs['total_assets']:>12,.2f}")
    print(f"  Liabilities:   ${bs['total_liabilities']:>12,.2f}")
    print(f"  Equity:        ${bs['total_equity']:>12,.2f}")
    print(f"  {'─'*40}")
    liab_equity = bs['total_liabilities'] + bs['total_equity']
    print(f"  L + E:         ${liab_equity:>12,.2f}")
    assert bs['total_assets'] == liab_equity, "Balance sheet does not balance!"
    print("  ✅ Balance sheet balances (A = L + E).")

    print("\n" + "=" * 70)
    print("  Accounting demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
