"""Database layer for APEX-OS Business Platform.

Provides SQLAlchemy models, migrations, connection pooling,
query builder, and transaction management.
"""

from apex_os_bp.database.models import Base, User, Account, Transaction, AuditLog
from apex_os_bp.database.pool import DatabasePool, get_pool
from apex_os_bp.database.query_builder import QueryBuilder
from apex_os_bp.database.transactions import TransactionManager, transaction_scope

__all__ = [
    "Base",
    "User",
    "Account",
    "Transaction",
    "AuditLog",
    "DatabasePool",
    "get_pool",
    "QueryBuilder",
    "TransactionManager",
    "transaction_scope",
]
