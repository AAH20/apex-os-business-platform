#!/usr/bin/env python3
"""BigData Demo — showcases dataset creation, ingestion, queries, storage, and pipelines."""

import time
import random
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class Dataset:
    id: str
    name: str
    schema: Dict[str, str]
    row_count: int = 0
    size_bytes: int = 0
    created_at: float = 0.0


@dataclass
class QueryResult:
    query_id: str
    rows_returned: int
    execution_ms: float
    columns: List[str]


@dataclass
class PipelineStage:
    name: str
    status: str = "pending"
    records_in: int = 0
    records_out: int = 0
    duration_ms: float = 0.0


# ─── Demo 1: Dataset Creation ────────────────────────────────────────────────

def demo_dataset_creation():
    print("=" * 60)
    print("DEMO 1: Dataset Creation")
    print("=" * 60)

    datasets: List[Dataset] = []

    schemas = [
        ("users", {"id": "UUID", "name": "STRING", "email": "STRING", "age": "INT"}),
        ("transactions", {"id": "UUID", "user_id": "UUID", "amount": "FLOAT", "ts": "TIMESTAMP"}),
        ("events", {"id": "UUID", "event_type": "STRING", "payload": "JSON", "ts": "TIMESTAMP"}),
    ]

    for name, schema in schemas:
        ds = Dataset(
            id=str(uuid.uuid4())[:8],
            name=name,
            schema=schema,
            created_at=time.time(),
        )
        datasets.append(ds)
        print(f"  Created dataset '{ds.name}' (id={ds.id})")
        print(f"    Schema: {', '.join(f'{k}:{v}' for k, v in schema.items())}")

    print(f"\n  Total datasets: {len(datasets)}")
    print()


# ─── Demo 2: Data Ingestion ──────────────────────────────────────────────────

def demo_data_ingestion():
    print("=" * 60)
    print("DEMO 2: Data Ingestion")
    print("=" * 60)

    datasets = {
        "users": Dataset(id="d1", name="users", schema={"id": "UUID", "name": "STRING"}),
        "transactions": Dataset(id="d2", name="transactions", schema={"id": "UUID", "amount": "FLOAT"}),
        "events": Dataset(id="d3", name="events", schema={"id": "UUID", "type": "STRING"}),
    }

    batch_sizes = [1000, 5000, 2500, 8000, 3000]
    print(f"  {'Batch':<8} {'Dataset':<15} {'Rows':<10} {'Size (KB)':<12} {'Rate (rows/s)'}")
    print(f"  {'-'*8} {'-'*15} {'-'*10} {'-'*12} {'-'*15}")

    total_ingested = 0
    for i, batch_size in enumerate(batch_sizes):
        ds_name = random.choice(list(datasets.keys()))
        ds = datasets[ds_name]
        size_kb = batch_size * random.uniform(0.1, 0.5)
        duration = random.uniform(0.1, 1.5)
        rate = batch_size / duration

        ds.row_count += batch_size
        ds.size_bytes += int(size_kb * 1024)
        total_ingested += batch_size

        print(f"  {i+1:<8} {ds_name:<15} {batch_size:<10} {size_kb:<12.1f} {rate:<15.0f}")

    print(f"\n  Total ingested: {total_ingested} rows")
    for name, ds in datasets.items():
        print(f"    {name}: {ds.row_count} rows, {ds.size_bytes / 1024:.1f} KB")
    print()


# ─── Demo 3: Query Execution ─────────────────────────────────────────────────

def demo_query_execution():
    print("=" * 60)
    print("DEMO 3: Query Execution")
    print("=" * 60)

    queries = [
        ("SELECT * FROM users WHERE age > 30", 150),
        ("SELECT COUNT(*) FROM transactions", 1),
        ("SELECT user_id, SUM(amount) FROM transactions GROUP BY user_id", 50),
        ("SELECT * FROM events WHERE event_type = 'click' ORDER BY ts DESC LIMIT 100", 100),
        ("SELECT u.name, COUNT(t.id) FROM users u JOIN transactions t ON u.id = t.user_id", 75),
    ]

    print(f"  {'Query':<55} {'Rows':<8} {'Time (ms)'}")
    print(f"  {'-'*55} {'-'*8} {'-'*10}")

    total_time = 0
    for sql, expected_rows in queries:
        exec_ms = random.uniform(5, 500)
        total_time += exec_ms
        qid = str(uuid.uuid4())[:6]
        display_sql = sql[:52] + "..." if len(sql) > 55 else sql
        print(f"  {display_sql:<55} {expected_rows:<8} {exec_ms:.1f}")

    print(f"\n  Queries executed: {len(queries)}")
    print(f"  Total execution time: {total_time:.1f} ms")
    print(f"  Average: {total_time / len(queries):.1f} ms")
    print()


# ─── Demo 4: Storage Analysis ────────────────────────────────────────────────

def demo_storage_analysis():
    print("=" * 60)
    print("DEMO 4: Storage Analysis")
    print("=" * 60)

    datasets = [
        ("users", 50000, 2048000),
        ("transactions", 250000, 102400000),
        ("events", 1000000, 512000000),
        ("logs", 5000000, 2048000000),
        ("analytics", 75000, 51200000),
    ]

    print(f"  {'Dataset':<15} {'Rows':<12} {'Size':<15} {'% of Total':<12} {'Bar'}")
    print(f"  {'-'*15} {'-'*12} {'-'*15} {'-'*12} {'-'*20}")

    total_size = sum(s for _, _, s in datasets)
    for name, rows, size in datasets:
        pct = size / total_size * 100
        size_str = f"{size / 1024 / 1024:.1f} MB" if size < 1024**3 else f"{size / 1024**3:.2f} GB"
        bar_len = int(pct / 2)
        bar = "█" * bar_len
        print(f"  {name:<15} {rows:<12,} {size_str:<15} {pct:<12.1f} {bar}")

    print(f"\n  Total storage: {total_size / 1024**3:.2f} GB")
    print(f"  Total rows: {sum(r for _, r, _ in datasets):,}")
    print(f"  Datasets: {len(datasets)}")
    print()


# ─── Demo 5: Pipeline Demo ───────────────────────────────────────────────────

def demo_pipeline():
    print("=" * 60)
    print("DEMO 5: Pipeline Demo")
    print("=" * 60)

    stages = [
        PipelineStage(name="extract", records_in=0, records_out=10000),
        PipelineStage(name="validate", records_in=10000, records_out=9800),
        PipelineStage(name="transform", records_in=9800, records_out=9800),
        PipelineStage(name="enrich", records_in=9800, records_out=9800),
        PipelineStage(name="load", records_in=9800, records_out=9800),
    ]

    print(f"  {'Stage':<15} {'Status':<12} {'In':<10} {'Out':<10} {'Duration (ms)'}")
    print(f"  {'-'*15} {'-'*12} {'-'*10} {'-'*10} {'-'*14}")

    total_duration = 0
    for stage in stages:
        stage.status = "running"
        stage.duration_ms = random.uniform(50, 2000)
        stage.status = "completed"
        total_duration += stage.duration_ms
        print(f"  {stage.name:<15} {stage.status:<12} {stage.records_in:<10,} "
              f"{stage.records_out:<10,} {stage.duration_ms:.1f}")

    print(f"\n  Pipeline: extract -> validate -> transform -> enrich -> load")
    print(f"  Total duration: {total_duration:.1f} ms")
    print(f"  Records processed: {stages[-1].records_out:,}")
    print(f"  Stages completed: {len(stages)}/{len(stages)}")
    print()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "█" * 60)
    print("  APEX-OS BigData Demo Suite")
    print("█" * 60 + "\n")

    demo_dataset_creation()
    demo_data_ingestion()
    demo_query_execution()
    demo_storage_analysis()
    demo_pipeline()

    print("█" * 60)
    print("  All BigData demos completed successfully!")
    print("█" * 60 + "\n")


if __name__ == "__main__":
    main()
