# BigData Benchmark Tests

Comprehensive benchmark suite for the BigData module of APEX-OS Business Platform.
Covers ingestion speed, query performance, storage efficiency, data quality, and
operational performance metrics.

---

## 1. Data Ingestion Speed

Measures throughput and latency of data ingestion pipelines.

| Benchmark ID | Name | Description | Metric | Target |
|-------------|------|-------------|--------|--------|
| BDI-001 | Batch CSV Ingest | Ingest 1M-row CSV files | Rows/sec | ≥ 50,000 |
| BDI-002 | Batch JSON Ingest | Ingest 1M-record JSON files | Records/sec | ≥ 40,000 |
| BDI-003 | Streaming Kafka Ingest | Consume from Kafka topic | Msgs/sec | ≥ 10,000 |
| BDI-004 | Parquet Bulk Load | Load 10GB Parquet dataset | MB/sec | ≥ 200 |
| BDI-005 | Avro Schema Evolution | Ingest with schema changes | Records/sec | ≥ 30,000 |
| BDI-006 | Multi-source Parallel | Ingest from 5 sources concurrently | Aggregate rows/sec | ≥ 100,000 |
| BDI-007 | CDC Replication Latency | Change data capture end-to-end | Latency (p99) | ≤ 5s |
| BDI-008 | Compression Ingest | Ingest gzip/snappy compressed data | MB/sec | ≥ 150 |

### Test Procedure
1. Prepare dataset of known size (rows, bytes).
2. Start ingestion pipeline with monitoring enabled.
3. Record start time, end time, rows/bytes processed.
4. Calculate throughput = records / duration.
5. Run 5 iterations; report median and p95.

---

## 2. Query Performance

Measures query execution speed and concurrency handling.

| Benchmark ID | Name | Description | Metric | Target |
|-------------|------|-------------|--------|--------|
| BDQ-001 | Point Lookup | Single-row primary key lookup | Latency (p99) | ≤ 10ms |
| BDQ-002 | Range Scan | Date-range filter on 100M rows | Latency (p99) | ≤ 500ms |
| BDQ-003 | Full Table Scan | COUNT(*) on 1B rows | Latency (p99) | ≤ 30s |
| BDQ-004 | Aggregation Query | GROUP BY with SUM/AVG on 100M rows | Latency (p99) | ≤ 5s |
| BDQ-005 | Join Query | 5-table join on 10M rows each | Latency (p99) | ≤ 10s |
| BDQ-006 | Window Function | ROW_NUMBER/RANK over 50M rows | Latency (p99) | ≤ 15s |
| BDQ-007 | Concurrent Queries | 100 simultaneous mixed queries | Throughput (QPS) | ≥ 500 |
| BDQ-008 | Ad-hoc Analytics | Uncached analytical query | Latency (p95) | ≤ 60s |
| BDQ-009 | Sub-second OLAP | Pre-aggregated cube query | Latency (p99) | ≤ 1s |
| BDQ-010 | Text Search | Full-text search on 10M documents | Latency (p99) | ≤ 200ms |

### Test Procedure
1. Warm cache with 3 preliminary runs (discard results).
2. Execute query 10 times; record each duration.
3. Report median, p95, p99 latencies.
4. For concurrency tests, ramp up clients over 30s, sustain for 5min.

---

## 3. Storage Efficiency

Measures disk usage, compression ratios, and storage operations.

| Benchmark ID | Name | Description | Metric | Target |
|-------------|------|-------------|--------|--------|
| BDS-001 | Columnar Compression | Parquet vs raw CSV size | Compression ratio | ≥ 5:1 |
| BDS-002 | Dictionary Encoding | Low-cardinality column storage | Space saved | ≥ 80% |
| BDS-003 | Partition Pruning | Query only relevant partitions | Data scanned | ≤ 10% of total |
| BDS-004 | Compaction Overhead | Minor/major compaction time | Duration (10GB) | ≤ 60s |
| BDS-005 | Index Storage | B-tree index size vs table size | Index overhead | ≤ 15% |
| BDS-006 | Cold Storage Tier | Move data to cold tier | Migration speed | ≥ 100 MB/s |
| BDS-007 | Replication Overhead | 3x replication storage cost | Total multiplier | ≤ 3.2x |
| BDS-008 | TTL Data Purge | Time-to-live expiry cleanup | Purge speed | ≥ 50K rows/s |

### Test Procedure
1. Load dataset into storage engine.
2. Measure raw size, compressed size, index size.
3. Execute queries with and without partition pruning.
4. Run compaction; measure time and space reclaimed.
5. Verify data integrity post-compaction (checksum).

---

## 4. Data Quality Metrics

Measures accuracy, completeness, and consistency of ingested data.

| Benchmark ID | Name | Description | Metric | Target |
|-------------|------|-------------|--------|--------|
| BDQ-101 | Schema Validation | Reject malformed records | Rejection accuracy | ≥ 99.9% |
| BDQ-102 | Null Detection | Identify null/missing values | Detection rate | ≥ 99.5% |
| BDQ-103 | Duplicate Detection | Find duplicate records | Precision/Recall | ≥ 98% |
| BDQ-104 | Outlier Detection | Statistical outlier identification | F1 score | ≥ 0.90 |
| BDQ-105 | Referential Integrity | Foreign key constraint checks | Violation detection | 100% |
| BDQ-106 | Data Drift Detection | Schema/statistical drift alerts | Detection latency | ≤ 1 hour |
| BDQ-107 | Freshness SLA | Data available within SLA window | SLA compliance | ≥ 99.9% |
| BDQ-108 | End-to-end Reconciliation | Source vs target row counts | Match rate | ≥ 99.99% |

### Test Procedure
1. Inject known anomalies (nulls, duplicates, outliers) into test data.
2. Run quality pipeline; capture detection results.
3. Compare against ground truth labels.
4. Calculate precision, recall, F1 for each check type.
5. Measure time from ingestion to quality report availability.

---

## 5. Performance Metrics

Operational and system-level performance indicators.

| Benchmark ID | Name | Description | Metric | Target |
|-------------|------|-------------|--------|--------|
| BDP-001 | CPU Utilization | Ingestion peak CPU usage | % cores | ≤ 80% |
| BDP-002 | Memory Footprint | Query engine RAM usage | GB | ≤ 64 |
| BDP-003 | Disk I/O Throughput | Sequential read/write | MB/sec | ≥ 500 |
| BDP-004 | Network Throughput | Inter-node data transfer | Gbps | ≥ 10 |
| BDP-005 | GC Pause Times | JVM garbage collection pauses | Max pause | ≤ 200ms |
| BDP-006 | Connection Pool | Max concurrent connections | Count | ≥ 1000 |
| BDP-007 | Failover Recovery | Node failure detection + recovery | RTO | ≤ 30s |
| BDP-008 | Checkpoint Duration | State checkpoint to stable storage | Duration | ≤ 10s |
| BDP-009 | Query Queue Depth | Pending queries under load | Max depth | ≤ 5000 |
| BDP-010 | End-to-end Latency | Ingest → queryable data | p99 latency | ≤ 60s |

### Test Procedure
1. Deploy monitoring agents on all cluster nodes.
2. Run mixed workload (ingest + query) for 30 minutes.
3. Collect system metrics at 10-second intervals.
4. Report peak, average, and p99 for each resource metric.
5. Inject node failure; measure detection and recovery time.

---

## Running the Benchmarks

```bash
# Run all benchmarks
./scripts/run-benchmarks.sh --suite bigdata --all

# Run specific category
./scripts/run-benchmarks.sh --suite bigdata --category ingestion

# Run with custom dataset
./scripts/run-benchmarks.sh --suite bigdata --dataset /data/test-100gb

# Generate report
./scripts/run-benchmarks.sh --suite bigdata --report html
```

## Reporting

Results are output in JSON format and can be visualized via the built-in
dashboard at `http://localhost:8080/benchmarks`. Historical trends are
retained for 90 days.

## Environment Requirements

- Minimum 3-node cluster (8 vCPU, 32GB RAM, 500GB SSD per node)
- Network: 10Gbps interconnect
- OS: Linux x86_64 (kernel 5.4+)
- Java 11+ or Python 3.9+ depending on engine
