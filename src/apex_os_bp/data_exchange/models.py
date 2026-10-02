"""Data models for the data exchange module."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Column:
    """Schema column definition."""
    name: str
    data_type: str = "string"  # string, integer, float, boolean, date
    required: bool = False
    default: Any = None
    description: str = ""


@dataclass
class DataSchema:
    """Schema definition for tabular data."""
    name: str
    columns: List[Column] = field(default_factory=list)

    def get_column(self, name: str) -> Optional[Column]:
        """Get column by name."""
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def validate_record(self, record: Dict[str, Any]) -> List[str]:
        """Validate a record against the schema. Returns list of error messages."""
        errors = []
        for col in self.columns:
            if col.required and col.name not in record:
                errors.append(f"Missing required column: {col.name}")
            elif col.name in record and record[col.name] is not None:
                value = record[col.name]
                type_error = self._validate_type(col, value)
                if type_error:
                    errors.append(type_error)
        return errors

    def _validate_type(self, col: Column, value: Any) -> Optional[str]:
        """Validate a value against a column's data type."""
        if value is None:
            return None
        try:
            if col.data_type == "integer":
                int(value)
            elif col.data_type == "float":
                float(value)
            elif col.data_type == "boolean":
                if not isinstance(value, (bool, int, str)):
                    return f"Column '{col.name}': expected boolean, got {type(value).__name__}"
                if isinstance(value, str) and value.lower() not in ("true", "false", "1", "0", "yes", "no"):
                    return f"Column '{col.name}': invalid boolean value '{value}'"
            elif col.data_type == "string":
                str(value)
            elif col.data_type == "date":
                from datetime import datetime
                if isinstance(value, str):
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError) as e:
            return f"Column '{col.name}': type validation failed - {e}"
        return None


@dataclass
class DataRecord:
    """A single data record (row)."""
    data: Dict[str, Any] = field(default_factory=dict)
    row_number: int = 0
    source: str = ""

    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set value by key."""
        self.data[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return dict(self.data)


@dataclass
class ImportResult:
    """Result of an import operation."""
    success: bool
    records_imported: int = 0
    records_failed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "records_imported": self.records_imported,
            "records_failed": self.records_failed,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }
