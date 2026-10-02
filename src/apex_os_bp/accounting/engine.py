"""Accounting engine."""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from apex_os_bp.accounting.ledger import Account, AccountType, JournalEntry, JournalEntryLine, Ledger


class AccountingEngine:
    """Accounting engine with invoice management."""

    def __init__(self):
        self._ledger = Ledger()
        self._invoices: Dict[str, Dict] = {}

    def add_account(self, account: Account) -> None:
        """Add account to ledger."""
        self._ledger.add_account(account)

    def create_invoice(self, customer_id: str, items: List[Dict]) -> Dict:
        """Create a new invoice."""
        invoice_id = str(uuid.uuid4())
        total = sum(item["amount"] for item in items)
        invoice = {
            "id": invoice_id,
            "customer_id": customer_id,
            "items": items,
            "total": total,
            "status": "draft",
        }
        self._invoices[invoice_id] = invoice
        return invoice

    def post_invoice(self, invoice_id: str) -> None:
        """Post invoice to ledger."""
        invoice = self._invoices.get(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")
        if invoice["status"] != "draft":
            raise ValueError(f"Invoice already posted: {invoice_id}")

        # Find AR and Revenue accounts
        ar_account = None
        revenue_account = None
        for acc in self._ledger.get_accounts():
            if acc.name == "Accounts Receivable":
                ar_account = acc
            elif acc.name == "Revenue":
                revenue_account = acc

        if not ar_account or not revenue_account:
            raise ValueError("Required accounts not found. Add 'Accounts Receivable' and 'Revenue' accounts.")

        lines = [
            JournalEntryLine(account_id=ar_account.id, debit=invoice["total"], credit=0.0),
            JournalEntryLine(account_id=revenue_account.id, debit=0.0, credit=invoice["total"]),
        ]
        entry = JournalEntry(
            id=str(uuid.uuid4()),
            description=f"Invoice {invoice_id}",
            lines=lines,
        )
        self._ledger.post(entry)
        invoice["status"] = "posted"

    def get_invoice(self, invoice_id: str) -> Optional[Dict]:
        """Get invoice by ID."""
        return self._invoices.get(invoice_id)

    def trial_balance(self) -> float:
        """Get trial balance."""
        return self._ledger.trial_balance()

    def get_accounts(self) -> List[Account]:
        """Get all accounts."""
        return self._ledger.get_accounts()

    def get_ledger(self) -> Ledger:
        """Get the ledger."""
        return self._ledger
