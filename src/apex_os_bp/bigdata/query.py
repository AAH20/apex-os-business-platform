"""SQL-like query engine supporting SELECT, WHERE, GROUP BY, ORDER BY, LIMIT."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from .models import Table

_AGG_FUNCS = {
    "count": len,
    "sum": sum,
    "min": min,
    "max": max,
    "avg": lambda vals: sum(vals) / len(vals) if vals else 0,
}


class QueryEngine:
    """Execute simplified SQL-like queries against a Table."""

    def __init__(self, table: Table) -> None:
        self.table = table

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, query: str) -> list[dict[str, Any]]:
        """Parse and run a single SELECT statement."""
        parsed = self._parse(query)
        rows = self._collect_rows()
        rows = self._apply_where(rows, parsed["where"])
        has_agg = any(
            re.match(r"(count|sum|min|max|avg)\s*\(", sel, re.IGNORECASE)
            for sel in parsed["select"]
        )
        if parsed["group_by"] or has_agg:
            rows = self._apply_group_by(rows, parsed)
        else:
            rows = self._apply_projection(rows, parsed["select"])
        rows = self._apply_order_by(rows, parsed["order_by"])
        if parsed["limit"] is not None:
            rows = rows[: parsed["limit"]]
        return rows

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse(self, query: str) -> dict[str, Any]:
        q = query.strip().rstrip(";")
        pattern = re.compile(
            r"SELECT\s+(?P<select>.+?)\s+FROM\s+\S+"
            r"(?:\s+WHERE\s+(?P<where>.+?))?"
            r"(?:\s+GROUP\s+BY\s+(?P<group>.+?))?"
            r"(?:\s+ORDER\s+BY\s+(?P<order>.+?))?"
            r"(?:\s+LIMIT\s+(?P<limit>\d+))?$",
            re.IGNORECASE | re.DOTALL,
        )
        m = pattern.match(q)
        if not m:
            raise ValueError(f"Unsupported query: {query!r}")
        gd = m.groupdict()
        return {
            "select": [c.strip() for c in gd["select"].split(",")],
            "where": gd["where"],
            "group_by": [c.strip() for c in gd["group"].split(",")] if gd["group"] else [],
            "order_by": gd["order"],
            "limit": int(gd["limit"]) if gd["limit"] else None,
        }

    # ------------------------------------------------------------------
    # Row collection
    # ------------------------------------------------------------------

    def _collect_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for partition in self.table.partitions.values():
            rows.extend(partition.rows)
        return rows

    # ------------------------------------------------------------------
    # WHERE
    # ------------------------------------------------------------------

    def _apply_where(
        self, rows: list[dict[str, Any]], condition: str | None
    ) -> list[dict[str, Any]]:
        if not condition:
            return rows
        return [r for r in rows if self._eval_condition(r, condition)]

    def _eval_condition(self, row: dict[str, Any], condition: str) -> bool:
        # Support simple AND-connected comparisons: col op value
        for part in re.split(r"\s+AND\s+", condition, flags=re.IGNORECASE):
            if not self._eval_single(row, part.strip()):
                return False
        return True

    def _eval_single(self, row: dict[str, Any], expr: str) -> bool:
        m = re.match(
            r"(\w+)\s*(>=|<=|!=|=|>|<)\s*(.+)", expr.strip()
        )
        if not m:
            raise ValueError(f"Cannot parse condition: {expr!r}")
        col, op, raw_val = m.groups()
        if col not in row:
            raise ValueError(f"Unknown column in WHERE: {col!r}")
        left = row[col]
        right = self._coerce(raw_val.strip().strip("'\""), type(left))
        ops = {
            "=": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
        }
        return ops[op](left, right)

    @staticmethod
    def _coerce(value: str, target_type: type) -> Any:
        if target_type is int:
            return int(value)
        if target_type is float:
            return float(value)
        if target_type is bool:
            return value.lower() in ("true", "1", "yes")
        return value

    # ------------------------------------------------------------------
    # GROUP BY + aggregation
    # ------------------------------------------------------------------

    def _apply_group_by(
        self, rows: list[dict[str, Any]], parsed: dict[str, Any]
    ) -> list[dict[str, Any]]:
        groups: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            key = tuple(row.get(g) for g in parsed["group_by"])
            groups[key].append(row)

        results: list[dict[str, Any]] = []
        for key, group_rows in groups.items():
            out: dict[str, Any] = dict(zip(parsed["group_by"], key))
            for sel in parsed["select"]:
                sel = sel.strip()
                agg_match = re.match(
                    r"(count|sum|min|max|avg)\s*\(\s*(\w+|\*)\s*\)", sel, re.IGNORECASE
                )
                if agg_match:
                    func_name = agg_match.group(1).lower()
                    col = agg_match.group(2)
                    vals = [r[col] for r in group_rows if col != "*" and r.get(col) is not None]
                    if col == "*":
                        out[sel] = _AGG_FUNCS[func_name](group_rows)
                    else:
                        out[sel] = _AGG_FUNCS[func_name](vals)
                elif sel not in parsed["group_by"]:
                    out[sel] = group_rows[0].get(sel)
            results.append(out)
        return results

    # ------------------------------------------------------------------
    # Projection (non-aggregate)
    # ------------------------------------------------------------------

    def _apply_projection(
        self, rows: list[dict[str, Any]], select: list[str]
    ) -> list[dict[str, Any]]:
        if select == ["*"]:
            return [dict(r) for r in rows]
        return [{col: r.get(col) for col in select} for r in rows]

    # ------------------------------------------------------------------
    # ORDER BY
    # ------------------------------------------------------------------

    def _apply_order_by(
        self, rows: list[dict[str, Any]], order_clause: str | None
    ) -> list[dict[str, Any]]:
        if not order_clause:
            return rows
        parts = [p.strip() for p in order_clause.split(",")]
        for part in reversed(parts):
            tokens = part.split()
            col = tokens[0]
            reverse = len(tokens) > 1 and tokens[1].upper() == "DESC"
            rows.sort(key=lambda r: (r.get(col) is None, r.get(col)), reverse=reverse)
        return rows
