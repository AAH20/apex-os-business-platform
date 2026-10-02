# Continuous BI Implementation

Real-time business intelligence architecture covering streaming ingestion, materialized views, query optimization, and caching for sub-second dashboard experiences.

---

## 1. Real-Time Dashboard Architecture

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','primaryBorderColor':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#0f3460','edgeLabelBackground':'#1a1a2e'}}}%%
flowchart TB
    subgraph Sources["Data Sources"]
        DB[(Transactional DB)]
        API[API Events]
        LOG[Log Streams]
        IOT[IoT / Sensors]
    end

    subgraph Ingestion["Streaming Ingestion Layer"]
        KAFKA[Apache Kafka / Kinesis]
        CDC[CDC Connector]
        BATCH[Batch Ingest]
    end

    subgraph Processing["Stream Processing"]
        FLINK[Apache Flink / Spark Streaming]
        ST[Streaming Tables]
        MV[Materialized Views]
    end

    subgraph Storage["Storage Layer"]
        LAKE[Data Lake - Bronze]
        DW[Data Warehouse - Silver/Gold]
        OLAP[OLAP Cube / Columnar]
    end

    subgraph Serving["Serving Layer"]
        CACHE[Redis / CDN Cache]
        API_GW[API Gateway]
        PUSH[WebSocket / SSE Push]
    end

    subgraph Presentation["Presentation Layer"]
        DASH[Real-time Dashboards]
        ALERT[Alerting Engine]
        ML[ML Predictions]
    end

    DB --> CDC
    API --> KAFKA
    LOG --> KAFKA
    IOT --> KAFKA
    CDC --> KAFKA
    BATCH --> LAKE
    KAFKA --> FLINK
    FLINK --> ST
    ST --> MV
    ST --> LAKE
    LAKE --> DW
    DW --> OLAP
    MV --> DW
    OLAP --> CACHE
    OLAP --> API_GW
    CACHE --> DASH
    API_GW --> DASH
    PUSH --> DASH
    DW --> ALERT
    ML --> DASH
```

**Key principles:**
- **Lambda + Kappa hybrid**: Batch for historical depth, streaming for real-time freshness
- **CQRS separation**: Write-optimized ingestion path, read-optimized serving path
- **Event-driven updates**: Push model via WebSocket/SSE eliminates polling overhead
- **Tiered storage**: Hot (Redis) → Warm (OLAP) → Cold (Data Lake)

---

## 2. Streaming ETL Patterns

### 2.1 Change Data Capture (CDC) Pipeline

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','primaryBorderColor':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#0f3460'}}}%%
flowchart LR
    SRC[(Source DB)] -->|WAL / Binlog| CDC[Debezium / CDC]
    CDC -->|Change Events| K[Kafka Topic]
    K --> T1[Stream Processor]
    K --> T2[Stream Processor]
    T1 -->|Enriched| SINK1[(Silver Tables)]
    T2 -->|Aggregated| SINK2[(Gold / MV)]
    SINK1 --> SINK2
```

### 2.2 Core Patterns

| Pattern | Use Case | Latency | Implementation |
|---------|----------|---------|----------------|
| **CDC Replication** | DB → Lake sync | < 5s | Debezium + Kafka |
| **Windowed Aggregation** | Real-time KPIs | 1-30s | Flink tumbling/sliding windows |
| **Stream-Table Join** | Enrich events with dims | < 2s | Flink lookup joins |
| **Exactly-Once Sink** | Financial data | < 10s | Idempotent writes + 2PC |
| **Dead Letter Queue** | Error handling | Async | Kafka DLT + replay |
| **Schema Evolution** | Changing sources | N/A | Schema Registry (Avro/Protobuf) |

### 2.3 Idempotent Sink Pattern

```python
# Pseudocode: Idempotent upsert into materialized view
def process_event(event):
    key = event["id"]
    watermark = event["timestamp"]
    
    # Skip out-of-order events
    if watermark <= last_processed_watermark[key]:
        return  # Deduplicate
    
    # Upsert with merge semantics
    target.merge(
        source=event,
        on=key,
        when_matched="update",
        when_not_matched="insert"
    )
    
    # Update watermark
    last_processed_watermark[key] = watermark
```

### 2.4 Backpressure & Recovery

- **Kafka consumer lag monitoring**: Alert at > 10k messages
- **Watermark-based windowing**: Handle late-arriving data gracefully
- **Checkpointing**: Flink savepoints for stateful recovery
- **Graceful degradation**: Fall back to last-known-good on upstream failure

---

## 3. Materialized View Strategies

### 3.1 MV Architecture Tiers

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','primaryBorderColor':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#0f3460'}}}%%
flowchart TB
    subgraph Bronze["Bronze - Raw"]
        B1[Raw Events Table]
        B2[CDC Log Table]
    end

    subgraph Silver["Silver - Cleaned"]
        S1[Streaming Table - Deduped]
        S2[Streaming Table - Enriched]
    end

    subgraph Gold["Gold - Aggregated"]
        MV1["MV: Hourly Sales"]
        MV2["MV: Daily KPIs"]
        MV3["MV: Real-time Inventory"]
        MV4["MV: Customer 360"]
    end

    subgraph Serving["Serving - Pre-computed"]
        P1[Pre-joined Dashboard Tables]
        P2[Rollup Tables]
    end

    B1 --> S1
    B2 --> S1
    S1 --> S2
    S2 --> MV1
    S2 --> MV2
    S2 --> MV3
    S2 --> MV4
    MV1 --> P1
    MV2 --> P1
    MV3 --> P2
    MV4 --> P2
```

### 3.2 Refresh Strategies

| Strategy | Freshness | Cost | Best For |
|----------|-----------|------|----------|
| **Continuous (Streaming)** | Sub-second | High | Real-time dashboards |
| **Incremental (Scheduled)** | 1-5 min | Medium | Near-real-time BI |
| **Full Rebuild** | Hourly/Daily | Low | Historical snapshots |
| **On-Demand** | Manual | Low | Ad-hoc analysis |

### 3.3 MV Definition Patterns

```sql
-- Real-time KPI materialized view (incremental refresh)
CREATE MATERIALIZED VIEW mv_realtime_sales
REFRESH EVERY 30 SECONDS
AS SELECT
    date_trunc('minute', event_ts) AS minute_bucket,
    region,
    product_category,
    COUNT(*) AS order_count,
    SUM(amount) AS total_revenue,
    AVG(amount) AS avg_order_value,
    COUNT(DISTINCT customer_id) AS unique_customers
FROM streaming_orders
WHERE event_ts >= now() - INTERVAL '24 HOURS'
GROUP BY 1, 2, 3;

-- Hierarchical rollup for dashboard drill-down
CREATE MATERIALIZED VIEW mv_sales_hierarchy
REFRESH EVERY 5 MINUTES
AS SELECT
    year, quarter, month, week, day,
    region, city, store,
    SUM(revenue) AS revenue,
    SUM(units) AS units_sold
FROM silver_orders
GROUP BY GROUPING SETS (
    (year, quarter, month, week, day),
    (year, quarter, month, week),
    (year, quarter, month),
    (year, quarter),
    (year),
    (year, quarter, month, day, region),
    (year, quarter, month, day, region, city),
    (year, quarter, month, day, region, city, store)
);
```

### 3.4 MV Selection Heuristics

- **Query frequency × base query cost** = priority score
- MVs pay off when: `refresh_cost < (query_cost × query_frequency)`
- Target: 80% of dashboard queries served by MVs
- Monitor MV staleness: `last_refresh_time` vs `max_acceptable_lag`

---

## 4. Query Optimization Techniques

### 4.1 Query Performance Stack

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','primaryBorderColor':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#0f3460'}}}%%
flowchart LR
    subgraph Query["Query Layer"]
        Q1[Query Parser]
        Q2[Query Rewriter]
        Q3[Cost-Based Optimizer]
        Q4[Execution Engine]
    end

    subgraph Optimizations["Optimization Techniques"]
        O1[Predicate Pushdown]
        O2[Partition Pruning]
        O3[Column Pruning]
        O4[Join Reordering]
        O5[Bitmap Index Scan]
        O6[Parallel Execution]
        O7[Result Cache]
        O8[Vectorized Execution]
    end

    subgraph Storage["Storage Optimizations"]
        S1[Partitioning]
        S2[Z-Order / Clustering]
        S3[Columnar Format - Parquet/ORC]
        S4[Compression - ZSTD/Snappy]
        S5[Statistics & Histograms]
    end

    Q1 --> Q2 --> Q3 --> Q4
    O1 --> Q3
    O2 --> Q3
    O3 --> Q3
    O4 --> Q3
    O5 --> Q4
    O6 --> Q4
    O7 --> Q4
    O8 --> Q4
    S1 --> Q4
    S2 --> Q4
    S3 --> Q4
    S4 --> Q4
    S5 --> Q3
```

### 4.2 Key Techniques

| Technique | Impact | Implementation |
|-----------|--------|----------------|
| **Predicate Pushdown** | 10-100x | Filter at storage layer before scan |
| **Partition Pruning** | 5-50x | Query only relevant date/region partitions |
| **Column Pruning** | 3-10x | Read only needed columns (columnar) |
| **Z-Order Clustering** | 2-5x | Co-locate related data for min/max pruning |
| **Bitmap Indexes** | 10-100x | Low-cardinality filter acceleration |
| **Approximate Aggregates** | 100-1000x | HyperLogLog, t-digest for distinct/percentile |
| **Query Result Cache** | ∞ (cache hit) | Redis/Memcached for repeated queries |
| **Prepared Statements** | 1.2-2x | Avoid re-parse/re-plan overhead |
| **Parallel Scan** | Linear scaling | Multi-threaded partition reads |
| **Vectorized Execution** | 2-5x | Batch processing with SIMD |

### 4.3 Dashboard-Specific Optimizations

```sql
-- Pre-aggregated dashboard query (uses MV, not base tables)
-- Instead of scanning 500M rows:
SELECT * FROM mv_realtime_sales
WHERE minute_bucket >= now() - INTERVAL '1 HOUR'
  AND region = $1;

-- Approximate distinct count (HyperLogLog)
SELECT
    date_trunc('hour', ts) AS h,
    approx_count_distinct(customer_id) AS unique_customers
FROM events
GROUP BY 1;

-- Percentile via t-digest (approximate, 100x faster)
SELECT
    approx_percentile(response_time, 0.95) AS p95,
    approx_percentile(response_time, 0.99) AS p99
FROM api_logs
WHERE ts >= now() - INTERVAL '5 minutes';
```

### 4.4 Query Plan Analysis Checklist

1. **Full table scan?** → Add partition filter or index
2. **Nested loop join on large tables?** → Force hash/merge join
3. **Sort spilling to disk?** → Increase `work_mem` or pre-sort in MV
4. **Sequential scan on columnar?** → Check column pruning
5. **High planning time?** → Use prepared statements / plan caching

---

## 5. Caching Strategies

### 5.5 Multi-Layer Cache Architecture

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','primaryBorderColor':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#0f3460'}}}%%
flowchart TB
    subgraph Client["Client Layer"]
        C1[Browser Cache]
        C2[CDN Edge Cache]
    end

    subgraph App["Application Layer"]
        A1[In-Memory Cache - Caffeine]
        A2[Distributed Cache - Redis Cluster]
    end

    subgraph Data["Data Layer"]
        D1[Query Result Cache]
        D2[Materialized View - Hot]
        D3[OLAP Cube Cache]
    end

    subgraph Invalidation["Invalidation Layer"]
        I1[Event-Driven Invalidation]
        I2[TTL-Based Expiry]
        I3[Version-Based ETags]
    end

    C1 --> C2 --> A1 --> A2 --> D1 --> D2 --> D3
    I1 -.->|Invalidate| A2
    I1 -.->|Invalidate| D1
    I2 -.->|Expire| A1
    I2 -.->|Expire| A2
    I3 -.->|Validate| C1
```

### 5.2 Cache Tier Details

| Tier | Technology | TTL | Hit Target | Use Case |
|------|-----------|-----|------------|----------|
| **L1 - Browser** | ETag / LocalStorage | Versioned | 60% | Static dashboard config |
| **L2 - CDN** | CloudFront / Cloudflare | 1-60s | 40% | Shared dashboard snapshots |
| **L3 - In-Memory** | Caffeine / Guava | 10-60s | 80% | Per-user session data |
| **L4 - Distributed** | Redis Cluster | 30s-5min | 90% | Cross-user query results |
| **L5 - OLAP Cache** | Druid / Pinot | 5-15min | 95% | Pre-aggregated segments |

### 5.3 Cache Invalidation Patterns

```python
# Event-driven cache invalidation
class CacheInvalidator:
    def on_new_data(self, event):
        """Invalidate affected cache keys when new data arrives."""
        affected_dashboards = self.reverse_index[event.table]
        for dash_id in affected_dashboards:
            # Invalidate specific dashboard cache
            cache.delete(f"dash:{dash_id}:data")
            cache.delete(f"dash:{dash_id}:meta")
            # Publish invalidation event for distributed caches
            pubsub.publish(f"invalidate:{dash_id}", event.timestamp)

    def on_mv_refresh(self, mv_name):
        """Invalidate when materialized view refreshes."""
        cache.delete_pattern(f"mv:{mv_name}:*")
        # Warm cache with fresh data
        self.warm_cache(mv_name)

# Cache-aside with write-through for critical KPIs
def get_kpi(dashboard_id, kpi_name):
    key = f"kpi:{dashboard_id}:{kpi_name}"
    value = cache.get(key)
    if value is None:
        # Cache miss - compute from MV (fast)
        value = mv_query(kpi_name)
        cache.set(key, value, ttl=30)  # Short TTL for freshness
    return value
```

### 5.4 Cache Warming Strategy

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','primaryBorderColor':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#0f3460'}}}%%
flowchart LR
    SCHED[Scheduler] -->|Every 30s| W1[Warm Top Dashboards]
    SCHED -->|Every 5min| W2[Warm MV Results]
    SCHED -->|On MV refresh| W3[Warm Affected Keys]
    W1 --> REDIS[(Redis)]
    W2 --> REDIS
    W3 --> REDIS
    REDIS --> DASH[Sub-second Dashboard Load]
```

### 5.5 Cache Consistency Guarantees

| Strategy | Consistency | Staleness | Complexity |
|----------|-------------|-----------|------------|
| **TTL Expiry** | Eventual | TTL duration | Low |
| **Write-Through** | Strong | None | Medium |
| **Event Invalidation** | Near-strong | < 1s | Medium |
| **Version-Based** | Strong | None | High |
| **Cache-Aside + TTL** | Eventual | TTL duration | Low |

**Recommendation**: TTL for most dashboards (30s), event-driven invalidation for real-time KPIs, version-based for financial data.

---

## Summary

| Layer | Target Latency | Key Technology |
|-------|---------------|----------------|
| Ingestion | < 5s | Kafka + CDC |
| Stream Processing | < 2s | Flink / Spark Streaming |
| Materialized Views | 30s-5min refresh | Incremental MV |
| Query Serving | < 100ms | MV + Columnar + Cache |
| Dashboard Render | < 1s | WebSocket push + L1-L4 cache |

**Success metrics:**
- Dashboard p95 load time: < 1s
- Data freshness: < 30s for real-time KPIs
- Cache hit rate: > 85%
- MV coverage: > 80% of dashboard queries
