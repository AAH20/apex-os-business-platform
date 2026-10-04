"""Fluent query builder for database operations.

Provides a chainable API for constructing complex SQLAlchemy queries
with filtering, sorting, pagination, and aggregation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, TypeVar

from sqlalchemy import select, func, and_, or_, desc, asc, ColumnElement
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from apex_os_bp.database.models import Base

T = TypeVar("T", bound=Base)


class QueryBuilder:
    """Fluent query builder for SQLAlchemy ORM.

    Example:
        results = (
            QueryBuilder(session, User)
            .filter(User.role == UserRole.ADMIN)
            .filter(User.is_active == True)
            .order_by(User.created_at, desc=True)
            .limit(10)
            .offset(0)
            .all()
        )
    """

    def __init__(self, session: Session, model: Type[T]) -> None:
        self._session = session
        self._model = model
        self._filters: List[ColumnElement[bool]] = []
        self._order_clauses: List[ColumnElement[Any]] = []
        self._limit_value: Optional[int] = None
        self._offset_value: Optional[int] = None
        self._eager_loads: List[Any] = []
        self._selected_columns: Optional[List[Any]] = None

    def filter(self, *criteria: ColumnElement[bool]) -> "QueryBuilder":
        """Add AND filter criteria."""
        self._filters.extend(criteria)
        return self

    def filter_by(self, **kwargs: Any) -> "QueryBuilder":
        """Add equality filters by column name."""
        for key, value in kwargs.items():
            column = getattr(self._model, key, None)
            if column is None:
                raise AttributeError(
                    f"Model '{self._model.__name__}' has no column '{key}'"
                )
            self._filters.append(column == value)
        return self

    def filter_or(self, *criteria: ColumnElement[bool]) -> "QueryBuilder":
        """Add OR filter criteria (grouped)."""
        if criteria:
            self._filters.append(or_(*criteria))
        return self

    def filter_in(self, column_name: str, values: List[Any]) -> "QueryBuilder":
        """Add an IN filter."""
        column = getattr(self._model, column_name, None)
        if column is None:
            raise AttributeError(
                f"Model '{self._model.__name__}' has no column '{column_name}'"
            )
        self._filters.append(column.in_(values))
        return self

    def filter_like(self, column_name: str, pattern: str) -> "QueryBuilder":
        """Add a LIKE filter."""
        column = getattr(self._model, column_name, None)
        if column is None:
            raise AttributeError(
                f"Model '{self._model.__name__}' has no column '{column_name}'"
            )
        self._filters.append(column.like(pattern))
        return self

    def filter_between(self, column_name: str, low: Any, high: Any) -> "QueryBuilder":
        """Add a BETWEEN filter."""
        column = getattr(self._model, column_name, None)
        if column is None:
            raise AttributeError(
                f"Model '{self._model.__name__}' has no column '{column_name}'"
            )
        self._filters.append(column.between(low, high))
        return self

    def order_by(self, column: Any, direction: str = "asc") -> "QueryBuilder":
        """Add an ORDER BY clause."""
        if direction.lower() == "desc":
            self._order_clauses.append(desc(column))
        else:
            self._order_clauses.append(asc(column))
        return self

    def order_by_column(self, column_name: str, direction: str = "asc") -> "QueryBuilder":
        """Add ORDER BY using a column name string."""
        column = getattr(self._model, column_name, None)
        if column is None:
            raise AttributeError(
                f"Model '{self._model.__name__}' has no column '{column_name}'"
            )
        return self.order_by(column, direction)

    def limit(self, n: int) -> "QueryBuilder":
        """Set LIMIT."""
        self._limit_value = n
        return self

    def offset(self, n: int) -> "QueryBuilder":
        """Set OFFSET."""
        self._offset_value = n
        return self

    def paginate(self, page: int, per_page: int = 20) -> "QueryBuilder":
        """Set pagination parameters."""
        self._limit_value = per_page
        self._offset_value = (page - 1) * per_page
        return self

    def with_(self, *relationships: Any) -> "QueryBuilder":
        """Eager-load relationships."""
        self._eager_loads.extend(relationships)
        return self

    def columns(self, *columns: Any) -> "QueryBuilder":
        """Select specific columns instead of full entities."""
        self._selected_columns = list(columns)
        return self

    def _build(self) -> Select:
        """Construct the final SQLAlchemy Select statement."""
        if self._selected_columns:
            stmt = select(*self._selected_columns)
        else:
            stmt = select(self._model)

        if self._filters:
            stmt = stmt.where(and_(*self._filters))

        for clause in self._order_clauses:
            stmt = stmt.order_by(clause)

        if self._limit_value is not None:
            stmt = stmt.limit(self._limit_value)

        if self._offset_value is not None:
            stmt = stmt.offset(self._offset_value)

        for rel in self._eager_loads:
            stmt = stmt.options(rel)

        return stmt

    def all(self) -> List[T]:
        """Execute and return all results."""
        stmt = self._build()
        result = self._session.execute(stmt)
        if self._selected_columns:
            return result.all()  # type: ignore[return-value]
        return result.scalars().all()  # type: ignore[return-value]

    def first(self) -> Optional[T]:
        """Execute and return the first result."""
        stmt = self._build()
        result = self._session.execute(stmt)
        if self._selected_columns:
            return result.first()  # type: ignore[return-value]
        return result.scalars().first()  # type: ignore[return-value]

    def one(self) -> T:
        """Execute and return exactly one result."""
        stmt = self._build()
        result = self._session.execute(stmt)
        if self._selected_columns:
            return result.one()  # type: ignore[return-value]
        return result.scalars().one()  # type: ignore[return-value]

    def one_or_none(self) -> Optional[T]:
        """Execute and return one result or None."""
        stmt = self._build()
        result = self._session.execute(stmt)
        if self._selected_columns:
            return result.one_or_none()  # type: ignore[return-value]
        return result.scalars().one_or_none()  # type: ignore[return-value]

    def count(self) -> int:
        """Return the count of matching rows."""
        stmt = select(func.count()).select_from(self._model)
        if self._filters:
            stmt = stmt.where(and_(*self._filters))
        return self._session.execute(stmt).scalar_one()

    def exists(self) -> bool:
        """Check if any matching row exists."""
        return self.first() is not None

    def aggregate(
        self, column: Any, agg_func: str = "sum"
    ) -> Optional[Any]:
        """Run an aggregate function on a column."""
        agg_map = {
            "sum": func.sum,
            "avg": func.avg,
            "min": func.min,
            "max": func.max,
            "count": func.count,
        }
        if agg_func not in agg_map:
            raise ValueError(f"Unknown aggregate function: {agg_func}")
        stmt = select(agg_map[agg_func](column))
        if self._filters:
            stmt = stmt.where(and_(*self._filters))
        return self._session.execute(stmt).scalar()

    def delete(self) -> int:
        """Delete all matching rows. Returns number of rows deleted."""
        stmt = self._build()
        # For delete, we need to fetch IDs first then delete
        results = self.all()
        count = len(results)
        for obj in results:
            self._session.delete(obj)
        return count

    def update(self, **values: Any) -> int:
        """Update all matching rows. Returns number of rows updated."""
        stmt = self._build()
        results = self.all()
        count = len(results)
        for obj in results:
            for key, value in values.items():
                setattr(obj, key, value)
        return count

    def to_dict(self) -> Dict[str, Any]:
        """Return the query parameters as a dictionary (for debugging)."""
        return {
            "model": self._model.__name__,
            "filters": len(self._filters),
            "order_by": len(self._order_clauses),
            "limit": self._limit_value,
            "offset": self._offset_value,
            "eager_loads": len(self._eager_loads),
        }
