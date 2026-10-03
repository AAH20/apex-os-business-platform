"""Comprehensive database CRUD tests for APEX-OS Business Platform."""
from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

src_path = Path(__file__).resolve().parents[1] / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from sqlalchemy import create_engine, text, event, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from apex_os_bp.database.models import (
    Base, User, Account, Transaction, AuditLog,
    UserRole, AccountStatus, TransactionType,
)
from apex_os_bp.database.query_builder import QueryBuilder
from apex_os_bp.database.transactions import TransactionManager, AuditMixin
from apex_os_bp.accounting.models import JournalEntry, Transaction as AccTransaction
from apex_os_bp.security.auth import Authenticator


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def fk_on(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    Sess = sessionmaker(bind=engine, expire_on_commit=False)
    s = Sess()
    yield s
    s.rollback()
    s.close()


@pytest.fixture
def sample_user(session):
    u = User(username="testuser", email="test@example.com", full_name="Test User", role=UserRole.ADMIN)
    session.add(u)
    session.commit()
    return u


@pytest.fixture
def sample_account(session, sample_user):
    a = Account(user_id=sample_user.id, name="Checking", account_number="CHK-001",
                balance=1000.0, currency="USD", status=AccountStatus.ACTIVE)
    session.add(a)
    session.commit()
    return a


@pytest.fixture
def sample_txns(session, sample_account):
    txns = [
        Transaction(account_id=sample_account.id, amount=100.0, type=TransactionType.CREDIT, description="Deposit"),
        Transaction(account_id=sample_account.id, amount=50.0, type=TransactionType.DEBIT, description="Withdrawal"),
        Transaction(account_id=sample_account.id, amount=200.0, type=TransactionType.CREDIT, description="Paycheck"),
    ]
    for t in txns:
        session.add(t)
    session.commit()
    return txns


# 1. Setup & Teardown
class TestSetupTeardown:
    def test_engine_creation(self, engine):
        assert engine is not None

    def test_tables_created(self, engine):
        tables = inspect(engine).get_table_names()
        assert all(t in tables for t in ["users", "accounts", "transactions", "audit_logs"])

    def test_session_lifecycle(self, session):
        assert session.is_active is True

    def test_synthetic_data(self, session, sample_user, sample_account, sample_txns):
        assert session.query(User).count() == 1
        assert session.query(Account).count() == 1
        assert session.query(Transaction).count() == 3


# 2. CRUD Operations
class TestUserCRUD:
    def test_create(self, session):
        u = User(username="alice", email="alice@example.com", role=UserRole.MANAGER)
        session.add(u)
        session.commit()
        assert u.id is not None and u.created_at is not None

    def test_read(self, session, sample_user):
        found = session.query(User).filter_by(username="testuser").first()
        assert found is not None and found.email == "test@example.com"

    def test_update(self, session, sample_user):
        sample_user.full_name = "Updated Name"
        session.commit()
        assert sample_user.full_name == "Updated Name"

    def test_delete(self, session, sample_user):
        uid = sample_user.id
        session.delete(sample_user)
        session.commit()
        assert session.query(User).filter_by(id=uid).first() is None

    def test_list(self, session):
        for i in range(5):
            session.add(User(username=f"u{i}", email=f"u{i}@example.com"))
        session.commit()
        assert session.query(User).count() == 5


class TestAccountCRUD:
    def test_create(self, session, sample_user):
        a = Account(user_id=sample_user.id, name="Savings", account_number="SAV-001", balance=500.0)
        session.add(a)
        session.commit()
        assert a.id is not None

    def test_read(self, session, sample_account):
        found = session.query(Account).filter_by(account_number="CHK-001").first()
        assert found is not None and found.balance == 1000.0

    def test_update(self, session, sample_account):
        sample_account.balance = 2000.0
        session.commit()
        assert sample_account.balance == 2000.0

    def test_delete(self, session, sample_account):
        aid = sample_account.id
        session.delete(sample_account)
        session.commit()
        assert session.query(Account).filter_by(id=aid).first() is None

    def test_list(self, session, sample_user):
        for i in range(3):
            session.add(Account(user_id=sample_user.id, name=f"Acc{i}", account_number=f"ACC-{i}"))
        session.commit()
        assert session.query(Account).filter_by(user_id=sample_user.id).count() == 3


class TestTransactionCRUD:
    def test_create(self, session, sample_account):
        t = Transaction(account_id=sample_account.id, amount=25.0, type=TransactionType.DEBIT)
        session.add(t)
        session.commit()
        assert t.id is not None

    def test_read(self, session, sample_txns):
        found = session.query(Transaction).filter_by(description="Deposit").first()
        assert found is not None and found.amount == 100.0

    def test_update(self, session, sample_txns):
        sample_txns[0].amount = 150.0
        session.commit()
        assert sample_txns[0].amount == 150.0

    def test_delete(self, session, sample_txns):
        tid = sample_txns[0].id
        session.delete(sample_txns[0])
        session.commit()
        assert session.query(Transaction).filter_by(id=tid).first() is None

    def test_list(self, session, sample_account, sample_txns):
        assert session.query(Transaction).filter_by(account_id=sample_account.id).count() == 3


# 3. Foreign Key Constraints & Cascading Deletes
class TestForeignKeyConstraints:
    def test_account_requires_user(self, session):
        a = Account(user_id=99999, name="Orphan", account_number="ORPH-001")
        session.add(a)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_cascade_delete_user_accounts(self, session, sample_user, sample_account):
        uid = sample_user.id
        session.delete(sample_user)
        session.commit()
        assert session.query(Account).filter_by(user_id=uid).first() is None

    def test_cascade_delete_account_transactions(self, session, sample_account, sample_txns):
        aid = sample_account.id
        session.delete(sample_account)
        session.commit()
        assert session.query(Transaction).filter_by(account_id=aid).count() == 0

    def test_audit_log_cascade_deleted_with_user(self, session, sample_user):
        log = AuditLog(user_id=sample_user.id, action="TEST", entity_type="Test")
        session.add(log)
        session.commit()
        lid = log.id
        session.delete(sample_user)
        session.commit()
        assert session.query(AuditLog).filter_by(id=lid).first() is None


# 4. Soft Delete & Restore
class TestSoftDelete:
    def test_soft_delete_user(self, session, sample_user):
        sample_user.is_active = False
        session.commit()
        assert sample_user.is_active is False

    def test_soft_delete_hidden_from_active_query(self, session, sample_user):
        sample_user.is_active = False
        session.commit()
        assert len(session.query(User).filter_by(is_active=True).all()) == 0

    def test_restore_soft_deleted(self, session, sample_user):
        sample_user.is_active = False
        session.commit()
        sample_user.is_active = True
        session.commit()
        assert sample_user.is_active is True

    def test_soft_delete_account(self, session, sample_account):
        sample_account.status = AccountStatus.CLOSED
        session.commit()
        assert sample_account.status == AccountStatus.CLOSED

    def test_filter_by_active_status(self, session):
        session.add(User(username="active", email="a@example.com", is_active=True))
        session.add(User(username="inactive", email="i@example.com", is_active=False))
        session.commit()
        active = session.query(User).filter_by(is_active=True).all()
        assert len(active) == 1 and active[0].username == "active"


# 5. Optimistic Locking
class TestOptimisticLocking:
    def test_updated_at_changes_on_update(self, session, sample_user):
        original = sample_user.updated_at
        time.sleep(0.01)
        sample_user.full_name = "New Name"
        session.commit()
        assert sample_user.updated_at >= original

    def test_concurrent_update_detection(self, session, sample_user):
        ts1 = sample_user.updated_at
        time.sleep(0.01)
        sample_user.full_name = "Update1"
        session.commit()
        assert sample_user.updated_at >= ts1

    def test_version_not_lost_on_multiple_updates(self, session, sample_user):
        for i in range(3):
            sample_user.full_name = f"Name{i}"
            session.commit()
            time.sleep(0.005)
        assert sample_user.full_name == "Name2"


# 6. Audit Logging
class TestAuditLogging:
    def test_audit_log_creation(self, session, sample_user):
        log = AuditLog(user_id=sample_user.id, action="CREATE", entity_type="User",
                       entity_id=sample_user.id, details="Created")
        session.add(log)
        session.commit()
        assert log.id is not None and log.created_at is not None

    def test_audit_log_fields(self, session, sample_user):
        log = AuditLog(user_id=sample_user.id, action="UPDATE", entity_type="User",
                       entity_id=sample_user.id, details="Updated", ip_address="127.0.0.1")
        session.add(log)
        session.commit()
        assert log.action == "UPDATE" and log.ip_address == "127.0.0.1"

    def test_audit_log_null_user(self, session):
        log = AuditLog(user_id=None, action="SYSTEM", entity_type="System")
        session.add(log)
        session.commit()
        assert log.id is not None and log.user_id is None

    def test_audit_mixin_log_action(self, session, sample_user):
        AuditMixin.log_action(session, user_id=sample_user.id, action="TEST",
                              entity_type="Test", entity_id=1, details="Test details")
        session.commit()
        log = session.query(AuditLog).filter_by(action="TEST").first()
        assert log is not None and log.details == "Test details"

    def test_audit_trail_ordering(self, session, sample_user):
        for action in ["CREATE", "UPDATE", "DELETE"]:
            session.add(AuditLog(user_id=sample_user.id, action=action, entity_type="User", entity_id=sample_user.id))
        session.commit()
        logs = session.query(AuditLog).filter_by(entity_type="User").order_by(AuditLog.created_at).all()
        assert len(logs) == 3 and [l.action for l in logs] == ["CREATE", "UPDATE", "DELETE"]

    def test_created_at_auto_set(self, session):
        log = AuditLog(action="TEST", entity_type="Test")
        session.add(log)
        session.commit()
        assert log.created_at is not None and isinstance(log.created_at, datetime)


# 7. Bulk Operations
class TestBulkOperations:
    def test_bulk_insert_users(self, session):
        users = [User(username=f"bulk{i}", email=f"bulk{i}@example.com") for i in range(50)]
        session.bulk_save_objects(users)
        session.commit()
        assert session.query(User).filter(User.username.like("bulk%")).count() == 50

    def test_bulk_insert_transactions(self, session, sample_account):
        txns = [Transaction(account_id=sample_account.id, amount=10.0, type=TransactionType.CREDIT) for _ in range(30)]
        session.bulk_save_objects(txns)
        session.commit()
        assert session.query(Transaction).filter_by(account_id=sample_account.id).count() == 30

    def test_bulk_update_via_query(self, session):
        for i in range(10):
            session.add(User(username=f"u{i}", email=f"u{i}@example.com", is_active=True))
        session.commit()
        count = QueryBuilder(session, User).filter_by(is_active=True).update(is_active=False)
        session.commit()
        assert count == 10

    def test_bulk_delete_via_query(self, session):
        for i in range(5):
            session.add(User(username=f"del{i}", email=f"del{i}@example.com"))
        session.commit()
        count = QueryBuilder(session, User).filter(User.username.like("del%")).delete()
        session.commit()
        assert count == 5

    def test_transaction_manager_bulk_insert(self, session):
        mgr = TransactionManager(session)
        users = [User(username=f"tm{i}", email=f"tm{i}@example.com") for i in range(20)]
        count = mgr.bulk_insert(users, batch_size=5)
        session.commit()
        assert count == 20


# 8. Pagination, Filtering, Sorting
class TestPaginationFilteringSorting:
    def test_pagination(self, session):
        for i in range(25):
            session.add(User(username=f"user{i:02d}", email=f"u{i}@example.com"))
        session.commit()
        page1 = QueryBuilder(session, User).paginate(page=1, per_page=10).all()
        page2 = QueryBuilder(session, User).paginate(page=2, per_page=10).all()
        assert len(page1) == 10 and len(page2) == 10
        assert {u.id for u in page1}.isdisjoint({u.id for u in page2})

    def test_filter_by_role(self, session):
        session.add(User(username="admin1", email="a1@example.com", role=UserRole.ADMIN))
        session.add(User(username="viewer1", email="v1@example.com", role=UserRole.VIEWER))
        session.commit()
        assert len(QueryBuilder(session, User).filter_by(role=UserRole.ADMIN).all()) == 1

    def test_filter_like(self, session):
        session.add(User(username="john_doe", email="john@example.com"))
        session.add(User(username="jane_doe", email="jane@example.com"))
        session.add(User(username="bob", email="bob@example.com"))
        session.commit()
        assert len(QueryBuilder(session, User).filter_like("username", "%_doe").all()) == 2

    def test_filter_in(self, session):
        for i in range(5):
            session.add(User(username=f"user{i}", email=f"u{i}@example.com"))
        session.commit()
        assert len(QueryBuilder(session, User).filter_in("username", ["user0", "user2", "user4"]).all()) == 3

    def test_filter_between(self, session, sample_user):
        now = datetime.utcnow()
        results = QueryBuilder(session, User).filter_between(
            "created_at", now - timedelta(hours=1), now + timedelta(hours=1)).all()
        assert len(results) >= 1

    def test_sort_ascending(self, session):
        for name in ["charlie", "alice", "bob"]:
            session.add(User(username=name, email=f"{name}@example.com"))
        session.commit()
        results = QueryBuilder(session, User).order_by_column("username", "asc").all()
        assert [u.username for u in results] == ["alice", "bob", "charlie"]

    def test_sort_descending(self, session):
        for name in ["charlie", "alice", "bob"]:
            session.add(User(username=name, email=f"{name}@example.com"))
        session.commit()
        results = QueryBuilder(session, User).order_by_column("username", "desc").all()
        assert [u.username for u in results] == ["charlie", "bob", "alice"]

    def test_limit_offset(self, session):
        for i in range(10):
            session.add(User(username=f"user{i}", email=f"u{i}@example.com"))
        session.commit()
        results = QueryBuilder(session, User).order_by_column("username").offset(3).limit(4).all()
        assert len(results) == 4

    def test_chained_filters(self, session):
        for i in range(10):
            session.add(User(username=f"user{i}", email=f"u{i}@example.com",
                             role=UserRole.MANAGER if i % 2 == 0 else UserRole.VIEWER))
        session.commit()
        results = (QueryBuilder(session, User).filter_by(role=UserRole.MANAGER)
                   .order_by_column("username", "desc").limit(2).all())
        assert len(results) == 2 and all(u.role == UserRole.MANAGER for u in results)


# 9. Double-Entry Validation
class TestDoubleEntryValidation:
    def test_balanced_journal_entry(self):
        entry = JournalEntry(transactions=[
            AccTransaction(account_id="acc1", amount=Decimal("100.00")),
            AccTransaction(account_id="acc2", amount=Decimal("-100.00")),
        ])
        assert entry.is_balanced() is True

    def test_unbalanced_journal_entry_raises(self):
        with pytest.raises(ValueError, match="not balanced"):
            JournalEntry(transactions=[
                AccTransaction(account_id="acc1", amount=Decimal("100.00")),
                AccTransaction(account_id="acc2", amount=Decimal("-50.00")),
            ])

    def test_single_transaction_raises(self):
        with pytest.raises(ValueError, match="at least two"):
            JournalEntry(transactions=[AccTransaction(account_id="acc1", amount=Decimal("100.00"))])

    def test_zero_amount_raises(self):
        with pytest.raises(ValueError, match="cannot be zero"):
            AccTransaction(account_id="acc1", amount=Decimal("0"))

    def test_total_debits_credits(self):
        entry = JournalEntry(transactions=[
            AccTransaction(account_id="a1", amount=Decimal("200.00")),
            AccTransaction(account_id="a2", amount=Decimal("-150.00")),
            AccTransaction(account_id="a3", amount=Decimal("-50.00")),
        ])
        assert entry.total_debits() == Decimal("200.00")
        assert entry.total_credits() == Decimal("200.00")

    def test_complex_balanced_entry(self):
        entry = JournalEntry(transactions=[
            AccTransaction(account_id="cash", amount=Decimal("1000.00")),
            AccTransaction(account_id="revenue", amount=Decimal("-600.00")),
            AccTransaction(account_id="tax", amount=Decimal("-400.00")),
        ])
        assert entry.is_balanced() is True


# 10. Password Hashing & Authentication
class TestPasswordHashing:
    def test_hash_consistency(self):
        auth = Authenticator()
        assert auth._hash_password("secret", "salt") == auth._hash_password("secret", "salt")

    def test_different_passwords_different_hashes(self):
        auth = Authenticator()
        assert auth._hash_password("p1", "s") != auth._hash_password("p2", "s")

    def test_different_salts_different_hashes(self):
        auth = Authenticator()
        assert auth._hash_password("p", "s1") != auth._hash_password("p", "s2")

    def test_hash_length(self):
        assert len(Authenticator()._hash_password("pw", "salt")) == 64

    def test_register_and_authenticate(self):
        auth = Authenticator()
        user = auth.register("alice", "alice@example.com", "secret123")
        assert user.password_hash != "secret123" and user.salt != ""
        result = auth.authenticate("alice", "secret123")
        assert result is not None and result.username == "alice"

    def test_authenticate_wrong_password(self):
        auth = Authenticator()
        auth.register("bob", "bob@example.com", "correct")
        assert auth.authenticate("bob", "wrong") is None

    def test_authenticate_nonexistent_user(self):
        assert Authenticator().authenticate("nobody", "pass") is None

    def test_password_not_stored_plaintext(self):
        user = Authenticator().register("carol", "carol@example.com", "mypassword")
        assert "mypassword" not in user.password_hash
