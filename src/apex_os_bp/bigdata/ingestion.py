"""Batch and streaming ingestion pipelines."""

from __future__ import annotations

import time
from typing import Any, Callable, Iterator

from .models import Table


class BatchIngestion:
    """Ingest a fixed set of rows into a table in one shot."""

    def __init__(self, table: Table, partition_key: str = "default") -> None:
        self.table = table
        self.partition_key = partition_key
        self._ingested = 0

    @property
    def ingested_count(self) -> int:
        return self._ingested

    def ingest(self, rows: list[dict[str, Any]]) -> int:
        """Validate and load *rows*; returns the number accepted."""
        if not rows:
            return 0
        self.table.add_partition(self.partition_key, rows)
        self._ingested += len(rows)
        return len(rows)

    def ingest_with_transform(
        self,
        rows: list[dict[str, Any]],
        transform: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> int:
        """Apply *transform* to each row before ingestion."""
        return self.ingest([transform(r) for r in rows])


class StreamingIngestion:
    """Micro-batch streaming ingestion with a configurable flush interval."""

    def __init__(
        self,
        table: Table,
        partition_key: str = "stream",
        max_buffer_size: int = 1000,
        flush_interval_sec: float = 5.0,
    ) -> None:
        self.table = table
        self.partition_key = partition_key
        self.max_buffer_size = max_buffer_size
        self.flush_interval_sec = flush_interval_sec
        self._buffer: list[dict[str, Any]] = []
        self._last_flush = time.monotonic()
        self._total_ingested = 0

    @property
    def total_ingested(self) -> int:
        return self._total_ingested

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)

    def emit(self, row: dict[str, Any]) -> bool:
        """Buffer a single row; auto-flush when buffer is full.

        Returns True if a flush happened.
        """
        self._buffer.append(row)
        if len(self._buffer) >= self.max_buffer_size:
            self.flush()
            return True
        return False

    def flush(self) -> int:
        """Force-emit all buffered rows; returns count flushed."""
        if not self._buffer:
            return 0
        batch = self._buffer[:]
        self._buffer.clear()
        self.table.add_partition(
            f"{self.partition_key}_{time.time_ns()}", batch
        )
        self._total_ingested += len(batch)
        self._last_flush = time.monotonic()
        return len(batch)

    def should_flush(self) -> bool:
        """Check whether the flush interval has elapsed."""
        return (time.monotonic() - self._last_flush) >= self.flush_interval_sec

    def consume(self, source: Iterator[dict[str, Any]]) -> int:
        """Consume rows from *source*, flushing on buffer-full or interval."""
        flushed = 0
        for row in source:
            did_flush = self.emit(row)
            if did_flush:
                flushed += 1
            elif self.should_flush():
                self.flush()
                flushed += 1
        if self._buffer:
            self.flush()
            flushed += 1
        return flushed
