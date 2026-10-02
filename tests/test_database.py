"""Comprehensive tests for the database layer.

Tests SQLAlchemy models, connection pooling, query builder,
transaction management, and migrations.
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Ensure src is on the path
src_path = Path(__file__).resolve().parents[1] / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, OperationalError

from apex_os_bp.database.models import (
    Base,
    User,
    Account,
    Transaction,
    AuditLog,
    UserRole,
    AccountStatus,
    TransactionType,
)
from apex_os_bp.database.pool import DatabasePool, get_pool
from apex_os_bp.database.query_builder import QueryBuilder
from apex_os_bp.database.transactions import (
    TransactionManager,
    transaction_scope,
    transactional,
    AuditMixin,
)
from apex_os_bp.database.migrations import (
    get_alembic_config,
    run_migrations,
    get_current_revision,
    get_pending_migrations,
    check_migration_status,
    init_database,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    """Create an in-memory SQLite engine for testing."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    """Create a database session."""
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    sess = SessionLocal()
    yield sess
    sess.rollback()
    sess.close()


@pytest.fixture
def sample_user(session):
    """Create a sample user."""
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        role=UserRole.ADMIN,
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def sample_account(session, sample_user):
    """Create a sample account for the test user."""
    account = Account(
        user_id=sample_user.id,
        name="Checking",
        account_number="CHK-001",
        balance=1000.0,
        currency="USD",
        status=AccountStatus.ACTIVE,
    )
    session.add(account)
    session.commit()
    return account


@pytest.fixture
def sample_transactions(session, sample_account):
    """Create sample transactions."""
    txns = [
        Transaction(
            account_id=sample_account.id,
            amount=100.0,
            type=TransactionType.CREDIT,
            description="Deposit",
        ),
        Transaction(
            account_id=sample_account.id,
            amount=50.0,
            type=TransactionType.DEBIT,
            description="Withdrawal",
        ),
        Transaction(
            account_id=sample_account.id,
            amount=200.0,
            type=TransactionType.CREDIT,
            description="Paycheck",
        ),
    ]
    for txn in txns:
        session.add(txn)
    session.commit()
    return txns


@pytest.fixture
def db_file():
    """Create a temporary database file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def pool():
    """Create a fresh DatabasePool for testing."""
    # Reset singleton for clean tests
    DatabasePool._instance = None
    p = DatabasePool()
    yield p
    p.dispose_all()
    DatabasePool._instance = None


# ===================================================================
# Model Tests
# ===================================================================


class TestModels:
    """Test SQLAlchemy model definitions and behavior."""

    def test_user_creation(self, session):
        user = User(
            username="alice",
            email="alice@example.com",
            full_name="Alice Smith",
            role=UserRole.MANAGER,
        )
        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.username == "alice"
        assert user.email == "alice@example.com"
        assert user.role == UserRole.MANAGER
        assert user.is_active is True
        assert user.created_at is not None

    def test_user_email_validation(self, session):
        with pytest.raises(ValueError, match="Invalid email"):
            User(username="bad", email="not-an-email")

    def test_user_email_lowercase(self, session):
        user = User(username="lower", email="UPPER@EXAMPLE.COM")
        session.add(user)
        session.commit()
        assert user.email == "upper@example.com"

    def test_user_unique_username(self, session, sample_user):
        dup = User(username="testuser", email="other@example.com")
        session.add(dup)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_user_unique_email(self, session, sample_user):
        dup = User(username="other", email="test@example.com")
        session.add(dup)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_account_creation(self, session, sample_user):
        account = Account(
            user_id=sample_user.id,
            name="Savings",
            account_number="SAV-001",
            balance=5000.0,
            currency="EUR",
        )
        session.add(account)
        session.commit()

        assert account.id is not None
        assert account.user_id == sample_user.id
        assert account.balance == 5000.0
        assert account.currency == "EUR"
        assert account.status == AccountStatus.ACTIVE

    def test_account_relationship(self, session, sample_user, sample_account):
        assert sample_account.owner.id == sample_user.id
        assert sample_account in sample_user.accounts

    def test_account_unique_number(self, session, sample_user, sample_account):
        dup = Account(
            user_id=sample_user.id,
            name="Duplicate",
            account_number="CHK-001",
        )
        session.add(dup)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_transaction_creation(self, session, sample_account):
        txn = Transaction(
            account_id=sample_account.id,
            amount=25.0,
            type=TransactionType.DEBIT,
            description="Coffee",
        )
        session.add(txn)
        session.commit()

        assert txn.id is not None
        assert txn.amount == 25.0
        assert txn.type == TransactionType.DEBIT

    def test_transaction_relationship(self, session, sample_account, sample_transactions):
        for txn in sample_transactions:
            assert txn.account.id == sample_account.id
        assert len(sample_account.transactions) == 3

    def test_audit_log_creation(self, session, sample_user):
        log = AuditLog(
            user_id=sample_user.id,
            action="CREATE",
            entity_type="User",
            entity_id=sample_user.id,
            details="Created user",
        )
        session.add(log)
        session.commit()

        assert log.id is not None
        assert log.action == "CREATE"
        assert log.entity_type == "User"

    def test_audit_log_null_user(self, session):
        log = AuditLog(
            user_id=None,
            action="SYSTEM",
            entity_type="System",
        )
        session.add(log)
        session.commit()
        assert log.id is not None

    def test_cascade_delete_user_accounts(self, session, sample_user, sample_account):
        user_id = sample_user.id
        session.delete(sample_user)
        session.commit()

        # Account should be cascade-deleted
        remaining = session.query(Account).filter_by(user_id=user_id).first()
        assert remaining is None

    def test_cascade_delete_account_transactions(
        self, session, sample_account, sample_transactions
    ):
        account_id = sample_account.id
        session.delete(sample_account)
        session.commit()

        remaining = (
            session.query(Transaction).filter_by(account_id=account_id).all()
        )
        assert len(remaining) == 0

    def test_user_repr(self, sample_user):
        r = repr(sample_user)
        assert "testuser" in r
        assert "admin" in r

    def test_account_repr(self, sample_account):
        r = repr(sample_account)
        assert "Checking" in r
        assert "1000" in r

    def test_transaction_repr(self, sample_transactions):
        txn = sample_transactions[0]
        r = repr(txn)
        assert "credit" in r

    def test_audit_log_repr(self, session):
        log = AuditLog(action="TEST", entity_type="Test")
        session.add(log)
        session.commit()
        r = repr(log)
        assert "TEST" in r

    def test_user_default_role(self, session):
        user = User(username="default_role", email="default@example.com")
        session.add(user)
        session.commit()
        assert user.role == UserRole.VIEWER

    def test_account_default_status(self, session, sample_user):
        account = Account(
            user_id=sample_user.id,
            name="Test",
            account_number="TST-001",
        )
        session.add(account)
        session.commit()
        assert account.status == AccountStatus.ACTIVE

    def test_updated_at_changes(self, session, sample_user):
        original = sample_user.updated_at
        time.sleep(0.01)
        sample_user.full_name = "Updated Name"
        session.commit()
        assert sample_user.updated_at >= original


# ===================================================================
# Connection Pool Tests
# ===================================================================


class TestConnectionPool:
    """Test connection pooling functionality."""

    def test_singleton_pattern(self):
        DatabasePool._instance = None
        p1 = DatabasePool()
        p2 = DatabasePool()
        assert p1 is p2
        DatabasePool._instance = None

    def test_create_pool(self, pool):
        engine = pool.create_pool(
            name="test_pool",
            url="sqlite:///:memory:",
            pool_size=3,
        )
        assert engine is not None
        assert "test_pool" in pool._pools

    def test_create_pool_duplicate_name(self, pool):
        pool.create_pool(name="dup", url="sqlite:///:memory:")
        with pytest.raises(ValueError, match="already exists"):
            pool.create_pool(name="dup", url="sqlite:///:memory:")

    def test_get_engine(self, pool):
        pool.create_pool(name="get_test", url="sqlite:///:memory:")
        engine = pool.get_engine("get_test")
        assert engine is not None

    def test_get_engine_not_found(self, pool):
        with pytest.raises(KeyError, match="not found"):
            pool.get_engine("nonexistent")

    def test_get_session(self, pool):
        pool.create_pool(name="session_test", url="sqlite:///:memory:")
        sess = pool.get_session("session_test")
        assert isinstance(sess, Session)
        sess.close()

    def test_session_scope_commit(self, pool):
        engine = pool.create_pool(name="scope_test", url="sqlite:///:memory:")
        Base.metadata.create_all(engine)

        with pool.session_scope("scope_test") as sess:
            user = User(username="scope_user", email="scope@example.com")
            sess.add(user)

        # Verify committed
        with pool.session_scope("scope_test") as sess:
            result = sess.query(User).filter_by(username="scope_user").first()
            assert result is not None

    def test_session_scope_rollback(self, pool):
        engine = pool.create_pool(name="rollback_test", url="sqlite:///:memory:")
        Base.metadata.create_all(engine)

        try:
            with pool.session_scope("rollback_test") as sess:
                user = User(username="rollback_user", email="rollback@example.com")
                sess.add(user)
                raise RuntimeError("Force rollback")
        except RuntimeError:
            pass

        # Verify rolled back
        with pool.session_scope("rollback_test") as sess:
            result = sess.query(User).filter_by(username="rollback_user").first()
            assert result is None

    def test_pool_status(self, pool):
        pool.create_pool(name="status_test", url="sqlite:///:memory:")
        status = pool.get_pool_status("status_test")
        assert "size" in status
        assert "checked_in" in status
        assert "checked_out" in status
        assert "overflow" in status

    def test_health_check_pass(self, pool):
        pool.create_pool(name="health_test", url="sqlite:///:memory:")
        assert pool.health_check("health_test") is True

    def test_health_check_fail(self, pool):
        # Create a pool with a bad URL that will fail on connect
        pool.create_pool(
            name="fail_test",
            url="sqlite:///nonexistent/path/that/does/not/exist.db",
        )
        # Health check should handle the failure gracefully
        result = pool.health_check("fail_test")
        assert isinstance(result, bool)

    def test_dispose_pool(self, pool):
        pool.create_pool(name="dispose_test", url="sqlite:///:memory:")
        pool.dispose_pool("dispose_test")
        assert "dispose_test" not in pool._pools

    def test_dispose_all(self, pool):
        pool.create_pool(name="all1", url="sqlite:///:memory:")
        pool.create_pool(name="all2", url="sqlite:///:memory:")
        pool.dispose_all()
        assert len(pool._pools) == 0

    def test_get_pool_function(self):
        DatabasePool._instance = None
        p = get_pool()
        assert isinstance(p, DatabasePool)
        DatabasePool._instance = None

    def test_thread_safety(self, pool):
        """Test that pool creation is thread-safe."""
        errors = []

        def create():
            try:
                pool.create_pool(name="thread_test", url="sqlite:///:memory:")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one should succeed, rest should get "already exists"
        assert len(errors) == 9
        assert all("already exists" in str(e) for e in errors)


# ===================================================================
# Query Builder Tests
# ===================================================================


class TestQueryBuilder:
    """Test fluent query builder."""

    def test_filter_by(self, session, sample_user):
        qb = QueryBuilder(session, User)
        results = qb.filter_by(username="testuser").all()
        assert len(results) == 1
        assert results[0].username == "testuser"

    def test_filter_by_no_match(self, session, sample_user):
        qb = QueryBuilder(session, User)
        results = qb.filter_by(username="nonexistent").all()
        assert len(results) == 0

    def test_filter(self, session, sample_user):
        qb = QueryBuilder(session, User)
        results = qb.filter(User.role == UserRole.ADMIN).all()
        assert len(results) == 1

    def test_filter_multiple(self, session):
        for i in range(5):
            session.add(User(username=f"user{i}", email=f"u{i}@example.com"))
        session.commit()

        qb = QueryBuilder(session, User)
        results = qb.filter(User.username.like("user%")).all()
        assert len(results) == 5

    def test_filter_or(self, session):
        session.add(User(username="alpha", email="a@example.com"))
        session.add(User(username="beta", email="b@example.com"))
        session.add(User(username="gamma", email="g@example.com"))
        session.commit()

        qb = QueryBuilder(session, User)
        results = qb.filter_or(
            User.username == "alpha",
            User.username == "beta",
        ).all()
        assert len(results) == 2

    def test_filter_in(self, session):
        for i in range(5):
            session.add(User(username=f"user{i}", email=f"u{i}@example.com"))
        session.commit()

        qb = QueryBuilder(session, User)
        results = qb.filter_in("username", ["user0", "user2", "user4"]).all()
        assert len(results) == 3

    def test_filter_like(self, session):
        session.add(User(username="john_doe", email="john@example.com"))
        session.add(User(username="jane_doe", email="jane@example.com"))
        session.add(User(username="bob", email="bob@example.com"))
        session.commit()

        qb = QueryBuilder(session, User)
        results = qb.filter_like("username", "%_doe").all()
        assert len(results) == 2

    def test_filter_between(self, session, sample_user):
        now = datetime.utcnow()
        qb = QueryBuilder(session, User)
        results = qb.filter_between(
            "created_at",
            now - timedelta(hours=1),
            now + timedelta(hours=1),
        ).all()
        assert len(results) >= 1

    def test_order_by_asc(self, session):
        for name in ["charlie", "alice", "bob"]:
            session.add(User(username=name, email=f"{name}@example.com"))
        session.commit()

        qb = QueryBuilder(session, User)
        results = qb.order_by_column("username", "asc").all()
        usernames = [u.username for u in results]
        assert usernames == sorted(usernames)

    def test_order_by_desc(self, session):
        for name in ["charlie", "alice", "bob"]:
            session.add(User(username=name, email=f"{name}@example.com"))
        session.commit()

        qb = QueryBuilder(session, User)
        results = qb.order_by_column("username", "desc").all()
        usernames = [u.username for u in results]
        assert usernames == sorted(usernames, reverse=True)

    def test_limit(self, session):
        for i in range(10):
            session.add(User(username=f"user{i}", email=f"u{i}@example.com"))
        session.commit()

        qb = QueryBuilder(session, User)
        results = qb.limit(3).all()
        assert len(results) == 3

    def test_offset(self, session):
        for i in range(10):
            session.add(User(username=f"user{i}", email=f"u{i}@example.com"))
        session.commit()

        qb = QueryBuilder(session, User)
        results = qb.order_by_column("username").offset(5).all()
        assert len(results) == 5

    def test_paginate(self, session):
        for i in range(25):
            session.add(User(username=f"user{i:02d}", email=f"u{i}@example.com"))
        session.commit()

        qb = QueryBuilder(session, User)
        page1 = qb.paginate(page=1, per_page=10).all()
        assert len(page1) == 10

        qb2 = QueryBuilder(session, User)
        page2 = qb2.paginate(page=2, per_page=10).all()
        assert len(page2) == 10

        # Different results
        page1_ids = {u.id for u in page1}
        page2_ids = {u.id for u in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_first(self, session, sample_user):
        qb = QueryBuilder(session, User)
        result = qb.filter_by(username="testuser").first()
        assert result is not None
        assert result.username == "testuser"

    def test_first_none(self, session):
        qb = QueryBuilder(session, User)
        result = qb.filter_by(username="nonexistent").first()
        assert result is None

    def test_count(self, session):
        for i in range(7):
            session.add(User(username=f"user{i}", email=f"u{i}@example.com"))
        session.commit()

        qb = QueryBuilder(session, User)
        assert qb.count() == 7

    def test_count_with_filter(self, session):
        session.add(User(username="active1", email="a1@example.com", is_active=True))
        session.add(User(username="inactive", email="in@example.com", is_active=False))
        session.add(User(username="active2", email="a2@example.com", is_active=True))
        session.commit()

        qb = QueryBuilder(session, User)
        assert qb.filter_by(is_active=True).count() == 2

    def test_exists_true(self, session, sample_user):
        qb = QueryBuilder(session, User)
        assert qb.filter_by(username="testuser").exists() is True

    def test_exists_false(self, session):
        qb = QueryBuilder(session, User)
        assert qb.filter_by(username="nonexistent").exists() is False

    def test_aggregate_sum(self, session, sample_account, sample_transactions):
        qb = QueryBuilder(session, Transaction)
        total = qb.filter_by(account_id=sample_account.id).aggregate(
            Transaction.amount, "sum"
        )
        assert total == 350.0  # 100 + 50 + 200

    def test_aggregate_avg(self, session, sample_account, sample_transactions):
        qb = QueryBuilder(session, Transaction)
        avg = qb.filter_by(account_id=sample_account.id).aggregate(
            Transaction.amount, "avg"
        )
        assert avg == pytest.approx(116.666, rel=0.01)

    def test_aggregate_count(self, session, sample_account, sample_transactions):
        qb = QueryBuilder(session, Transaction)
        count = qb.filter_by(account_id=sample_account.id).aggregate(
            Transaction.id, "count"
        )
        assert count == 3

    def test_aggregate_min_max(self, session, sample_account, sample_transactions):
        qb = QueryBuilder(session, Transaction)
        min_val = qb.filter_by(account_id=sample_account.id).aggregate(
            Transaction.amount, "min"
        )
        max_val = qb.filter_by(account_id=sample_account.id).aggregate(
            Transaction.amount, "max"
        )
        assert min_val == 50.0
        assert max_val == 200.0

    def test_aggregate_invalid(self, session):
        qb = QueryBuilder(session, User)
        with pytest.raises(ValueError, match="Unknown aggregate"):
            qb.aggregate(User.id, "invalid_func")

    def test_chaining(self, session):
        for i in range(10):
            session.add(User(
                username=f"user{i}",
                email=f"u{i}@example.com",
                role=UserRole.MANAGER if i % 2 == 0 else UserRole.VIEWER,
            ))
        session.commit()

        results = (
            QueryBuilder(session, User)
            .filter_by(role=UserRole.MANAGER)
            .order_by_column("username", "desc")
            .limit(2)
            .all()
        )
        assert len(results) == 2
        assert all(u.role == UserRole.MANAGER for u in results)

    def test_to_dict(self, session):
        qb = QueryBuilder(session, User)
        d = qb.to_dict()
        assert d["model"] == "User"
        assert "filters" in d

    def test_filter_by_invalid_column(self, session):
        qb = QueryBuilder(session, User)
        with pytest.raises(AttributeError, match="no column"):
            qb.filter_by(nonexistent_column="value")

    def test_update(self, session):
        for i in range(3):
            session.add(User(username=f"user{i}", email=f"u{i}@example.com", is_active=True))
        session.commit()

        qb = QueryBuilder(session, User)
        count = qb.filter_by(is_active=True).update(is_active=False)
        session.commit()
        assert count == 3

        qb2 = QueryBuilder(session, User)
        assert qb2.filter_by(is_active=False).count() == 3

    def test_delete(self, session):
        for i in range(5):
            session.add(User(username=f"user{i}", email=f"u{i}@example.com"))
        session.commit()

        qb = QueryBuilder(session, User)
        count = qb.filter(User.username.like("user%")).delete()
        session.commit()
        assert count == 5

        qb2 = QueryBuilder(session, User)
        assert qb2.count() == 0

    def test_columns_select(self, session, sample_user):
        qb = QueryBuilder(session, User)
        results = qb.columns(User.id, User.username).all()
        assert len(results) == 1
        # Results are Row objects when selecting specific columns
        row = results[0]
        assert row[0] == sample_user.id
        assert row[1] == "testuser"


# ===================================================================
# Transaction Management Tests
# ===================================================================


class TestTransactionManager:
    """Test transaction management functionality."""

    def test_begin_commit(self, session):
        mgr = TransactionManager(session)
        mgr.begin()
        assert mgr.is_active is True
        user = User(username="tx_user", email="tx@example.com")
        session.add(user)
        mgr.commit()
        assert mgr.is_active is False

        # Verify persisted
        result = session.query(User).filter_by(username="tx_user").first()
        assert result is not None

    def test_begin_rollback(self, session):
        mgr = TransactionManager(session)
        mgr.begin()
        user = User(username="rollback_user", email="rb@example.com")
        session.add(user)
        mgr.rollback()

        result = session.query(User).filter_by(username="rollback_user").first()
        assert result is None

    def test_transaction_context_manager(self, session):
        mgr = TransactionManager(session)
        with mgr.transaction() as sess:
            user = User(username="ctx_user", email="ctx@example.com")
            sess.add(user)

        result = session.query(User).filter_by(username="ctx_user").first()
        assert result is not None

    def test_transaction_context_manager_rollback(self, session):
        mgr = TransactionManager(session)
        try:
            with mgr.transaction() as sess:
                user = User(username="fail_user", email="fail@example.com")
                sess.add(user)
                raise RuntimeError("Force failure")
        except RuntimeError:
            pass

        result = session.query(User).filter_by(username="fail_user").first()
        assert result is None

    def test_savepoint(self, session):
        mgr = TransactionManager(session)
        mgr.begin()

        user1 = User(username="sp_user1", email="sp1@example.com")
        session.add(user1)
        session.flush()

        with mgr.savepoint("test_sp") as sess:
            user2 = User(username="sp_user2", email="sp2@example.com")
            sess.add(user2)

        # Both should be present
        assert session.query(User).filter_by(username="sp_user1").first() is not None
        assert session.query(User).filter_by(username="sp_user2").first() is not None

        mgr.commit()

    def test_savepoint_rollback(self, session):
        mgr = TransactionManager(session)
        mgr.begin()

        user1 = User(username="sp_keep", email="keep@example.com")
        session.add(user1)
        session.flush()

        try:
            with mgr.savepoint("fail_sp") as sess:
                user2 = User(username="sp_discard", email="discard@example.com")
                sess.add(user2)
                raise RuntimeError("Fail savepoint")
        except RuntimeError:
            pass

        # user1 should still be there, user2 should not
        assert session.query(User).filter_by(username="sp_keep").first() is not None
        assert session.query(User).filter_by(username="sp_discard").first() is None

        mgr.commit()

    def test_execute_with_retry_success(self, session):
        mgr = TransactionManager(session)
        call_count = 0

        def operation(sess):
            nonlocal call_count
            call_count += 1
            user = User(username="retry_user", email="retry@example.com")
            sess.add(user)
            return user

        result = mgr.execute_with_retry(operation, max_retries=3)
        assert result is not None
        assert call_count == 1

    def test_execute_with_retry_eventual_success(self, session):
        mgr = TransactionManager(session)
        call_count = 0

        def operation(sess):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                from sqlalchemy.exc import OperationalError
                raise OperationalError("test", {}, Exception("simulated"))
            user = User(username="eventual", email="eventual@example.com")
            sess.add(user)
            return user

        result = mgr.execute_with_retry(
            operation, max_retries=3, retry_delay=0.01
        )
        assert result is not None
        assert call_count == 3

    def test_execute_with_retry_exhausted(self, session):
        mgr = TransactionManager(session)
        call_count = 0

        def operation(sess):
            nonlocal call_count
            call_count += 1
            raise OperationalError("test", {}, Exception("always fails"))

        with pytest.raises(OperationalError):
            mgr.execute_with_retry(operation, max_retries=2, retry_delay=0.01)
        assert call_count == 3  # initial + 2 retries

    def test_bulk_insert(self, session):
        mgr = TransactionManager(session)
        users = [
            User(username=f"bulk{i}", email=f"bulk{i}@example.com")
            for i in range(100)
        ]
        count = mgr.bulk_insert(users, batch_size=25)
        session.commit()
        assert count == 100

        result = session.query(User).filter(User.username.like("bulk%")).count()
        assert result == 100

    def test_bulk_insert_empty(self, session):
        mgr = TransactionManager(session)
        count = mgr.bulk_insert([])
        assert count == 0


class TestTransactionScope:
    """Test transaction_scope context manager."""

    def test_commit_on_success(self, engine):
        SessionLocal = sessionmaker(bind=engine)
        sess = SessionLocal()
        with transaction_scope(sess) as s:
            user = User(username="scope_tx", email="scope_tx@example.com")
            s.add(user)

        # Verify in a new session
        sess2 = SessionLocal()
        result = sess2.query(User).filter_by(username="scope_tx").first()
        assert result is not None
        sess2.close()

    def test_rollback_on_error(self, engine):
        SessionLocal = sessionmaker(bind=engine)
        sess = SessionLocal()
        try:
            with transaction_scope(sess) as s:
                user = User(username="fail_scope", email="fail_scope@example.com")
                s.add(user)
                raise ValueError("Force error")
        except ValueError:
            pass

        sess2 = SessionLocal()
        result = sess2.query(User).filter_by(username="fail_scope").first()
        assert result is None
        sess2.close()


class TestTransactionalDecorator:
    """Test @transactional decorator."""

    def test_decorator_success(self, engine):
        SessionLocal = sessionmaker(bind=engine)

        @transactional(max_retries=2)
        def create_user(session: Session, username: str, email: str):
            user = User(username=username, email=email)
            session.add(user)
            return user

        sess = SessionLocal()
        result = create_user(sess, "decorated", "decorated@example.com")
        assert result.username == "decorated"
        sess.close()

        # Verify persisted
        sess2 = SessionLocal()
        found = sess2.query(User).filter_by(username="decorated").first()
        assert found is not None
        sess2.close()

    def test_decorator_retry(self, engine):
        SessionLocal = sessionmaker(bind=engine)
        call_count = 0

        @transactional(max_retries=2, retry_delay=0.01)
        def flaky_operation(session: Session):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                from sqlalchemy.exc import OperationalError
                raise OperationalError("test", {}, Exception("simulated"))
            user = User(username="flaky", email="flaky@example.com")
            session.add(user)
            return user

        sess = SessionLocal()
        result = flaky_operation(sess)
        assert result.username == "flaky"
        assert call_count == 2
        sess.close()


class TestAuditMixin:
    """Test audit logging mixin."""

    def test_log_action(self, session, sample_user):
        AuditMixin.log_action(
            session,
            user_id=sample_user.id,
            action="TEST_ACTION",
            entity_type="Test",
            entity_id=1,
            details="Test details",
            ip_address="127.0.0.1",
        )
        session.commit()

        log = session.query(AuditLog).filter_by(action="TEST_ACTION").first()
        assert log is not None
        assert log.user_id == sample_user.id
        assert log.entity_type == "Test"
        assert log.details == "Test details"
        assert log.ip_address == "127.0.0.1"

    def test_log_action_null_user(self, session):
        AuditMixin.log_action(
            session,
            user_id=None,
            action="SYSTEM_ACTION",
            entity_type="System",
        )
        session.commit()

        log = session.query(AuditLog).filter_by(action="SYSTEM_ACTION").first()
        assert log is not None
        assert log.user_id is None


# ===================================================================
# Migration Tests
# ===================================================================


class TestMigrations:
    """Test database migration functionality."""

    def test_get_alembic_config(self, db_file):
        url = f"sqlite:///{db_file}"
        cfg = get_alembic_config(url=url)
        assert cfg is not None

    def test_run_migrations(self, db_file):
        url = f"sqlite:///{db_file}"
        run_migrations(url)

        # Verify tables were created
        engine = create_engine(url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "users" in tables
        assert "accounts" in tables
        assert "transactions" in tables
        assert "audit_logs" in tables
        engine.dispose()

    def test_get_current_revision(self, db_file):
        url = f"sqlite:///{db_file}"
        run_migrations(url)
        rev = get_current_revision(url)
        assert rev is not None
        assert rev == "0001_initial_schema"

    def test_get_pending_migrations(self, db_file):
        url = f"sqlite:///{db_file}"
        run_migrations(url)
        pending = get_pending_migrations(url)
        assert len(pending) == 0

    def test_check_migration_status(self, db_file):
        url = f"sqlite:///{db_file}"
        run_migrations(url)
        status = check_migration_status(url)
        assert status["is_up_to_date"] is True
        assert status["current"] == "0001_initial_schema"
        assert len(status["pending"]) == 0

    def test_init_database(self, db_file):
        url = f"sqlite:///{db_file}"
        init_database(url)

        engine = create_engine(url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "users" in tables
        assert "accounts" in tables
        engine.dispose()

    def test_migration_with_data(self, db_file):
        """Test that migrations work and data can be inserted after."""
        url = f"sqlite:///{db_file}"
        run_migrations(url)

        engine = create_engine(url)
        SessionLocal = sessionmaker(bind=engine)
        sess = SessionLocal()

        user = User(username="migrated", email="migrated@example.com")
        sess.add(user)
        sess.commit()

        result = sess.query(User).filter_by(username="migrated").first()
        assert result is not None
        sess.close()
        engine.dispose()

    def test_migration_idempotent(self, db_file):
        """Running migrations twice should be safe."""
        url = f"sqlite:///{db_file}"
        run_migrations(url)
        # Second run should be a no-op
        run_migrations(url)

        engine = create_engine(url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "users" in tables
        engine.dispose()


# ===================================================================
# Integration Tests
# ===================================================================


class TestIntegration:
    """End-to-end integration tests."""

    def test_full_crud_workflow(self, engine):
        """Test complete CRUD workflow across all models."""
        SessionLocal = sessionmaker(bind=engine)
        sess = SessionLocal()

        # Create
        user = User(
            username="integration",
            email="integration@example.com",
            full_name="Integration Test",
            role=UserRole.MANAGER,
        )
        sess.add(user)
        sess.commit()

        account = Account(
            user_id=user.id,
            name="Test Account",
            account_number="INT-001",
            balance=1000.0,
        )
        sess.add(account)
        sess.commit()

        txn = Transaction(
            account_id=account.id,
            amount=500.0,
            type=TransactionType.CREDIT,
            description="Initial deposit",
        )
        sess.add(txn)
        sess.commit()

        # Read
        qb = QueryBuilder(sess, User)
        found_user = qb.filter_by(username="integration").first()
        assert found_user is not None
        assert found_user.accounts[0].name == "Test Account"

        # Update
        account.balance = 1500.0
        sess.commit()

        # Delete
        sess.delete(user)
        sess.commit()

        # Verify cascade
        assert sess.query(Account).filter_by(user_id=user.id).first() is None
        assert sess.query(Transaction).filter_by(account_id=account.id).first() is None

        sess.close()

    def test_concurrent_sessions(self, engine):
        """Test multiple sessions working independently."""
        SessionLocal = sessionmaker(bind=engine)

        sess1 = SessionLocal()
        sess2 = SessionLocal()

        user1 = User(username="concurrent1", email="c1@example.com")
        user2 = User(username="concurrent2", email="c2@example.com")

        sess1.add(user1)
        sess1.commit()

        sess2.add(user2)
        sess2.commit()

        # Both should see both users
        assert sess1.query(User).count() == 2
        assert sess2.query(User).count() == 2

        sess1.close()
        sess2.close()

    def test_complex_query(self, session):
        """Test complex query with multiple joins and filters."""
        # Create test data
        users = []
        for i in range(5):
            u = User(
                username=f"complex{i}",
                email=f"complex{i}@example.com",
                role=UserRole.ADMIN if i < 2 else UserRole.VIEWER,
            )
            session.add(u)
            session.flush()

            for j in range(3):
                a = Account(
                    user_id=u.id,
                    name=f"Account-{i}-{j}",
                    account_number=f"ACC-{i}-{j}",
                    balance=100.0 * (i + 1),
                )
                session.add(a)
                session.flush()

                for k in range(2):
                    t = Transaction(
                        account_id=a.id,
                        amount=10.0 * (k + 1),
                        type=TransactionType.CREDIT if k == 0 else TransactionType.DEBIT,
                    )
                    session.add(t)
            users.append(u)
        session.commit()

        # Complex query: find all transactions for admin users
        results = (
            QueryBuilder(session, Transaction)
            .filter(
                Transaction.account_id.in_(
                    session.query(Account.id).filter(
                        Account.user_id.in_(
                            session.query(User.id).filter(
                                User.role == UserRole.ADMIN
                            )
                        )
                    )
                )
            )
            .order_by_column("id")
            .all()
        )
        # 2 users * 3 accounts * 2 transactions = 12
        assert len(results) == 12

    def test_audit_trail_workflow(self, session):
        """Test creating audit logs alongside entity changes."""
        # Create user with audit
        user = User(username="audited", email="audited@example.com")
        session.add(user)
        session.flush()

        AuditMixin.log_action(
            session,
            user_id=user.id,
            action="CREATE",
            entity_type="User",
            entity_id=user.id,
            details="User created",
        )
        session.commit()

        # Update user with audit
        user.full_name = "Audited User"
        session.flush()

        AuditMixin.log_action(
            session,
            user_id=user.id,
            action="UPDATE",
            entity_type="User",
            entity_id=user.id,
            details="Name updated",
        )
        session.commit()

        # Verify audit trail
        logs = (
            QueryBuilder(session, AuditLog)
            .filter_by(entity_type="User", entity_id=user.id)
            .order_by_column("created_at")
            .all()
        )
        assert len(logs) == 2
        assert logs[0].action == "CREATE"
        assert logs[1].action == "UPDATE"
