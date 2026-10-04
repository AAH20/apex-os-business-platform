"""Transaction management for database operations.

Provides context managers and decorators for handling transactions
with automatic commit/rollback, nested transactions (savepoints),
and retry logic.
"""

from __future__ import annotations

import functools
import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, Generator, Optional, TypeVar

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class TransactionManager:
    """Manages database transactions with savepoint support.

    Provides methods for beginning, committing, and rolling back
    transactions, as well as nested transaction support.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._savepoint_count = 0

    @property
    def session(self) -> Session:
        """Get the underlying SQLAlchemy session."""
        return self._session

    @property
    def is_active(self) -> bool:
        """Check if a transaction is currently active."""
        return self._session.in_transaction()

    def begin(self) -> None:
        """Begin a new transaction."""
        if not self.is_active:
            self._session.begin()
            logger.debug("Transaction started")

    def commit(self) -> None:
        """Commit the current transaction."""
        if self.is_active:
            self._session.commit()
            logger.debug("Transaction committed")

    def rollback(self) -> None:
        """Roll back the current transaction."""
        if self.is_active:
            self._session.rollback()
            logger.debug("Transaction rolled back")

    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """Context manager for a transaction block.

        Commits on success, rolls back on exception.
        """
        try:
            with self._session.begin():
                yield self._session
            logger.debug("Transaction committed successfully")
        except SQLAlchemyError as e:
            logger.error(f"Transaction failed, rolling back: {e}")
            raise

    @contextmanager
    def savepoint(self, name: Optional[str] = None) -> Generator[Session, None, None]:
        """Context manager for a nested transaction (savepoint).

        Args:
            name: Optional savepoint name. Auto-generated if not provided.
        """
        if not self.is_active:
            # No active transaction; start one
            with self.transaction() as session:
                yield session
            return

        self._savepoint_count += 1
        sp_name = name or f"sp_{self._savepoint_count}"
        try:
            with self._session.begin_nested():
                logger.debug(f"Savepoint '{sp_name}' created")
                yield self._session
            logger.debug(f"Savepoint '{sp_name}' released")
        except SQLAlchemyError as e:
            logger.error(f"Savepoint '{sp_name}' failed: {e}")
            raise

    def execute_with_retry(
        self,
        operation: Callable[[Session], Any],
        max_retries: int = 3,
        retry_delay: float = 0.1,
        retry_exceptions: tuple = (OperationalError,),
    ) -> Any:
        """Execute an operation with automatic retry on failure.

        Args:
            operation: Callable that takes a Session and returns a result.
            max_retries: Maximum number of retry attempts.
            retry_delay: Initial delay between retries (exponential backoff).
            retry_exceptions: Tuple of exception types to retry on.

        Returns:
            The result of the operation.

        Raises:
            The last exception if all retries are exhausted.
        """
        last_exception: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                with self.transaction() as session:
                    return operation(session)
            except retry_exceptions as e:
                last_exception = e
                if attempt < max_retries:
                    delay = retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Operation failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Operation failed after {max_retries + 1} attempts: {e}")
        raise last_exception  # type: ignore[misc]

    def bulk_insert(self, objects: list, batch_size: int = 1000) -> int:
        """Efficiently insert multiple objects in batches.

        Args:
            objects: List of ORM objects to insert.
            batch_size: Number of objects per batch.

        Returns:
            Total number of objects inserted.
        """
        if not objects:
            return 0

        total = 0
        for i in range(0, len(objects), batch_size):
            batch = objects[i : i + batch_size]
            self._session.bulk_save_objects(batch)
            total += len(batch)
            logger.debug(f"Bulk inserted batch of {len(batch)} objects")
        return total

    def bulk_update(self, mappings: list[dict], batch_size: int = 1000) -> int:
        """Efficiently update multiple rows in batches.

        Args:
            mappings: List of dicts with column values to update.
            batch_size: Number of rows per batch.

        Returns:
            Total number of rows updated.
        """
        if not mappings:
            return 0

        total = 0
        for i in range(0, len(mappings), batch_size):
            batch = mappings[i : i + batch_size]
            self._session.bulk_update_mappings(self._session.bind.mappers[0].class_, batch)
            total += len(batch)
            logger.debug(f"Bulk updated batch of {len(batch)} rows")
        return total


@contextmanager
def transaction_scope(session: Session) -> Generator[Session, None, None]:
    """Simple transaction scope context manager.

    Commits on success, rolls back on exception, always closes.

    Args:
        session: SQLAlchemy session to manage.

    Yields:
        The session for use within the block.
    """
    try:
        yield session
        session.commit()
        logger.debug("Transaction scope committed")
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Transaction scope rolled back: {e}")
        raise
    finally:
        session.close()


def transactional(
    max_retries: int = 3,
    retry_delay: float = 0.1,
) -> Callable[[F], F]:
    """Decorator that wraps a function in a transaction.

    The decorated function must accept a Session as its first argument.

    Args:
        max_retries: Maximum retry attempts on failure.
        retry_delay: Initial delay between retries.

    Returns:
        Decorated function.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(session: Session, *args: Any, **kwargs: Any) -> Any:
            manager = TransactionManager(session)
            return manager.execute_with_retry(
                lambda s: func(s, *args, **kwargs),
                max_retries=max_retries,
                retry_delay=retry_delay,
            )

        return wrapper  # type: ignore[return-value]

    return decorator


class AuditMixin:
    """Mixin that adds audit logging to model operations."""

    @staticmethod
    def log_action(
        session: Session,
        user_id: Optional[int],
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Create an audit log entry."""
        from apex_os_bp.database.models import AuditLog

        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
        )
        session.add(log_entry)
