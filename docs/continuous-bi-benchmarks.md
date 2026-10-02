# Continuous BI Benchmarks

Performance benchmarks for continuous/real-time Business Intelligence systems, covering query latency, dashboard load time, concurrent users, and data freshness. Compiled from industry benchmarks, vendor publications, and independent studies (2024–2026).

---

## 1. Query Latency Benchmarks

Query latency measures the time from query submission to result delivery. For interactive BI, p95 and p99 percentiles matter more than averages—a fast mean with multi-second tails is unusable for dashboards.[3]

### Industry Targets

| Metric | Target | Source |
|--------|--------|--------|
| p95 dashboard query latency | ≤ 1.5 s | [7] |
| p95 interactive query latency | ≤ 2.0 s | [2] |
| p99 query latency | ≤ 3.0 s | [8] |
| Single-query aggregation latency (OLAP) | < 100 ms | [8] |
| TPC-H 1 TB: queries under 1 second | 13 of 22 | [3] |

### Measured Results

- **VeloDB vs ClickHouse (SSB SF-100, 100 GB):** At 25% update ratio, VeloDB query response time is 14× faster than ClickHouse. At 100% update ratio, the gap widens to 18×.[1]
- **ClickHouse (CRM workloads, 1B rows):** p95 ≈ 220 ms for aggregation templates; sustained 800 QPS. p99 ≈ 1.2 s during heavy merges.[8]
- **Managed cloud OLAP (compute-storage separated):** p95 ≈ 350 ms median, but more stable p99 due to autoscaling and managed caching.[8]
- **Exasol (TPC-H 1 TB, 160-core):** 5,489,326.4 QphH; 13 of 22 power-test queries completed in under one second.[3]
- **Snowflake (TPC-DS 3 TB, 14 dashboard queries):** Median and p99 latency tracked daily; 32-user benchmark yields stable results over 20-minute runs.[4]

### Key Insight

Average latency is a vanity metric. A system averaging 200 ms but spiking to 5 seconds during heavy ingestion is unusable for application backends. Evaluate p95/p99 stability under concurrent ingest and query load.[5]

---

## 2. Dashboard Load Benchmarks

Dashboard load time encompasses data fetching, semantic-layer processing, network transfer, and browser rendering. End-to-end latency includes all four stages.[3]

### Industry Targets

| Metric | Target | Source |
|--------|--------|--------|
| Dashboard initial load | ≤ 2 s (p95) | [2] |
| Dashboard interaction response | ≤ 1 s (p95) | [3] |
| Browser rendering time | ≤ 500 ms | [3] |
| API/delivery latency | ≤ 200 ms | [3] |

### Measured Results

- **BARC Benchmark (Qlik vs Power BI, 10M rows, 50 users):** Qlik delivered ~3× faster response times than Power BI. Normalized index: Qlik 100, Power BI 40 (productivity 31, scalability 48).[6]
- **Materialized views:** Reduced average aggregation latencies by 6× but increased write latency for ingestion by ~10%.[8]
- **Snowflake TPC-DS dashboard queries:** 14 representative queries (group-bys, filtered aggregations, window functions, joins, counting, ranking) run by each simulated user in random order with different predicate values.[4]

### Key Insight

A fast database query cannot compensate for delayed ingestion or slow browser rendering. The service target should state the required freshness, p95/p99 end-to-end latency, update frequency, expected user demand, and acceptable failure rate.[3]

---

## 3. Concurrent User Benchmarks

Concurrency measures how many simultaneous users a system can handle without degradation. The system must remain performant under high load to maintain strict real-time SLAs.[1]

### Industry Targets

| Metric | Target | Source |
|--------|--------|--------|
| Concurrent dashboard users | 100+ without degradation | [5] |
| Concurrent query rate | 100+ QPS | [5] |
| Query failures under peak load | 0% | [2] |
| Sustained QPS (OLAP) | 800+ | [8] |

### Measured Results

- **VeloDB concurrency (128-core, SSB-FLAT 100 GB):** Significantly higher QPS than ClickHouse Cloud at 10, 30, and 50 threads. ClickHouse was unable to complete all 13 SSB queries.[1]
- **Snowflake (TPC-DS 3 TB):** Scales from 1 to 128+ users by doubling; each user loops through 14 queries for 20 minutes. 32-user runs yield stable results.[4]
- **BARC (50 simultaneous users):** Qlik completed roughly twice as many sessions per hour as Power BI while keeping response times stable. Power BI exhibited greater variability as concurrency increased.[6]
- **ClickHouse (CRM, 100 concurrent clients):** Sustained 800 QPS for 10 minutes steady-state on 1B-row dataset.[8]
- **Exasol:** Recommends testing peak load of 200 concurrently submitted dashboard queries against defined p95 latency, throughput, timeout rate, and cost targets.[3]

### Key Insight

A system may complete many queries overall while some requests wait in queues. A fast result at limited concurrency does not establish performance during peak demand. Base the target on peak concurrent query demand, not total user numbers.[3]

---

## 4. Data Freshness Benchmarks

Data freshness is the time from a source change to queryable data. In 2026, real-time means this gap is sub-second or, at worst, sub-minute.[5]

### Industry Targets

| Metric | Target | Source |
|--------|--------|--------|
| Event-to-queryable latency | < 1 s (real-time) | [5] |
| Source-to-query freshness | ≤ 5 min (99% of rows) | [7] |
| End-to-end freshness (streaming) | p99 < 1.5 s | [9] |
| Ingestion burst handling | No backpressure at 2× expected rate | [5] |

### Measured Results

- **VeloDB (SSB SF-100, 25% updates):** Query response time 14× faster than ClickHouse under concurrent updates. Delete Bitmap mechanism skips deleted rows without comparison, keeping response times in hundreds of milliseconds.[1]
- **VeloDB (SSB SF-100, 100% updates):** 18× faster than ClickHouse. Unique Key model efficiently overwrites existing records.[1]
- **Iggy → VeloDB (2,000 events/s):** End-to-end p50 = 577 ms, p99 = 1,232 ms, p99.9 = 1,346 ms, max = 1,412 ms.[9]
- **Kafka → VeloDB (2,000 events/s):** End-to-end p50 = 789 ms, p99 = 3,588 ms, p99.9 = 10,022 ms, max = 10,247 ms. ~7× heavier tail than Iggy.[9]
- **Broker-only latency:** Iggy p99 = 2.5 ms, p99.9 = 2.8 ms. Kafka p99 ≈ 40 ms, p99.9 ≈ 80 ms.[9]
- **TSM-Bench (time series, 10K–1.4M data points/s):** Tree-based systems (QuestDB) achieve best runtimes for low-selectivity queries. ClickHouse excels at high-selectivity queries on large datasets.[10]

### Key Insight

Real-time analytics does not fail only when the average gets bad. It fails when freshness becomes unpredictable—when the 99th percentile silently becomes the user experience for the workflow that happens to land in the wrong window.[9]

---

## 5. Optimization Recommendations

### Query Latency Optimization

1. **Use materialized views** for common dashboard rollups—reduces aggregation latency by 6× at the cost of ~10% higher ingestion write latency.[8]
2. **Implement result caching** to avoid re-executing identical queries; calculate reusable results once and distribute through a delivery layer.[3]
3. **Optimize SQL and semantic models**—reduce dashboard query fan-out, limit data processed, and add execution capacity when needed.[3]
4. **Partition and index** to match query patterns; use bloom filters for high-cardinality filters.[8]
5. **Tune compression codecs** for the CPU vs I/O trade-off specific to your workload.[8]

### Dashboard Load Optimization

1. **Pre-aggregate data** at the required freshness cadence; avoid sending an independent database query for every browser refresh.[3]
2. **Stagger refresh activity** to prevent refresh storms from synchronized auto-refresh intervals.[3]
3. **Isolate competing workloads**—separate compute for ETL, data science, and semantic-layer queries.[3]
4. **Reduce browser rendering time** by limiting visualizations per dashboard and optimizing payload sizes.[3]

### Concurrency Optimization

1. **Use workload groups and queues** to prioritize latency-sensitive dashboard queries over heavy batch work.[3]
2. **Add capacity** when query optimization and workload controls can no longer maintain required tail latency and throughput.[3]
3. **Test with realistic mixed workloads**—testing only identical warm queries will overstate production capacity.[3]
4. **Scale horizontally** for high concurrency; real-time OLAP engines handle 100+ concurrent queries on fixed hardware by efficiently parallelizing reads.[5]

### Data Freshness Optimization

1. **Use streaming ingestion** (Kafka, Iggy, or CDC) instead of batch ETL for sub-minute freshness requirements.[5]
2. **Pre-aggregate at ingest time** using materialized views to shift compute cost from query side to ingest side.[5]
3. **Choose low-latency brokers**—broker architecture matters; Iggy delivered ~16× lower p99 latency than Kafka in broker-only tests.[9]
4. **Monitor end-to-end freshness** as a first-class SLI: `data_freshness_seconds` gauge from event_time to available_time.[7]
5. **Implement backpressure handling**—test ingestion at 2× expected rate to ensure bursts don't break the pipeline.[5]

### General Recommendations

1. **Define SLIs and SLOs** for each dimension: p95/p99 latency, freshness percentage, throughput, and error rate.[7]
2. **Run synthetic benchmarks in CI/CD**—gate deployments if p95 degrades beyond a threshold relative to baseline.[7]
3. **Use percentile-based alerting**—page when p95 crosses SLA for a sustained period (e.g., 10 minutes).[7]
4. **Profile before optimizing**—capture query execution plans (`EXPLAIN ANALYZE`) to pinpoint root causes: bad join order, missing predicate pushdown, or disk spilling.[7]
5. **Benchmark with production-like data**—replay actual production queries with similar concurrency patterns and load levels.[2]
6. **Test concurrency and ingest simultaneously**—a database returning a query in 0.01 s for one user but hanging for 10 s when 50 users query simultaneously is useless for real-time analytics.[5]

---

## Sources

[1] VeloDB Performance Series Part 1: Real-Time Analytics for Data Freshness, Concurrency, and Joins. https://www.velodb.io/blog/velodb-performance-series-part-1-real-time-analytics-for-data-freshness-concurrency-and-joins

[2] Freshworks's Approach to Benchmarking SQL Engines for Customer-Facing Analytics. https://medium.com/freshworks-engineering-blog/freshworkss-approach-to-benchmarking-sql-engines-for-customer-facing-analytics-a20fb26320d0

[3] Exasol: High-Concurrency BI — How to Evaluate Analytics Databases. https://www.exasol.com/hub/database/high-concurrency-bi/

[4] Snowflake: Benchmarking Concurrent Workloads for Operational Analytics BI. https://www.snowflake.com/en/blog/engineering/concurrency-benchmark-operationa-analytics-bi/

[5] ClickHouse: How to Choose a Database for Real-Time Analytics in 2026. https://clickhouse.com/resources/engineering/how-to-choose-a-database-for-real-time-analytics-in-2026

[6] BARC Ranks Qlik Cloud Analytics Ahead of Power BI on User Throughput and Stability. https://www.qlik.com/us/news/company/press-room/press-releases/barc-ranks-qlik-cloud-analytics-ahead-of-power-bi-on-user-throughput-and-stability

[7] Beefed.ai: Benchmarking & Monitoring Data Platform Performance. https://beefed.ai/en/benchmarking-monitoring-data-platform-performance

[8] Dataviewer: Benchmark CRM Query Performance on Modern OLAP Engine. https://dataviewer.cloud/how-to-benchmark-crm-query-performance-on-modern-olap-engine

[9] LaserData: Real-Time Analytics Benchmark — Apache Iggy vs Kafka into VeloDB Cloud. https://laserdata.com/blog/real-time-streaming-analytics-iggy-velodb-benchmark

[10] TSM-Bench: Benchmarking Time Series Database Systems for Monitoring Applications. https://exa.ai/library/publication/sfqx5w6v0zm
