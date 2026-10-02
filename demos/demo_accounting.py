#!/usr/bin/env python3
"""Demo: Accounting workflow — journal entries, trial balance, invoice, payment, P&L."""

from collections import defaultdict
from datetime import date


# ── In-memory ledger ──────────────────────────────────────────────────────────
journal: list[dict] = []
invoices: list[dict] = []
payments: list[dict] = []


# ── 1. Create journal entries ────────────────────────────────────────────────
def create_journal_entries():
    entries = [
        {"date": date(2026, 10, 1), "desc": "Owner capital injection",
         "debits": [("Cash", 50_000)], "credits": [("Equity", 50_000)]},
        {"date": date(2026, 10, 2), "desc": "Purchase equipment",
         "debits": [("Equipment", 12_000)], "credits": [("Cash", 12_000)]},
        {"date": date(2026, 10, 3), "desc": "Service revenue on account",
         "debits": [("Accounts Receivable", 8_500)], "credits": [("Revenue", 8_500)]},
        {"date": date(2026, 10, 4), "desc": "Pay rent",
         "debits": [("Rent Expense", 3_000)], "credits": [("Cash", 3_000)]},
        {"date": date(2026, 10, 5), "desc": "Pay salaries",
         "debits": [("Salary Expense", 7_500)], "credits": [("Cash", 7_500)]},
    ]
    journal.extend(entries)
    print(f"✓ Created {len(entries)} journal entries")
    for e in entries:
        dr = ", ".join(f"{a} ${v:,}" for a, v in e["debits"])
        cr = ", ".join(f"{a} ${v:,}" for a, v in e["credits"])
        print(f"  {e['date']}  {e['desc']:<30}  DR {dr}  |  CR {cr}")


# ── 2. Generate trial balance ────────────────────────────────────────────────
def generate_trial_balance():
    balances: dict[str, float] = defaultdict(float)
    for entry in journal:
        for acct, amt in entry["debits"]:
            balances[acct] += amt
        for acct, amt in entry["credits"]:
            balances[acct] -= amt

    print("\n── TRIAL BALANCE ──")
    print(f"{'Account':<25} {'Debit':>12} {'Credit':>12}")
    print("─" * 50)
    total_dr = total_cr = 0.0
    for acct in sorted(balances):
        bal = balances[acct]
        dr = bal if bal > 0 else 0
        cr = -bal if bal < 0 else 0
        total_dr += dr
        total_cr += cr
        print(f"{acct:<25} {dr:>12,.2f} {cr:>12,.2f}")
    print("─" * 50)
    print(f"{'TOTAL':<25} {total_dr:>12,.2f} {total_cr:>12,.2f}")
    assert abs(total_dr - total_cr) < 0.01, "Trial balance out of balance!"
    print("✓ Balanced")


# ── 3. Create invoice ────────────────────────────────────────────────────────
def create_invoice():
    inv = {"id": "INV-001", "date": date(2026, 10, 6), "client": "Acme Corp",
           "amount": 8_500, "status": "open"}
    invoices.append(inv)
    journal.append({"date": inv["date"], "desc": f"Invoice {inv['id']} to {inv['client']}",
                    "debits": [("Accounts Receivable", inv["amount"])],
                    "credits": [("Revenue", inv["amount"])]})
    print(f"\n✓ Created invoice {inv['id']} — {inv['client']} — ${inv['amount']:,}")


# ── 4. Process payment ───────────────────────────────────────────────────────
def process_payment():
    inv = next(i for i in invoices if i["status"] == "open")
    pay = {"id": "PAY-001", "date": date(2026, 10, 10), "invoice_id": inv["id"],
           "amount": inv["amount"]}
    payments.append(pay)
    inv["status"] = "paid"
    journal.append({"date": pay["date"], "desc": f"Payment {pay['id']} for {inv['id']}",
                    "debits": [("Cash", pay["amount"])],
                    "credits": [("Accounts Receivable", pay["amount"])]})
    print(f"✓ Processed payment {pay['id']} — ${pay['amount']:,} — invoice {inv['id']} paid")


# ── 5. Generate P&L report ───────────────────────────────────────────────────
def generate_pl_report():
    revenue = expense = 0.0
    for entry in journal:
        for acct, amt in entry["credits"]:
            if acct == "Revenue":
                revenue += amt
        for acct, amt in entry["debits"]:
            if "Expense" in acct:
                expense += amt

    print("\n── PROFIT & LOSS ──")
    print(f"{'Revenue':<25} ${revenue:>12,.2f}")
    print(f"{'Expenses':<25} ${expense:>12,.2f}")
    print("─" * 40)
    net = revenue - expense
    label = "NET PROFIT" if net >= 0 else "NET LOSS"
    print(f"{label:<25} ${net:>12,.2f}")


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  APEX-OS Accounting Demo")
    print("=" * 60)
    create_journal_entries()
    generate_trial_balance()
    create_invoice()
    process_payment()
    generate_pl_report()
    print("\n" + "=" * 60)
    print("  Demo complete")
    print("=" * 60)
