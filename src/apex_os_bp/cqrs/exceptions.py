"""Custom exceptions for the CQRS system."""


class CQRSException(Exception):
    """Base exception for all CQRS-related errors."""


class CommandValidationError(CQRSException):
    """Raised when a command fails validation."""


class QueryValidationError(CQRSException):
    """Raised when a query fails validation."""


class EventValidationError(CQRSException):
    """Raised when an event fails validation."""


class HandlerNotFoundError(CQRSException):
    """Raised when no handler is registered for a command/query/event."""


class ConcurrencyError(CQRSException):
    """Raised when an optimistic concurrency check fails."""


class AggregateNotFoundError(CQRSException):
    """Raised when an aggregate root is not found."""


class EventStoreError(CQRSException):
    """Raised when the event store encounters an error."""
