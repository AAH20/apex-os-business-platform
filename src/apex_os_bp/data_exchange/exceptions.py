"""Exceptions for the data exchange module."""
from __future__ import annotations


class DataExchangeError(Exception):
    """Base exception for all data exchange errors."""


class ImportError(DataExchangeError):
    """Raised when data import fails."""


class ExportError(DataExchangeError):
    """Raised when data export fails."""


class ValidationError(DataExchangeError):
    """Raised when data validation fails."""
