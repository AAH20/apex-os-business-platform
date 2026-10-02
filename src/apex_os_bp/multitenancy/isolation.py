"""Tenant isolation — ensures data and operations are scoped to the correct tenant."""

from __future__ import annotations

import contextlib
import contextvars
import functools
import threading
from collections.abc import Callable, Generator, Iterable, Sequence
from typing import Any, Optional, TypeVar

from apex_os_bp.multitenancy.models import Tenant, TenantStatus

T = TypeVar("T")


class TenantIsolationError(Exception):
    """Raised when a tenant isolation boundary is violated."""

    def __init__(self, message: str, tenant_id: Optional[str] = None) -> None:
        super().__init__(message)
        self.tenant_id = tenant_id


# Thread-local + contextvars hybrid for async and sync safety
_tenant_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "tenant_id", default=None
)
_tenant_stack: contextvars.ContextVar[list[str]] = contextvars.ContextVar(
    "tenant_stack", default=[]
)
_thread_local = threading.local()


def get_current_tenant() -> Optional[str]:
    """Return the current tenant ID from context, or None if not set."""
    tenant_id = _tenant_context.get()
    if tenant_id is not None:
        return tenant_id
    return getattr(_thread_local, "tenant_id", None)


def set_current_tenant(tenant_id: str) -> None:
    """Set the current tenant ID for the active context."""
    _tenant_context.set(tenant_id)
    _thread_local.tenant_id = tenant_id


def clear_current_tenant() -> None:
    """Clear the current tenant ID."""
    _tenant_context.set(None)
    _thread_local.tenant_id = None


@contextlib.contextmanager
def TenantContext(tenant_id: str) -> Generator[str, None, None]:
    """Context manager that scopes operations to a specific tenant.

    Usage:
        with TenantContext("tenant-123"):
            # All operations here are scoped to tenant-123
            ...
    """
    if not tenant_id:
        raise TenantIsolationError("Tenant ID cannot be empty")

    token = _tenant_context.set(tenant_id)
    _thread_local.tenant_id = tenant_id
    try:
        yield tenant_id
    finally:
        _tenant_context.reset(token)
        _thread_local.tenant_id = None


def require_tenant(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator that requires a tenant context to be active.

    Raises TenantIsolationError if no tenant is set.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        tenant_id = get_current_tenant()
        if tenant_id is None:
            raise TenantIsolationError(
                f"Function '{func.__name__}' requires an active tenant context"
            )
        return func(*args, **kwargs)

    return wrapper


def tenant_scoped_query(
    records: Sequence[T],
    tenant_id: Optional[str] = None,
    tenant_attr: str = "tenant_id",
) -> list[T]:
    """Filter a sequence of records to only those belonging to the current tenant.

    Args:
        records: The records to filter.
        tenant_id: Explicit tenant ID. If None, uses the current context tenant.
        tenant_attr: The attribute name on each record that holds the tenant ID.

    Returns:
        Filtered list of records belonging to the tenant.

    Raises:
        TenantIsolationError: If no tenant context is active and no tenant_id given.
    """
    effective_tenant = tenant_id or get_current_tenant()
    if effective_tenant is None:
        raise TenantIsolationError(
            "Cannot scope query: no tenant context active"
        )

    return [
        record
        for record in records
        if getattr(record, tenant_attr, None) == effective_tenant
    ]


class TenantAwareRepository:
    """Base repository that enforces tenant isolation on all queries."""

    def __init__(self, tenant_id: Optional[str] = None) -> None:
        self._tenant_id = tenant_id or get_current_tenant()
        if self._tenant_id is None:
            raise TenantIsolationError(
                "TenantAwareRepository requires a tenant context"
            )

    @property
    def tenant_id(self) -> str:
        return self._tenant_id  # type: ignore[return-value]

    def filter_by_tenant(self, records: Iterable[T], tenant_attr: str = "tenant_id") -> list[T]:
        """Filter records to only those belonging to this repository's tenant."""
        return [
            r for r in records if getattr(r, tenant_attr, None) == self._tenant_id
        ]

    def assert_tenant(self, record: Any, tenant_attr: str = "tenant_id") -> None:
        """Assert that a record belongs to this repository's tenant."""
        record_tenant = getattr(record, tenant_attr, None)
        if record_tenant != self._tenant_id:
            raise TenantIsolationError(
                f"Record tenant '{record_tenant}' does not match repository tenant '{self._tenant_id}'",
                tenant_id=self._tenant_id,
            )


class TenantBoundary:
    """Enforces that operations cannot cross tenant boundaries."""

    @staticmethod
    def validate_same_tenant(
        source_tenant_id: str,
        target_tenant_id: str,
        operation: str = "operation",
    ) -> None:
        """Validate that source and target are the same tenant."""
        if source_tenant_id != target_tenant_id:
            raise TenantIsolationError(
                f"Cross-tenant {operation} is not allowed: "
                f"'{source_tenant_id}' -> '{target_tenant_id}'",
                tenant_id=source_tenant_id,
            )

    @staticmethod
    def validate_tenant_access(
        user_tenant_id: str,
        resource_tenant_id: str,
    ) -> None:
        """Validate that a user can access a resource in their tenant."""
        if user_tenant_id != resource_tenant_id:
            raise TenantIsolationError(
                f"Access denied: user tenant '{user_tenant_id}' "
                f"cannot access resource in tenant '{resource_tenant_id}'",
                tenant_id=user_tenant_id,
            )
