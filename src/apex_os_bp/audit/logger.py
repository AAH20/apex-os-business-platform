"""Audit logging — records security and operational events."""
from __future__ import annotations

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Optional

from .models import AuditEvent, AuditSeverity, AuditStatus
from .store import AuditStore, InMemoryAuditStore


class AuditLogger:
    """Primary interface for recording audit events."""

    def __init__(self, store: Optional[AuditStore] = None) -> None:
        self._store = store if store is not None else InMemoryAuditStore()

    @property
    def store(self) -> AuditStore:
        return self._store

    def log(
        self,
        action: str,
        *,
        actor: str = "system",
        resource: str = "",
        resource_type: str = "",
        metadata: Optional[dict[str, Any]] = None,
        severity: AuditSeverity = AuditSeverity.WARNING,
        status: AuditStatus = AuditStatus.SUCCESS,
        correlation_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> AuditEvent:
        """Record an audit event."""
        event = AuditEvent(
            actor=actor,
            action=action,
            resource=resource,
            resource_type=resource_type,
            metadata=metadata or {},
            severity=severity,
            status=status,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
            duration_ms=duration_ms,
        )
        self._store.append(event)
        return event

    @contextmanager
    def context(self, action: str, **kwargs: Any):
        """Context manager that logs entry and exit of a block."""
        start = time.monotonic()
        event = self.log(action, **kwargs)
        try:
            yield event
        except Exception as exc:
            self.log(
                action,
                status=AuditStatus.FAILURE,
                severity=AuditSeverity.ERROR,
                metadata={"error": str(exc), "original_event_id": event.id},
                **{k: v for k, v in kwargs.items() if k != "metadata"},
            )
            raise
        finally:
            elapsed = (time.monotonic() - start) * 1000
            event.duration_ms = elapsed

    def decorator(self, action: str, **kwargs: Any) -> Callable:
        """Decorator that logs function execution."""

        def wrapper(func: Callable) -> Callable:
            @functools.wraps(func)
            def inner(*args: Any, **func_kwargs: Any) -> Any:
                start = time.monotonic()
                try:
                    result = func(*args, **func_kwargs)
                    self.log(
                        action,
                        status=AuditStatus.SUCCESS,
                        duration_ms=(time.monotonic() - start) * 1000,
                        **kwargs,
                    )
                    return result
                except Exception as exc:
                    self.log(
                        action,
                        status=AuditStatus.FAILURE,
                        severity=AuditSeverity.ERROR,
                        metadata={"error": str(exc)},
                        duration_ms=(time.monotonic() - start) * 1000,
                        **{k: v for k, v in kwargs.items() if k != "metadata"},
                    )
                    raise

            return inner

        return wrapper
