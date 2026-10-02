# Big Data Benchmarks

> Research summary: query performance, ingestion throughput, storage efficiency, and cost analysis for big data systems (2024–2025 data).

---

## 1. Query Performance Benchmarks

### TPC-DS (10 TB Scale Factor, 99 Queries)

| System | Total Time | Avg per Query | Notes |
|---|---|---|---|
| Trino 468 | 4,442 s | 17.5 s | Fastest sequential; some correctness issues |
| Hive on MR3 | 4,874 s | 19.8 s | Best under concurrency (40 clients) |
| Hive on Tez | 12,707 s | 57.0 s | High container launch overhead |
| Spark 4.0 | 15,678 s | 37.7 s | Skewed by outlier queries |

### Cloud Data Warehouses (ClickBench, 100B Rows)

| System | Runtime | Cost |
|---|---|---|
| ClickHouse Cloud | 126 s | $16 |
| Snowflake (4XL) | 176 s | $25 |
| Databricks | — | 32× ClickHouse |
| Redshift | — | 57× ClickHouse |
| BigQuery | — | 101× ClickHouse |

### Hot Query Latency (PyPI Dataset, 100B+ Rows)

| System | Mean Aggregation | Configuration |
|---|---|---|
| ClickHouse Cloud | 0.28 s | 240 vCPUs |
| Snowflake 2XL | 0.75 s | 256 vCPUs |

### Key Observations

- ClickHouse is **2–3× faster** for hot queries vs. Snowflake with comparable resources.
- Trino leads on raw speed but shows higher variance under concurrency.
- Databricks reported **up to 40% performance improvement** across production workloads in 2025 via automatic tuning.
- Berkeley AMPLab: Shark/Impala outperform Hive by **3–4×** due to efficient task scheduling.

---

## 2. Ingestion Throughput Benchmarks

### Time-Series / Streaming (10M Rows, 1M Series)

| Protocol | Throughput (rows/s) | P99 Latency |
|---|---|---|
| gRPC Bulk (Arrow) | 2,678,839 | 8.8 ms |
| gRPC Stream | 1,562,134 | 10.8 ms |
| gRPC SDK (Unary) | 1,174,221 | 10.8 ms |
| InfluxDB Line Protocol | 889,051 | 13.1 ms |
| OTLP Logs (HTTP) | 621,367 | 16.4 ms |
| PostgreSQL INSERT | 73,760 | 101.6 ms |
| MySQL INSERT | 72,103 | 119.4 ms |

### Bulk Data Movement (NYC Taxi, 4B Rows)

| Tool | Full-Load Throughput | CDC Throughput |
|---|---|---|
| OLake | 580,113 rows/s | 55,555 rows/s |
| Fivetran | 46,395 rows/s | 26,910 rows/s |
| Debezium | 14,839 rows/s | 13,808 rows/s |
| Estuary | 3,982 rows/s | 3,085 rows/s |
| Airbyte Cloud | 457 rows/s | 585 rows/s |

### Key Observations

- **gRPC Bulk (Arrow)** is the fastest ingestion path — near zero-copy columnar transfer.
- Batch size matters: gRPC Bulk scales from 806K (batch=50) to 3.34M rows/s (batch=2000).
- SQL INSERT is **~37× slower** than gRPC Bulk — avoid for high-throughput pipelines.
- ClickHouse delivers **2× faster ingestion** than Snowflake at equal vCPUs.

---

## 3. Storage Efficiency Benchmarks

### Compression Ratios

| System / Codec | Compression Ratio | Notes |
|---|---|---|
| ClickHouse (optimal key) | 38% smaller than Snowflake | 0.902 TiB vs 1.33 TiB |
| Snowflake (clustered) | Baseline | 1.33 TiB |
| Zstandard (level 3) | ~2–3× | 20+ GB/s throughput |
| LZ4 | ~2× | Fastest decompression |
| Gzip | ~3–4× | Best ratio, slowest speed |
| Snappy | ~2× | Fastest, moderate ratio |

### Compression Throughput (Zstandard)

| Data Size | Level 1 | Level 3 | Level 9 |
|---|---|---|---|
| 1 KB | 397 MB/s | 395 MB/s | 304 MB/s |
| 100 KB | 14.0 GB/s | 13.5 GB/s | 6.2 GB/s |
| 1 MB | 20.0 GB/s | 19.8 GB/s | 4.4 GB/s |

### GPU vs CPU Compression (FCBench)

| Metric | CPU Median | GPU Median |
|---|---|---|
| Compression throughput | 0.21 GB/s | 73.71 GB/s |
| Speedup | 1× | **350×** |

### Key Observations

- **Zstandard level 3** offers the best speed/ratio balance for production workloads.
- Dictionary-based predictors (Chimp, Gorilla) outperform delta-based for time-series.
- GPU compression is viable for scientific/HPC datasets but has higher failure rates (7.3% vs 2.0%).
- Columnar formats (Parquet/ORC) with ZSTD achieve **1.6–2.1× compression** on scientific data.

---

## 4. Cost Analysis

### Cloud Storage Pricing (per GB/month)

| Tier | AWS S3 | Azure Blob | GCS |
|---|---|---|---|
| Standard/Hot | $0.023 | $0.018 | $0.020 |
| Infrequent/Cool | $0.0125 | $0.010 | $0.010 |
| Archive | $0.004 | $0.00099 | $0.0012 |
| Deep Archive | $0.00099 | — | $0.00099 |

### Data Warehouse Cost Comparison

| Cost Factor | ClickHouse Cloud | Snowflake | BigQuery |
|---|---|---|---|
| Storage | $0.02/GB | $0.023–0.04/GB | $0.02/GB |
| Query (on-demand) | — | — | $5/TB scanned |
| Compute | $0.36/RPU hr | $2–4/credit hr | $0.04–0.10/slot hr |
| Data loading | $41 (benchmark) | $202 (benchmark) | Free (batch) |
| Clustering maintenance | $0 | $900/month | Free (automatic) |

### Production Workload Cost (3-Month Dataset, Always-On)

| System | Monthly Cost |
|---|---|
| ClickHouse Cloud | ~$14,700 |
| Snowflake | ~$46,100 |
| On-premise DW (1 TB) | ~$41,667 ($500K/yr) |

### Key Observations

- ClickHouse is **3–5× more cost-effective** than Snowflake for equivalent performance.
- Snowflake clustering can cost **$900/month per table** — ClickHouse ordering keys are free.
- On-premise data warehousing is **~50× more expensive** than cloud object storage.
- BigQuery on-demand pricing ($5/TB scanned) becomes expensive at scale; capacity pricing is more predictable.

---

## 5. Optimization Recommendations

### Query Performance

1. **Use columnar storage** (Parquet/ORC) — enables vectorized execution and predicate pushdown.
2. **Create appropriate sort/clustering keys** — can improve query performance 6–10×.
3. **Leverage materialized views/projections** — pre-compute common aggregations.
4. **Choose the right engine**: Trino for interactive ad-hoc, ClickHouse for real-time analytics, Spark for batch ETL.
5. **Enable result caching** — reduces repeated query costs by 80–90%.

### Ingestion Throughput

1. **Use gRPC Bulk (Arrow)** for highest throughput — 2.7M+ rows/s vs 72K for SQL INSERT.
2. **Batch aggressively** — batch sizes of 1,000–2,000 rows maximize throughput.
3. **Prefer binary protocols** (Protobuf, Arrow) over text (SQL, JSON) — 3–37× faster.
4. **Use CDC for incremental loads** — avoids full-table scans and reduces load time by 10–100×.
5. **Parallelize writes** — scale ingestion linearly with concurrent writers.

### Storage Efficiency

1. **Adopt Zstandard (level 3)** — best balance of speed (20 GB/s) and ratio (2–3×).
2. **Use columnar formats** — 38% better compression than row-based storage.
3. **Implement tiered storage** — hot (SSD) → warm (object) → cold (archive) reduces costs 90%+.
4. **Apply dictionary encoding** for low-cardinality columns — 5–10× compression.
5. **Consider GPU compression** for scientific datasets — 350× faster than CPU.

### Cost Optimization

1. **Separate compute and storage** — scale each independently; avoid paying for idle compute.
2. **Use spot/preemptible instances** for batch workloads — 60–90% compute savings.
3. **Reserve capacity** for predictable workloads — 30–50% discount vs on-demand.
4. **Monitor clustering costs** — Snowflake auto-clustering can silently consume hundreds of credits/month.
5. **Implement data lifecycle policies** — auto-tier to cold storage after 30/60/90 days.
6. **Use compression before storage** — every 2× compression halves storage costs.

---

## Sources

- TPC-DS Benchmark Results (tpc.org, 2025)
- ClickHouse vs Snowflake Benchmarks (clickhouse.com, 2025)
- GreptimeDB Ingestion Protocol Benchmarks (greptime.com, 2026)
- OLake Ingestion Benchmarks (olake.io, 2026)
- FCBench Compression Study (VLDB, 2025)
- Spark Compression Codec Analysis (dlabi.org, 2024)
- Cloud Storage Pricing (AWS, Azure, GCP documentation, 2024–2025)
- Databricks 2025 Performance Review (databricks.com, 2025)
- Berkeley AMPLab Big Data Benchmark (amplab.cs.berkeley.edu)
