"""Tests for accounting module."""
import pytest
from apex_os_bp.accounting.ledger import Account, AccountType, JournalEntry, Ledger
from apex_os_bp.accounting.engine import AccountingEngine


class TestAccount:
    """Test account data structure."""

    def test_account_creation(self):
        """Account can be created."""
        account = Account(id="acc-1", name="Cash", type=AccountType.ASSET)
        assert account.id == "acc-1"
        assert account.name == "Cash"
        assert account.type == AccountType.ASSET
        assert account.balance == 0.0

    def test_account_credit_debit(self):
        """Account tracks credit and debit."""
        account = Account(id="acc-1", name="Cash", type=AccountType.ASSET)
        account.debit(100.0)
        assert account.balance == 100.0
        account.credit(50.0)
        assert account.balance == 50.0


class TestJournalEntry:
    """Test journal entry."""

    def test_journal_entry_creation(self):
        """Journal entry can be created."""
        entry = JournalEntry(
            id="je-1",
            description="Test entry",
            lines=[
                {"account_id": "acc-1", "debit": 100.0, "credit": 0.0},
                {"account_id": "acc-2", "debit": 0.0, "credit": 100.0},
            ],
        )
        assert entry.id == "je-1"
        assert entry.description == "Test entry"
        assert len(entry.lines) == 2

    def test_journal_entry_balanced(self):
        """Journal entry must be balanced."""
        entry = JournalEntry(
            id="je-1",
            description="Test entry",
            lines=[
                {"account_id": "acc-1", "debit": 100.0, "credit": 0.0},
                {"account_id": "acc-2", "debit": 0.0, "credit": 100.0},
            ],
        )
        assert entry.is_balanced()

    def test_journal_entry_unbalanced_raises(self):
        """Unbalanced journal entry raises error."""
        with pytest.raises(ValueError):
            JournalEntry(
                id="je-1",
                description="Bad entry",
                lines=[
                    {"account_id": "acc-1", "debit": 100.0, "credit": 0.0},
                    {"account_id": "acc-2", "debit": 0.0, "credit": 50.0},
                ],
            )


class TestLedger:
    """Test ledger functionality."""

    def test_add_account(self):
        """Account can be added to ledger."""
        ledger = Ledger()
        account = Account(id="acc-1", name="Cash", type=AccountType.ASSET)
        ledger.add_account(account)
        assert ledger.get_account("acc-1") == account

    def test_post_entry(self):
        """Journal entry can be posted to ledger."""
        ledger = Ledger()
        ledger.add_account(Account(id="acc-1", name="Cash", type=AccountType.ASSET))
        ledger.add_account(Account(id="acc-2", name="Revenue", type=AccountType.INCOME))
        entry = JournalEntry(
            id="je-1",
            description="Test",
            lines=[
                {"account_id": "acc-1", "debit": 100.0, "credit": 0.0},
                {"account_id": "acc-2", "debit": 0.0, "credit": 100.0},
            ],
        )
        ledger.post(entry)
        assert ledger.get_account("acc-1").balance == 100.0
        assert ledger.get_account("acc-2").balance == 100.0

    def test_trial_balance(self):
        """Trial balance is zero for balanced entries."""
        ledger = Ledger()
        ledger.add_account(Account(id="acc-1", name="Cash", type=AccountType.ASSET))
        ledger.add_account(Account(id="acc-2", name="Revenue", type=AccountType.INCOME))
        entry = JournalEntry(
            id="je-1",
            description="Test",
            lines=[
                {"account_id": "acc-1", "debit": 100.0, "credit": 0.0},
                {"account_id": "acc-2", "debit": 0.0, "credit": 100.0},
            ],
        )
        ledger.post(entry)
        assert ledger.trial_balance() == 0.0


class TestAccountingEngine:
    """Test accounting engine."""

    def test_create_invoice(self):
        """Invoice can be created."""
        engine = AccountingEngine()
        engine.add_account(Account(id="acc-1", name="Accounts Receivable", type=AccountType.ASSET))
        engine.add_account(Account(id="acc-2", name="Revenue", type=AccountType.INCOME))
        invoice = engine.create_invoice(
            customer_id="cust-1",
            items=[{"description": "Service", "amount": 100.0}],
        )
        assert invoice["customer_id"] == "cust-1"
        assert invoice["total"] == 100.0
        assert invoice["status"] == "draft"

    def test_post_invoice(self):
        """Invoice can be posted."""
        engine = AccountingEngine()
        engine.add_account(Account(id="acc-1", name="Accounts Receivable", type=AccountType.ASSET))
        engine.add_account(Account(id="acc-2", name="Revenue", type=AccountType.INCOME))
        invoice = engine.create_invoice(
            customer_id="cust-1",
            items=[{"description": "Service", "amount": 100.0}],
        )
        engine.post_invoice(invoice["id"])
        assert engine.get_invoice(invoice["id"])["status"] == "posted"

    def test_double_entry_integrity(self):
        """Double-entry integrity is maintained."""
        engine = AccountingEngine()
        engine.add_account(Account(id="acc-1", name="Accounts Receivable", type=AccountType.ASSET))
        engine.add_account(Account(id="acc-2", name="Revenue", type=AccountType.INCOME))
        invoice = engine.create_invoice(
            customer_id="cust-1",
            items=[{"description": "Service", "amount": 100.0}],
        )
        engine.post_invoice(invoice["id"])
        assert engine.trial_balance() == 0.0
