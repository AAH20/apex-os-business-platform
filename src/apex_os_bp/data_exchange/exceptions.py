"""Exceptions for the data exchange module."""
from __future__ import annotations


class DataExchangeError(Exception):
    """Base exception for all data exchange errors."""
    pass


class ImportError(DataExchangeError):
    """Raised when data import fails."""
    pass


class ExportError(DataExchangeError):
    """Raised when data export fails."""
    pass


class ValidationError(DataExchangeError):
    """Raised when data validation fails."""
    pass
