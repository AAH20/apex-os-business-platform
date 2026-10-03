"""Tests for the Big Data core module."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from apex_os_bp.bigdata import (
    BatchIngestion,
    Column,
    ColumnarStorage,
    DataType,
    Dataset,
    Partition,
    QueryEngine,
    StreamingIngestion,
    Table,
)


def _make_table() -> Table:
    return Table(
        name="events",
        columns=[
            Column("id", DataType.INTEGER, nullable=False),
            Column("user", DataType.STRING, nullable=False),
            Column("amount", DataType.FLOAT, nullable=True),
            Column("active", DataType.BOOLEAN, nullable=True),
        ],
    )


def _sample_rows() -> list[dict]:
    return [
        {"id": 1, "user": "alice", "amount": 10.5, "active": True},
        {"id": 2, "user": "bob", "amount": 20.0, "active": False},
        {"id": 3, "user": "alice", "amount": 5.5, "active": True},
        {"id": 4, "user": "carol", "amount": 30.0, "active": True},
    ]


class TestModels(unittest.TestCase):
    def test_column_validate_value(self):
        col = Column("age", DataType.INTEGER)
        self.assertTrue(col.validate_value(42))
        self.assertFalse(col.validate_value("42"))
        self.assertTrue(col.validate_value(None))  # nullable by default

    def test_table_add_partition_valid(self):
        t = _make_table()
        t.add_partition("p1", _sample_rows())
        self.assertEqual(t.row_count, 4)

    def test_table_add_partition_invalid_column(self):
        t = _make_table()
        with self.assertRaises(ValueError):
            t.add_partition("p1", [{"unknown_col": 1}])

    def test_table_add_partition_invalid_type(self):
        t = _make_table()
        with self.assertRaises(ValueError):
            t.add_partition("p1", [{"id": "not_an_int"}])

    def test_dataset(self):
        ds = Dataset("test")
        t = _make_table()
        ds.add_table(t)
        self.assertIs(ds.get_table("events"), t)
        self.assertIsNone(ds.get_table("missing"))


class TestBatchIngestion(unittest.TestCase):
    def test_ingest(self):
        t = _make_table()
        ing = BatchIngestion(t, partition_key="batch1")
        count = ing.ingest(_sample_rows())
        self.assertEqual(count, 4)
        self.assertEqual(ing.ingested_count, 4)
        self.assertEqual(t.row_count, 4)

    def test_ingest_with_transform(self):
        t = _make_table()
        ing = BatchIngestion(t)
        rows = [{"id": i, "user": f"u{i}", "amount": float(i), "active": True} for i in range(3)]
        ing.ingest_with_transform(rows, lambda r: {**r, "amount": r["amount"] * 2})
        self.assertEqual(t.partitions["default"].rows[0]["amount"], 0.0)

    def test_ingest_empty(self):
        t = _make_table()
        ing = BatchIngestion(t)
        self.assertEqual(ing.ingest([]), 0)


class TestStreamingIngestion(unittest.TestCase):
    def test_emit_and_flush(self):
        t = _make_table()
        stream = StreamingIngestion(t, max_buffer_size=3)
        rows = _sample_rows()
        for r in rows[:2]:
            stream.emit(r)
        self.assertEqual(stream.buffer_size, 2)
        flushed = stream.flush()
        self.assertEqual(flushed, 2)
        self.assertEqual(stream.total_ingested, 2)

    def test_auto_flush_on_full_buffer(self):
        t = _make_table()
        stream = StreamingIngestion(t, max_buffer_size=2)
        self.assertFalse(stream.emit(_sample_rows()[0]))  # buffer: 1/2
        self.assertTrue(stream.emit(_sample_rows()[1]))   # buffer: 2/2 → flush
        self.assertEqual(stream.total_ingested, 2)

    def test_consume_iterator(self):
        t = _make_table()
        stream = StreamingIngestion(t, max_buffer_size=100)
        flushed = stream.consume(iter(_sample_rows()))
        self.assertGreaterEqual(flushed, 1)
        self.assertEqual(stream.total_ingested, 4)


class TestQueryEngine(unittest.TestCase):
    def _engine(self) -> QueryEngine:
        t = _make_table()
        t.add_partition("p1", _sample_rows())
        return QueryEngine(t)

    def test_select_star(self):
        result = self._engine().execute("SELECT * FROM events")
        self.assertEqual(len(result), 4)

    def test_select_columns(self):
        result = self._engine().execute("SELECT id, user FROM events")
        self.assertEqual(set(result[0].keys()), {"id", "user"})

    def test_where(self):
        result = self._engine().execute("SELECT * FROM events WHERE amount > 15")
        self.assertEqual(len(result), 2)

    def test_where_and(self):
        result = self._engine().execute(
            "SELECT * FROM events WHERE user = 'alice' AND amount > 6"
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 1)

    def test_group_by_count(self):
        result = self._engine().execute(
            "SELECT user, count(*) FROM events GROUP BY user"
        )
        counts = {r["user"]: r["count(*)"] for r in result}
        self.assertEqual(counts["alice"], 2)
        self.assertEqual(counts["bob"], 1)

    def test_group_by_sum(self):
        result = self._engine().execute(
            "SELECT user, sum(amount) FROM events GROUP BY user"
        )
        sums = {r["user"]: r["sum(amount)"] for r in result}
        self.assertAlmostEqual(sums["alice"], 16.0)

    def test_order_by(self):
        result = self._engine().execute("SELECT id FROM events ORDER BY id DESC")
        ids = [r["id"] for r in result]
        self.assertEqual(ids, [4, 3, 2, 1])

    def test_limit(self):
        result = self._engine().execute("SELECT * FROM events LIMIT 2")
        self.assertEqual(len(result), 2)

    def test_avg(self):
        result = self._engine().execute("SELECT avg(amount) FROM events")
        self.assertAlmostEqual(result[0]["avg(amount)"], 16.5)


class TestColumnarStorage(unittest.TestCase):
    def test_write_and_read_roundtrip(self):
        t = _make_table()
        t.add_partition("p1", _sample_rows())
        with tempfile.TemporaryDirectory() as tmp:
            storage = ColumnarStorage(tmp)
            byte_count = storage.write_table(t)
            self.assertGreater(byte_count, 0)

            loaded = storage.read_table("events")
            self.assertEqual(loaded.name, "events")
            self.assertEqual(loaded.row_count, 4)
            self.assertEqual(
                loaded.partitions["p1"].rows[0]["user"], "alice"
            )

    def test_missing_table_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = ColumnarStorage(tmp)
            with self.assertRaises(FileNotFoundError):
                storage.read_table("nope")

    def test_compression_reduces_size(self):
        t = _make_table()
        rows = [{"id": i, "user": "x" * 100, "amount": 1.0, "active": True} for i in range(100)]
        t.add_partition("p1", rows)
        with tempfile.TemporaryDirectory() as tmp:
            storage = ColumnarStorage(tmp, compression_level=9)
            size = storage.write_table(t)
            raw = sum(len(str(r)) for r in rows)
            self.assertLess(size, raw)


if __name__ == "__main__":
    unittest.main()
