"""Error Handling — structured error capture, classification, and recovery."""

from __future__ import annotations

import asyncio
import time
import traceback
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Optional


class ErrorSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    NETWORK = "network"
    TIMEOUT = "timeout"
    AUTH = "auth"
    VALIDATION = "validation"
    RATE_LIMIT = "rate_limit"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


@dataclass
class ErrorRecord:
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    severity: ErrorSeverity = ErrorSeverity.ERROR
    category: ErrorCategory = ErrorCategory.UNKNOWN
    message: str = ""
    source: str = ""
    operation: str = ""
    exception_type: str = ""
    stack_trace: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    resolved: bool = False
    resolution: Optional[str] = None
    related_error_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "source": self.source,
            "operation": self.operation,
            "exception_type": self.exception_type,
            "stack_trace": self.stack_trace,
            "context": self.context,
            "retry_count": self.retry_count,
            "resolved": self.resolved,
            "resolution": self.resolution,
            "related_error_id": self.related_error_id,
        }


@dataclass
class ErrorPolicy:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_categories: set[ErrorCategory] = field(default_factory=lambda: {
        ErrorCategory.NETWORK,
        ErrorCategory.TIMEOUT,
        ErrorCategory.RATE_LIMIT,
    })
    fatal_categories: set[ErrorCategory] = field(default_factory=lambda: {
        ErrorCategory.AUTH,
        ErrorCategory.VALIDATION,
    })
    on_error: Optional[Callable[[ErrorRecord], None]] = None
    on_retry: Optional[Callable[[ErrorRecord, int], None]] = None
    on_fatal: Optional[Callable[[ErrorRecord], None]] = None

    def should_retry(self, record: ErrorRecord) -> bool:
        if record.category in self.fatal_categories:
            return False
        if record.category in self.retryable_categories:
            return record.retry_count < self.max_retries
        return record.retry_count < self.max_retries

    def get_delay(self, retry_count: int) -> float:
        import random
        delay = min(
            self.base_delay * (self.exponential_base ** retry_count),
            self.max_delay,
        )
        if self.jitter:
            delay *= (0.5 + random.random())
        return delay


class ErrorHandler:
    """Centralized error handling with classification, retry, and recovery."""

    def __init__(self, policy: Optional[ErrorPolicy] = None):
        self.policy = policy or ErrorPolicy()
        self._records: list[ErrorRecord] = []
        self._max_records: int = 10000
        self._error_counts: dict[str, int] = {}
        self._circuit_breakers: dict[str, dict] = {}
        self._recovery_strategies: dict[ErrorCategory, Callable] = {}

    def register_recovery(
        self, category: ErrorCategory, strategy: Callable[[ErrorRecord], Awaitable[Any]]
    ) -> None:
        self._recovery_strategies[category] = strategy

    def _classify_exception(self, exc: Exception) -> ErrorCategory:
        exc_name = type(exc).__name__.lower()
        exc_msg = str(exc).lower()

        if "timeout" in exc_name or "timeout" in exc_msg:
            return ErrorCategory.TIMEOUT
        if "connection" in exc_name or "network" in exc_name:
            return ErrorCategory.NETWORK
        if "auth" in exc_name or "unauthorized" in exc_msg or "forbidden" in exc_msg:
            return ErrorCategory.AUTH
        if "rate" in exc_name or "429" in exc_msg or "throttle" in exc_msg:
            return ErrorCategory.RATE_LIMIT
        if "not found" in exc_msg or "404" in exc_msg:
            return ErrorCategory.NOT_FOUND
        if "conflict" in exc_msg or "409" in exc_msg:
            return ErrorCategory.CONFLICT
        if "validation" in exc_name or "invalid" in exc_msg or "schema" in exc_msg:
            return ErrorCategory.VALIDATION
        return ErrorCategory.UNKNOWN

    def _get_severity(self, category: ErrorCategory) -> ErrorSeverity:
        mapping = {
            ErrorCategory.NETWORK: ErrorSeverity.WARNING,
            ErrorCategory.TIMEOUT: ErrorSeverity.WARNING,
            ErrorCategory.RATE_LIMIT: ErrorSeverity.INFO,
            ErrorCategory.AUTH: ErrorSeverity.ERROR,
            ErrorCategory.VALIDATION: ErrorSeverity.WARNING,
            ErrorCategory.NOT_FOUND: ErrorSeverity.INFO,
            ErrorCategory.CONFLICT: ErrorSeverity.WARNING,
            ErrorCategory.INTERNAL: ErrorSeverity.CRITICAL,
            ErrorCategory.UNKNOWN: ErrorSeverity.ERROR,
        }
        return mapping.get(category, ErrorSeverity.ERROR)

    def _check_circuit_breaker(self, source: str) -> bool:
        """Return True if circuit is open (should reject)."""
        cb = self._circuit_breakers.get(source)
        if not cb:
            return False
        if cb["open"]:
            if time.time() - cb["opened_at"] > cb["timeout"]:
                cb["open"] = False
                cb["failures"] = 0
                return False
            return True
        return False

    def _record_failure(self, source: str) -> None:
        if source not in self._circuit_breakers:
            self._circuit_breakers[source] = {
                "open": False,
                "failures": 0,
                "opened_at": 0.0,
                "timeout": 60.0,
            }
        cb = self._circuit_breakers[source]
        cb["failures"] += 1
        if cb["failures"] >= 5:
            cb["open"] = True
            cb["opened_at"] = time.time()

    def _record_success(self, source: str) -> None:
        if source in self._circuit_breakers:
            self._circuit_breakers[source]["failures"] = 0
            self._circuit_breakers[source]["open"] = False

    def capture(
        self,
        exc: Exception,
        source: str = "",
        operation: str = "",
        context: Optional[dict] = None,
    ) -> ErrorRecord:
        """Capture and classify an exception."""
        category = self._classify_exception(exc)
        record = ErrorRecord(
            severity=self._get_severity(category),
            category=category,
            message=str(exc),
            source=source,
            operation=operation,
            exception_type=type(exc).__name__,
            stack_trace=traceback.format_exc(),
            context=context or {},
        )

        self._records.append(record)
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

        key = f"{source}:{category.value}"
        self._error_counts[key] = self._error_counts.get(key, 0) + 1

        if self.policy.on_error:
            self.policy.on_error(record)

        return record

    async def execute(
        self,
        fn: Callable[..., Awaitable[Any]],
        *args,
        source: str = "",
        operation: str = "",
        context: Optional[dict] = None,
        **kwargs,
    ) -> Any:
        """Execute a function with error handling and retry logic."""
        if self._check_circuit_breaker(source):
            raise Exception(f"Circuit breaker open for '{source}'")

        last_exc: Optional[Exception] = None

        for attempt in range(self.policy.max_retries + 1):
            try:
                result = await fn(*args, **kwargs)
                self._record_success(source)
                return result
            except Exception as exc:
                last_exc = exc
                record = self.capture(exc, source, operation, context)
                record.retry_count = attempt

                if not self.policy.should_retry(record):
                    self._record_failure(source)
                    if self.policy.on_fatal:
                        self.policy.on_fatal(record)
                    raise

                if attempt < self.policy.max_retries:
                    delay = self.policy.get_delay(attempt)
                    if self.policy.on_retry:
                        self.policy.on_retry(record, attempt + 1)
                    await asyncio.sleep(delay)

        self._record_failure(source)
        raise last_exc  # type: ignore[misc]

    async def attempt_recovery(self, record: ErrorRecord) -> bool:
        """Attempt to recover from an error using registered strategy."""
        strategy = self._recovery_strategies.get(record.category)
        if not strategy:
            return False
        try:
            await strategy(record)
            record.resolved = True
            record.resolution = f"Recovered via {record.category.value} strategy"
            return True
        except Exception:
            return False

    def get_errors(
        self,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
        source: str = "",
        limit: int = 100,
    ) -> list[ErrorRecord]:
        """Query error records with optional filters."""
        records = self._records
        if severity:
            records = [r for r in records if r.severity == severity]
        if category:
            records = [r for r in records if r.category == category]
        if source:
            records = [r for r in records if r.source == source]
        return records[-limit:]

    def get_error_counts(self) -> dict[str, int]:
        return dict(self._error_counts)

    def get_circuit_breaker_status(self) -> dict[str, dict]:
        return {k: dict(v) for k, v in self._circuit_breakers.items()}

    def resolve_error(self, error_id: str, resolution: str = "") -> bool:
        """Mark an error as resolved."""
        for record in self._records:
            if record.error_id == error_id:
                record.resolved = True
                record.resolution = resolution
                return True
        return False

    def clear(self) -> None:
        self._records.clear()
        self._error_counts.clear()
        self._circuit_breakers.clear()
