#!/usr/bin/env python3
"""APEX-OS Accounting Demo — accounts, journals, trial balance, statements, budgets."""

import random
from datetime import datetime

random.seed(42)


def header(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def section(title):
    print(f"\n--- {title} ---")


# ── 1. Account Creation ──────────────────────────────────────────────
def demo_account_creation():
    header("1. ACCOUNT CREATION")
    accounts = [
        ("1000", "Cash", "Asset", 45230.00),
        ("1010", "Accounts Receivable", "Asset", 28450.00),
        ("1100", "Inventory", "Asset", 67800.00),
        ("1200", "Equipment", "Asset", 125000.00),
        ("2000", "Accounts Payable", "Liability", 19300.00),
        ("2100", "Notes Payable", "Liability", 50000.00),
        ("3000", "Owner's Equity", "Equity", 197180.00),
        ("4000", "Revenue", "Revenue", 0.00),
        ("5000", "Cost of Goods Sold", "Expense", 0.00),
        ("6000", "Salaries Expense", "Expense", 0.00),
        ("6100", "Rent Expense", "Expense", 0.00),
        ("6200", "Utilities Expense", "Expense", 0.00),
    ]
    print(f"  {'Code':<8} {'Name':<26} {'Type':<12} {'Balance':>14}")
    print(f"  {'-' * 62}")
    for code, name, acc_type, balance in accounts:
        print(f"  {code:<8} {name:<26} {acc_type:<12} ${balance:>13,.2f}")
    print(f"\n  Total accounts created: {len(accounts)}")
    print(f"  Chart of accounts initialized ✓")


# ── 2. Journal Entry ────────────────────────────────────────────────
def demo_journal_entry():
    header("2. JOURNAL ENTRY")
    entries = [
        {
            "date": "2026-10-01",
            "desc": "Invoice #INV-2041 — Web design services",
            "lines": [
                ("1010", "Accounts Receivable", 4200.00, 0),
                ("4000", "Revenue", 0, 4200.00),
            ],
        },
        {
            "date": "2026-10-01",
            "desc": "Office rent for October",
            "lines": [
                ("6100", "Rent Expense", 3500.00, 0),
                ("1000", "Cash", 0, 3500.00),
            ],
        },
        {
            "date": "2026-10-02",
            "desc": "Purchase of office equipment",
            "lines": [
                ("1200", "Equipment", 8500.00, 0),
                ("1000", "Cash", 0, 8500.00),
            ],
        },
        {
            "date": "2026-10-02",
            "desc": "Client payment received — INV-2038",
            "lines": [
                ("1000", "Cash", 6800.00, 0),
                ("1010", "Accounts Receivable", 0, 6800.00),
            ],
        },
        {
            "date": "2026-10-03",
            "desc": "Monthly salaries",
            "lines": [
                ("6000", "Salaries Expense", 12000.00, 0),
                ("1000", "Cash", 0, 12000.00),
            ],
        },
    ]
    for entry in entries:
        print(f"\n  Date: {entry['date']}")
        print(f"  Description: {entry['desc']}")
        print(f"  {'Account':<26} {'Debit':>12} {'Credit':>12}")
        print(f"  {'-' * 52}")
        total_debit = 0
        total_credit = 0
        for code, name, debit, credit in entry["lines"]:
            d = f"${debit:,.2f}" if debit else ""
            c = f"${credit:,.2f}" if credit else ""
            print(f"  {code} {name:<20} {d:>12} {c:>12}")
            total_debit += debit
            total_credit += credit
        print(f"  {'-' * 52}")
        print(f"  {'Totals:':<26} ${total_debit:>11,.2f} ${total_credit:>11,.2f}")
        balanced = "✓ Balanced" if total_debit == total_credit else "✗ IMBALANCED"
        print(f"  Status: {balanced}")


# ── 3. Trial Balance ─────────────────────────────────────────────────
def demo_trial_balance():
    header("3. TRIAL BALANCE")
    print(f"  As of {datetime.now().strftime('%B %d, %Y')}\n")
    tb = [
        ("1000", "Cash", 25030.00, 0),
        ("1010", "Accounts Receivable", 21650.00, 0),
        ("1100", "Inventory", 67800.00, 0),
        ("1200", "Equipment", 133500.00, 0),
        ("2000", "Accounts Payable", 0, 19300.00),
        ("2100", "Notes Payable", 0, 50000.00),
        ("3000", "Owner's Equity", 0, 197180.00),
        ("4000", "Revenue", 0, 4200.00),
        ("5000", "Cost of Goods Sold", 0, 0),
        ("6000", "Salaries Expense", 12000.00, 0),
        ("6100", "Rent Expense", 3500.00, 0),
        ("6200", "Utilities Expense", 0, 0),
    ]
    print(f"  {'Code':<8} {'Account':<26} {'Debit':>14} {'Credit':>14}")
    print(f"  {'-' * 64}")
    total_debit = 0
    total_credit = 0
    for code, name, debit, credit in tb:
        d = f"${debit:,.2f}" if debit else ""
        c = f"${credit:,.2f}" if credit else ""
        print(f"  {code:<8} {name:<26} {d:>14} {c:>14}")
        total_debit += debit
        total_credit += credit
    print(f"  {'-' * 64}")
    print(f"  {'TOTALS':<36} ${total_debit:>13,.2f} ${total_credit:>13,.2f}")
    if total_debit == total_credit:
        print(f"\n  ✓ Trial balance is in balance")
    else:
        diff = abs(total_debit - total_credit)
        print(f"\n  ✗ IMBALANCE of ${diff:,.2f}")


# ── 4. Financial Statement ───────────────────────────────────────────
def demo_financial_statement():
    header("4. FINANCIAL STATEMENT")
    section("Income Statement (YTD 2026)")
    income = [
        ("Revenue", 1284500.00),
        ("Cost of Goods Sold", -513800.00),
    ]
    gross = sum(v for _, v in income)
    print(f"  {'Revenue':<30} ${1284500:>13,.2f}")
    print(f"  {'Cost of Goods Sold':<30} ${-513800:>13,.2f}")
    print(f"  {'-' * 46}")
    print(f"  {'Gross Profit':<30} ${gross:>13,.2f}")
    expenses = [
        ("Salaries", -384000.00),
        ("Rent", -42000.00),
        ("Utilities", -18500.00),
        ("Marketing", -67000.00),
        ("Depreciation", -25000.00),
        ("Other", -31200.00),
    ]
    total_exp = sum(v for _, v in expenses)
    print(f"\n  Operating Expenses:")
    for name, val in expenses:
        print(f"    {name:<28} ${val:>13,.2f}")
    print(f"  {'-' * 46}")
    print(f"  {'Total Expenses':<30} ${total_exp:>13,.2f}")
    net = gross + total_exp
    print(f"\n  {'NET INCOME':<30} ${net:>13,.2f}")
    margin = (net / 1284500) * 100
    print(f"  {'Net Profit Margin':<30} {margin:>13.1f}%")

    section("Balance Sheet Summary")
    bs = [
        ("Total Assets", 247980.00),
        ("Total Liabilities", 69300.00),
        ("Total Equity", 197180.00),
    ]
    for name, val in bs:
        print(f"  {name:<30} ${val:>13,.2f}")
    liab_eq = 69300.00 + 197180.00
    print(f"  {'L + E':<30} ${liab_eq:>13,.2f}")
    balanced = "✓ Balanced" if abs(247980.00 - liab_eq) < 0.01 else "✗ Check"
    print(f"  Status: {balanced}")


# ── 5. Budget Comparison ─────────────────────────────────────────────
def demo_budget_comparison():
    header("5. BUDGET COMPARISON")
    print(f"  Q4 2026 Budget vs Actual\n")
    categories = [
        ("Salaries", 400000, 384000),
        ("Rent", 42000, 42000),
        ("Utilities", 20000, 18500),
        ("Marketing", 80000, 67000),
        ("Equipment", 30000, 8500),
        ("Software", 15000, 14200),
        ("Travel", 10000, 6800),
        ("Training", 8000, 5200),
    ]
    print(f"  {'Category':<16} {'Budget':>12} {'Actual':>12} {'Variance':>12} {'%':>8}")
    print(f"  {'-' * 62}")
    total_budget = 0
    total_actual = 0
    for name, budget, actual in categories:
        variance = budget - actual
        pct = (variance / budget) * 100 if budget else 0
        status = "✓" if variance >= 0 else "✗"
        print(f"  {name:<16} ${budget:>11,} ${actual:>11,} ${variance:>+11,} {pct:>+7.1f}% {status}")
        total_budget += budget
        total_actual += actual
    print(f"  {'-' * 62}")
    total_var = total_budget - total_actual
    total_pct = (total_var / total_budget) * 100
    print(f"  {'TOTAL':<16} ${total_budget:>11,} ${total_actual:>11,} ${total_var:>+11,} {total_pct:>+7.1f}%")
    print(f"\n  Overall: Under budget by ${total_var:,} ({total_pct:.1f}%)")
    print(f"  Largest savings: Marketing (${80000 - 67000:,} under)")
    print(f"  Overspend: Equipment (${8500 - 30000:,} over)")


# ── Main ─────────────────────────────────────────────────────────────
def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║        APEX-OS Business Platform — Accounting Demo      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    demo_account_creation()
    demo_journal_entry()
    demo_trial_balance()
    demo_financial_statement()
    demo_budget_comparison()
    print(f"\n{'=' * 60}")
    print("  Accounting demo complete.")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
