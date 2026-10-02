"""Double-entry accounting ledger."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Union


class AccountType(Enum):
    """Account types."""
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


@dataclass
class Account:
    """Account data structure."""
    id: str
    name: str
    type: AccountType
    balance: float = 0.0

    def debit(self, amount: float) -> None:
        """Debit the account."""
        if self.type in (AccountType.ASSET, AccountType.EXPENSE):
            self.balance += amount
        else:
            self.balance -= amount

    def credit(self, amount: float) -> None:
        """Credit the account."""
        if self.type in (AccountType.ASSET, AccountType.EXPENSE):
            self.balance -= amount
        else:
            self.balance += amount


@dataclass
class JournalEntryLine:
    """Journal entry line."""
    account_id: str
    debit: float = 0.0
    credit: float = 0.0

    @classmethod
    def from_dict(cls, data: dict) -> "JournalEntryLine":
        """Create from dictionary."""
        return cls(
            account_id=data["account_id"],
            debit=data.get("debit", 0.0),
            credit=data.get("credit", 0.0),
        )


@dataclass
class JournalEntry:
    """Journal entry."""
    id: str
    description: str
    lines: List[JournalEntryLine] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        # Convert dict lines to JournalEntryLine objects
        converted = []
        for line in self.lines:
            if isinstance(line, dict):
                converted.append(JournalEntryLine.from_dict(line))
            else:
                converted.append(line)
        self.lines = converted
        if not self.is_balanced():
            raise ValueError("Journal entry is not balanced")

    def is_balanced(self) -> bool:
        """Check if debits equal credits."""
        total_debits = sum(line.debit for line in self.lines)
        total_credits = sum(line.credit for line in self.lines)
        return abs(total_debits - total_credits) < 0.01


class Ledger:
    """Double-entry accounting ledger."""

    def __init__(self):
        self._accounts: Dict[str, Account] = {}
        self._entries: List[JournalEntry] = []

    def add_account(self, account: Account) -> None:
        """Add account to ledger."""
        self._accounts[account.id] = account

    def get_account(self, account_id: str) -> Optional[Account]:
        """Get account by ID."""
        return self._accounts.get(account_id)

    def post(self, entry: JournalEntry) -> None:
        """Post journal entry to ledger."""
        for line in entry.lines:
            account = self._accounts.get(line.account_id)
            if not account:
                raise ValueError(f"Account not found: {line.account_id}")
            if line.debit > 0:
                account.debit(line.debit)
            if line.credit > 0:
                account.credit(line.credit)
        self._entries.append(entry)

    def trial_balance(self) -> float:
        """Calculate trial balance (sum of all debit balances - sum of all credit balances).
        Should be 0 for balanced entries."""
        debit_balance = 0.0
        credit_balance = 0.0
        for account in self._accounts.values():
            if account.type in (AccountType.ASSET, AccountType.EXPENSE):
                debit_balance += account.balance
            else:
                credit_balance += account.balance
        return debit_balance - credit_balance

    def get_accounts(self) -> List[Account]:
        """Get all accounts."""
        return list(self._accounts.values())

    def get_entries(self) -> List[JournalEntry]:
        """Get all journal entries."""
        return list(self._entries)
