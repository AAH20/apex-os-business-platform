"""Columnar storage engine with pluggable compression."""

from __future__ import annotations

import json
import zlib
from pathlib import Path
from typing import Any

from .models import DataType, Partition, Table


class ColumnarStorage:
    """Store tables in a columnar layout with zlib compression.

    Each column is serialised independently, compressed, and written to
    ``<root>/<table_name>/<column>.col`` alongside a ``meta.json`` schema.
    """

    def __init__(self, root: str | Path, compression_level: int = 6) -> None:
        self.root = Path(root)
        self.compression_level = compression_level

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def write_table(self, table: Table) -> int:
        """Persist *table* to disk; returns total bytes written."""
        table_dir = self.root / table.name
        table_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "name": table.name,
            "columns": [
                {"name": c.name, "dtype": c.dtype.value, "nullable": c.nullable}
                for c in table.columns
            ],
            "partition_keys": list(table.partitions.keys()),
        }
        meta_bytes = self._compress(json.dumps(meta).encode("utf-8"))
        (table_dir / "meta.json").write_bytes(meta_bytes)

        total = len(meta_bytes)
        col_names = [c.name for c in table.columns]
        for col_name in col_names:
            values = self._extract_column(table, col_name)
            payload = json.dumps(values, default=str).encode("utf-8")
            compressed = self._compress(payload)
            (table_dir / f"{col_name}.col").write_bytes(compressed)
            total += len(compressed)
        return total

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    def read_table(self, name: str) -> Table:
        """Load a table previously written by :meth:`write_table`."""
        table_dir = self.root / name
        if not table_dir.is_dir():
            raise FileNotFoundError(f"Table '{name}' not found under {self.root}")

        meta = json.loads(self._decompress((table_dir / "meta.json").read_bytes()))
        from .models import Column

        columns = [
            Column(
                name=c["name"],
                dtype=DataType(c["dtype"]),
                nullable=c["nullable"],
            )
            for c in meta["columns"]
        ]
        table = Table(name=meta["name"], columns=columns)

        for part_key in meta["partition_keys"]:
            rows = self._reconstruct_rows(table_dir, columns)
            table.partitions[part_key] = Partition(key=part_key, rows=rows)
        return table

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_column(self, table: Table, col_name: str) -> list[Any]:
        values: list[Any] = []
        for partition in table.partitions.values():
            for row in partition.rows:
                values.append(row.get(col_name))
        return values

    def _reconstruct_rows(
        self, table_dir: Path, columns: list[Any]
    ) -> list[dict[str, Any]]:
        col_data: dict[str, list[Any]] = {}
        for col in columns:
            raw = (table_dir / f"{col.name}.col").read_bytes()
            col_data[col.name] = json.loads(self._decompress(raw))

        n_rows = max((len(v) for v in col_data.values()), default=0)
        rows: list[dict[str, Any]] = []
        for i in range(n_rows):
            rows.append({col.name: col_data[col.name][i] for col in columns})
        return rows

    def _compress(self, data: bytes) -> bytes:
        return zlib.compress(data, level=self.compression_level)

    def _decompress(self, data: bytes) -> bytes:
        return zlib.decompress(data)
