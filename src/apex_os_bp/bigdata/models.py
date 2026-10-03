"""Core data models for the Big Data module."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DataType(str, Enum):
    """Supported column data types."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    TIMESTAMP = "timestamp"


@dataclass
class Column:
    """Schema definition for a single column."""

    name: str
    dtype: DataType
    nullable: bool = True
    description: str = ""

    def validate_value(self, value: Any) -> bool:
        """Check that *value* is compatible with this column's type."""
        if value is None:
            return self.nullable
        if self.dtype is DataType.STRING:
            return isinstance(value, str)
        if self.dtype is DataType.INTEGER:
            return isinstance(value, int) and not isinstance(value, bool)
        if self.dtype is DataType.FLOAT:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if self.dtype is DataType.BOOLEAN:
            return isinstance(value, bool)
        if self.dtype is DataType.TIMESTAMP:
            return isinstance(value, (int, float, str))
        return False


@dataclass
class Partition:
    """A horizontal slice of a table keyed by a partition column."""

    key: str
    rows: list[dict[str, Any]] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.rows)


@dataclass
class Table:
    """A named collection of columns and row partitions."""

    name: str
    columns: list[Column]
    partitions: dict[str, Partition] = field(default_factory=dict)

    @property
    def schema(self) -> dict[str, DataType]:
        return {c.name: c.dtype for c in self.columns}

    def add_partition(self, key: str, rows: list[dict[str, Any]]) -> None:
        """Append a partition, validating every row against the schema."""
        col_map = {c.name: c for c in self.columns}
        for row in rows:
            for col_name, value in row.items():
                if col_name not in col_map:
                    raise ValueError(f"Unknown column '{col_name}' in table '{self.name}'")
                if not col_map[col_name].validate_value(value):
                    raise ValueError(
                        f"Invalid value {value!r} for column '{col_name}' "
                        f"(type {col_map[col_name].dtype.value})"
                    )
        self.partitions[key] = Partition(key=key, rows=list(rows))

    @property
    def row_count(self) -> int:
        return sum(len(p) for p in self.partitions.values())


@dataclass
class Dataset:
    """Top-level container grouping related tables."""

    name: str
    tables: dict[str, Table] = field(default_factory=dict)

    def add_table(self, table: Table) -> None:
        self.tables[table.name] = table

    def get_table(self, name: str) -> Table | None:
        return self.tables.get(name)
