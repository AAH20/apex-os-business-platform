# Caching Strategy Guide

## 1. Caching Patterns

### Cache-Aside (Lazy Loading)
- Application checks cache first; on miss, loads from database and populates cache.
- Most common pattern; simple to implement.
- Risk: stale data if invalidation is incomplete.

### Read-Through
- Cache sits between application and data store; cache handles loading on miss.
- Application always reads from cache; cache fetches from DB transparently.
- Good for read-heavy workloads with predictable access patterns.

### Write-Through
- Writes go to cache and database simultaneously.
- Ensures cache and DB are always consistent.
- Higher write latency; suitable when read performance is critical.

### Write-Behind (Write-Back)
- Writes go to cache only; cache asynchronously flushes to database.
- Lowest write latency; risk of data loss if cache fails before flush.
- Use only when writes are idempotent or loss is acceptable.

### Refresh-Ahead
- Cache proactively refreshes entries before they expire.
- Reduces latency spikes from cache misses on hot keys.
- Best for small, hot datasets with predictable access.

---

## 2. Cache Invalidation Strategies

### Time-Based Expiration (TTL)
- Each entry has a TTL; cache evicts after expiry.
- Simple but can serve stale data within the TTL window.
- Choose TTL based on data volatility: seconds for session data, hours for reference data.

### Event-Driven Invalidation
- Invalidate cache entries when underlying data changes.
- Use database triggers, change data capture (CDC), or application events.
- Most accurate but requires tight coupling with data layer.

### Version-Based Invalidation
- Include a version or timestamp in cache keys.
- Bump version on write; old keys become unreachable and are evicted by LRU.
- Eliminates stale reads without explicit invalidation logic.

### Explicit Eviction
- Application explicitly removes keys on mutation.
- Use for critical data where staleness is unacceptable.
- Combine with TTL as a safety net.

### Cache Warming
- Pre-populate cache on startup or before traffic spikes.
- Prevents cold-start latency and thundering herd.
- Schedule during low-traffic windows.

---

## 3. Cache Consistency

### Strong Consistency
- Cache and database are updated atomically (e.g., distributed transactions).
- Highest consistency guarantee; highest latency and complexity.
- Use for financial data, inventory counts, or compliance-critical records.

### Eventual Consistency
- Cache may be temporarily stale but converges with database.
- Achieved via TTL, event-driven invalidation, or read-repair.
- Suitable for most business applications (profiles, catalogs, analytics).

### Consistency Patterns
- **Read-Your-Writes**: Ensure a client sees its own writes immediately (sticky sessions or write-through).
- **Monotonic Reads**: Guarantee a client never sees older data after seeing newer data (version vectors).
- **Causal Consistency**: Preserve cause-effect relationships across related keys (session sequencing).

### Handling Inconsistency
- Use conditional writes (compare-and-swap) for concurrent updates.
- Implement cache stampede protection (request coalescing, jittered TTL).
- Log and alert on consistency violations detected by reconciliation jobs.

---

## 4. Multi-Level Caching

### L1: In-Process (Local) Cache
- Embedded in application memory (e.g., Caffeine, Guava Cache).
- Sub-millisecond latency; limited by heap size.
- Use for hot, read-only or read-mostly data (config, feature flags).

### L2: Distributed Cache
- Shared across instances (e.g., Redis, Memcached).
- Network latency (~1ms); larger capacity; shared state.
- Use for session data, query results, rate-limit counters.

### L3: CDN / Edge Cache
- Geographically distributed (e.g., Cloudflare, Fastly).
- Caches static assets and API responses at the edge.
- Use for public, cacheable content (images, JS, public APIs).

### L4: Database Query Cache
- Built into the database (e.g., MySQL query cache, PostgreSQL prepared statements).
- Transparent to application; limited control.
- Use as a last-resort safety net; do not rely on it for correctness.

### Cache Hierarchy Flow
```
Request → L1 (local) → L2 (distributed) → L3 (CDN) → DB
```
- Each level has its own TTL; lower levels should have longer TTLs.
- Invalidate top-down: L1 first, then L2, then L3.
- Use cache tags or key prefixes for bulk invalidation across levels.

---

## 5. Cache Monitoring

### Key Metrics
| Metric | Description | Target |
|--------|-------------|--------|
| Hit Ratio | Hits / (Hits + Misses) | > 90% for hot data |
| Eviction Rate | Keys evicted per second | Near zero under normal load |
| Latency (p50/p99) | Cache read/write latency | p99 < 5ms for L1, < 20ms for L2 |
| Memory Usage | % of allocated memory used | < 80% to avoid evictions |
| Stale Read Rate | Reads returning outdated data | < 0.1% for critical paths |

### Alerting Thresholds
- **Hit ratio drops below 80%**: Investigate key distribution or TTL changes.
- **Eviction rate spikes**: Increase cache size or review memory pressure.
- **p99 latency exceeds threshold**: Check network, serialization, or hot keys.
- **Memory usage > 85%**: Scale up or review eviction policy.

### Observability Practices
- Emit cache metrics to Prometheus/StatsD with labels for cache name, operation, and result.
- Trace cache calls in distributed tracing (OpenTelemetry) to identify cache-related latency.
- Log cache misses for cold keys to identify warming opportunities.
- Run periodic cache audits comparing cache state against database for critical keys.

### Tools
- **Redis**: `INFO` command, RedisInsight, `SLOWLOG`.
- **Memcached**: `stats`, `memcached-tool`.
- **Application-level**: Micrometer, Dropwizard Metrics, or custom instrumentation.
- **Reconciliation**: Scheduled jobs comparing cache vs. database for sample keys.

---

## Summary

| Concern | Recommendation |
|---------|---------------|
| Pattern | Cache-Aside for most; Write-Through for critical writes |
| Invalidation | TTL + event-driven for accuracy; version-based for simplicity |
| Consistency | Eventual for most; strong for financial/compliance data |
| Multi-level | L1 (local) + L2 (Redis) + L3 (CDN) with top-down invalidation |
| Monitoring | Hit ratio, eviction rate, latency, memory usage, stale read rate |
