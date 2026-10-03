#!/usr/bin/env python3
"""Demo: Big Data — simulated large-scale data processing pipeline."""

import hashlib
import random
import time
from collections import Counter

DATA_SOURCES = ["kafka-stream", "s3-batch", "cdc-postgres", "api-ingest"]
BATCH_SIZES = [1_000, 10_000, 50_000, 100_000]


def generate_record(source: str, idx: int) -> dict:
    """Generate a synthetic data record."""
    return {
        "id": hashlib.md5(f"{source}-{idx}".encode()).hexdigest()[:12],
        "source": source,
        "value": round(random.gauss(100, 25), 2),
        "category": random.choice(["A", "B", "C", "D"]),
        "valid": random.random() > 0.05,
    }


def process_batch(source: str, size: int) -> dict:
    """Simulate processing a batch of records."""
    start = time.time()
    records = [generate_record(source, i) for i in range(size)]
    valid = [r for r in records if r["valid"]]
    categories = Counter(r["category"] for r in valid)
    avg_value = sum(r["value"] for r in valid) / max(len(valid), 1)
    elapsed = time.time() - start
    return {
        "source": source,
        "total": size,
        "valid": len(valid),
        "invalid": size - len(valid),
        "categories": dict(categories),
        "avg_value": round(avg_value, 2),
        "elapsed_s": round(elapsed, 3),
        "throughput": round(size / max(elapsed, 0.001), 0),
    }


def run_demo():
    print("=" * 60)
    print("  BIG DATA DEMO — Large-Scale Processing Pipeline")
    print("=" * 60)

    all_results = []
    for source in DATA_SOURCES:
        batch_size = random.choice(BATCH_SIZES)
        result = process_batch(source, batch_size)
        all_results.append(result)
        print(
            f"\n  Source: {source} | Batch: {result['total']:,} records"
        )
        print(
            f"    Valid: {result['valid']:,} | Invalid: {result['invalid']:,}"
        )
        print(f"    Avg value: {result['avg_value']}")
        print(f"    Categories: {result['categories']}")
        print(
            f"    Time: {result['elapsed_s']}s | "
            f"Throughput: {result['throughput']:,.0f} rec/s"
        )

    total_records = sum(r["total"] for r in all_results)
    total_valid = sum(r["valid"] for r in all_results)
    total_time = sum(r["elapsed_s"] for r in all_results)

    print("\n" + "-" * 60)
    print("  PIPELINE SUMMARY")
    print("-" * 60)
    print(f"  Total records processed : {total_records:,}")
    print(f"  Total valid records     : {total_valid:,}")
    print(f"  Total invalid records   : {total_records - total_valid:,}")
    print(f"  Data quality rate       : {total_valid / total_records * 100:.1f}%")
    print(f"  Total processing time   : {total_time:.3f}s")
    print(
        f"  Overall throughput      : "
        f"{total_records / max(total_time, 0.001):,.0f} rec/s"
    )
    print("=" * 60)
    print("\n  Big Data demo complete.\n")


if __name__ == "__main__":
    run_demo()
