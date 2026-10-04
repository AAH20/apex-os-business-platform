"""Data modeling module for data warehouse.

Provides star schema, dimension, fact table, column, and relationship
definitions for dimensional modeling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DataType(Enum):
    """Supported data types for columns."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    DECIMAL = "decimal"
    TEXT = "text"
    JSON = "json"
    BINARY = "binary"
    UUID = "uuid"


@dataclass
class Column:
    """Represents a column in a table."""

    name: str
    data_type: DataType
    nullable: bool = True
    primary_key: bool = False
    foreign_key: Optional[str] = None
    unique: bool = False
    default: Any = None
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def validate_value(self, value: Any) -> bool:
        """Validate a value against this column's data type."""
        if value is None:
            return self.nullable

        type_checks = {
            DataType.STRING: lambda v: isinstance(v, str),
            DataType.INTEGER: lambda v: isinstance(v, int) and not isinstance(v, bool),
            DataType.FLOAT: lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            DataType.BOOLEAN: lambda v: isinstance(v, bool),
            DataType.DATE: lambda v: isinstance(v, str),  # ISO format date
            DataType.DATETIME: lambda v: isinstance(v, str),  # ISO format datetime
            DataType.TIMESTAMP: lambda v: isinstance(v, (int, float)),
            DataType.DECIMAL: lambda v: isinstance(v, (int, float)),
            DataType.TEXT: lambda v: isinstance(v, str),
            DataType.JSON: lambda v: isinstance(v, (dict, list)),
            DataType.BINARY: lambda v: isinstance(v, bytes),
            DataType.UUID: lambda v: isinstance(v, str),
        }

        check = type_checks.get(self.data_type)
        return check(value) if check else True


@dataclass
class Relationship:
    """Represents a relationship between tables."""

    name: str
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    relationship_type: str = "many_to_one"  # one_to_one, one_to_many, many_to_one, many_to_many

    def validate(self, tables: Dict[str, Any]) -> bool:
        """Validate that both tables and columns exist."""
        if self.source_table not in tables or self.target_table not in tables:
            return False
        source_cols = {c.name for c in tables[self.source_table].columns}
        target_cols = {c.name for c in tables[self.target_table].columns}
        return self.source_column in source_cols and self.target_column in target_cols


@dataclass
class Dimension:
    """Represents a dimension table in star schema."""

    name: str
    columns: List[Column] = field(default_factory=list)
    description: str = ""
    slowly_changing_dimension: bool = False
    scd_type: Optional[int] = None  # 1, 2, or 3

    @property
    def primary_key(self) -> Optional[Column]:
        """Get the primary key column."""
        for col in self.columns:
            if col.primary_key:
                return col
        return None

    @property
    def column_names(self) -> List[str]:
        """Get all column names."""
        return [c.name for c in self.columns]

    def get_column(self, name: str) -> Optional[Column]:
        """Get a column by name."""
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def add_column(self, column: Column) -> None:
        """Add a column to the dimension."""
        self.columns.append(column)

    def validate(self) -> List[str]:
        """Validate the dimension definition."""
        errors = []
        pk_count = sum(1 for c in self.columns if c.primary_key)
        if pk_count == 0:
            errors.append(f"Dimension '{self.name}' has no primary key")
        if pk_count > 1:
            errors.append(f"Dimension '{self.name}' has multiple primary keys")
        if self.slowly_changing_dimension and self.scd_type not in (1, 2, 3):
            errors.append(f"Dimension '{self.name}' has invalid SCD type: {self.scd_type}")
        return errors


@dataclass
class FactTable:
    """Represents a fact table in star schema."""

    name: str
    columns: List[Column] = field(default_factory=list)
    dimension_keys: Dict[str, str] = field(default_factory=dict)  # dimension_name -> fk_column
    measures: List[str] = field(default_factory=list)
    description: str = ""
    grain: str = ""

    @property
    def primary_key(self) -> Optional[Column]:
        """Get the primary key column."""
        for col in self.columns:
            if col.primary_key:
                return col
        return None

    @property
    def column_names(self) -> List[str]:
        """Get all column names."""
        return [c.name for c in self.columns]

    def get_column(self, name: str) -> Optional[Column]:
        """Get a column by name."""
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def add_measure(self, name: str) -> None:
        """Add a measure column."""
        self.measures.append(name)

    def link_dimension(self, dimension_name: str, fk_column: str) -> None:
        """Link a dimension to this fact table."""
        self.dimension_keys[dimension_name] = fk_column

    def validate(self) -> List[str]:
        """Validate the fact table definition."""
        errors = []
        if not self.dimension_keys:
            errors.append(f"Fact table '{self.name}' has no dimension links")
        if not self.measures:
            errors.append(f"Fact table '{self.name}' has no measures")
        for dim_name, fk_col in self.dimension_keys.items():
            if fk_col not in self.column_names:
                errors.append(f"Fact table '{self.name}' FK column '{fk_col}' not found")
        return errors


@dataclass
class StarSchema:
    """Represents a star schema with dimensions and fact tables."""

    name: str
    dimensions: List[Dimension] = field(default_factory=list)
    fact_tables: List[FactTable] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    description: str = ""

    def add_dimension(self, dimension: Dimension) -> None:
        """Add a dimension to the schema."""
        self.dimensions.append(dimension)

    def add_fact_table(self, fact_table: FactTable) -> None:
        """Add a fact table to the schema."""
        self.fact_tables.append(fact_table)

    def add_relationship(self, relationship: Relationship) -> None:
        """Add a relationship to the schema."""
        self.relationships.append(relationship)

    def get_dimension(self, name: str) -> Optional[Dimension]:
        """Get a dimension by name."""
        for dim in self.dimensions:
            if dim.name == name:
                return dim
        return None

    def get_fact_table(self, name: str) -> Optional[FactTable]:
        """Get a fact table by name."""
        for ft in self.fact_tables:
            if ft.name == name:
                return ft
        return None

    def validate(self) -> List[str]:
        """Validate the entire star schema."""
        errors = []
        dim_names = {d.name for d in self.dimensions}
        ft_names = {f.name for f in self.fact_tables}

        for dim in self.dimensions:
            errors.extend(dim.validate())

        for ft in self.fact_tables:
            errors.extend(ft.validate())
            for dim_name in ft.dimension_keys:
                if dim_name not in dim_names:
                    errors.append(f"Fact table '{ft.name}' references unknown dimension '{dim_name}'")

        for rel in self.relationships:
            tables = {}
            for d in self.dimensions:
                tables[d.name] = d
            for f in self.fact_tables:
                tables[f.name] = f
            if not rel.validate(tables):
                errors.append(f"Relationship '{rel.name}' is invalid")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert schema to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "dimensions": [
                {
                    "name": d.name,
                    "description": d.description,
                    "columns": [
                        {
                            "name": c.name,
                            "data_type": c.data_type.value,
                            "nullable": c.nullable,
                            "primary_key": c.primary_key,
                        }
                        for c in d.columns
                    ],
                    "scd_type": d.scd_type,
                }
                for d in self.dimensions
            ],
            "fact_tables": [
                {
                    "name": f.name,
                    "description": f.description,
                    "grain": f.grain,
                    "dimension_keys": f.dimension_keys,
                    "measures": f.measures,
                    "columns": [
                        {
                            "name": c.name,
                            "data_type": c.data_type.value,
                            "nullable": c.nullable,
                        }
                        for c in f.columns
                    ],
                }
                for f in self.fact_tables
            ],
            "relationships": [
                {
                    "name": r.name,
                    "source_table": r.source_table,
                    "source_column": r.source_column,
                    "target_table": r.target_table,
                    "target_column": r.target_column,
                    "type": r.relationship_type,
                }
                for r in self.relationships
            ],
        }
