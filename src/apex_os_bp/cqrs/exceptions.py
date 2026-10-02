"""Custom exceptions for the CQRS system."""


class CQRSException(Exception):
    """Base exception for all CQRS-related errors."""
    pass


class CommandValidationError(CQRSException):
    """Raised when a command fails validation."""
    pass


class QueryValidationError(CQRSException):
    """Raised when a query fails validation."""
    pass


class EventValidationError(CQRSException):
    """Raised when an event fails validation."""
    pass


class HandlerNotFoundError(CQRSException):
    """Raised when no handler is registered for a command/query/event."""
    pass


class ConcurrencyError(CQRSException):
    """Raised when an optimistic concurrency check fails."""
    pass


class AggregateNotFoundError(CQRSException):
    """Raised when an aggregate root is not found."""
    pass


class EventStoreError(CQRSException):
    """Raised when the event store encounters an error."""
    pass
