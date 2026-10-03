# New Projects Performance Guide

## 1. Performance Optimization

### Frontend
- **Code splitting**: Use dynamic imports for route-level and heavy components.
- **Tree shaking**: Remove dead code; audit bundle size with `webpack-bundle-analyzer`.
- **Lazy loading**: Defer non-critical images, scripts, and third-party widgets.
- **Minimize re-renders**: Memoize expensive computations (`useMemo`, `useCallback`); avoid inline object props in React.
- **Virtualization**: Render large lists with `react-window` or `react-virtualized`.
- **Critical CSS**: Inline above-the-fold styles; defer non-critical CSS.
- **Image optimization**: Serve WebP/AVIF; use responsive `srcset`; compress to <200 KB.

### Backend
- **Async I/O**: Use non-blocking patterns (async/await, event loops) for all I/O-bound work.
- **Connection pooling**: Reuse DB and HTTP connections; avoid per-request connections.
- **Compression**: Enable gzip/brotli on all text responses.
- **Payload size**: Return only requested fields (sparse fieldsets); paginate large collections.
- **Timeouts**: Set aggressive timeouts on all external calls (200–500 ms for internal, 1–3 s for third-party).
- **Profiling**: Continuously profile with pprof/perf; optimize hot paths only.

### Infrastructure
- **CDN**: Serve static assets and cacheable APIs from edge locations.
- **HTTP/2 or HTTP/3**: Enable multiplexing and header compression.
- **Keep-alive**: Reuse TCP connections between client and server.

---

## 2. Caching Strategies

### Multi-Layer Caching

| Layer | Tool | TTL | Use Case |
|-------|------|-----|----------|
| Browser | Cache-Control headers | Varies | Static assets, API responses |
| CDN Edge | Cloudflare / CloudFront | 1–24 h | Public content, API responses |
| Application | Redis / Memcached | 5–60 min | Session data, query results |
| Database | Query cache / Materialized views | 1–24 h | Expensive joins, reports |

### Cache Invalidation
- **Write-through**: Update cache on every write; simplest consistency.
- **Write-behind**: Update cache asynchronously; higher throughput, eventual consistency.
- **TTL-based**: Auto-expire stale data; use for non-critical reads.
- **Event-driven**: Invalidate on domain events (e.g., `UserUpdated` → evict user cache).

### Cache Patterns
- **Cache-aside (lazy loading)**: Check cache → query DB → populate cache. Most common.
- **Read-through**: Cache layer fetches from DB transparently.
- **Write-through**: Write to cache and DB synchronously.
- **Refresh-ahead**: Proactively refresh hot keys before expiry.

### Best Practices
- Never cache without a fallback; degrade gracefully on cache miss.
- Use cache versioning (`v1:user:123`) to simplify invalidation.
- Set memory limits and eviction policies (LRU/LFU) on Redis.
- Monitor hit ratio; target >90% for hot data.

---

## 3. Query Optimization

### Database Indexing
- Index all columns used in `WHERE`, `JOIN`, `ORDER BY`, and `GROUP BY`.
- Use composite indexes for multi-column filters (order matters: equality first, range last).
- Avoid indexing low-cardinality columns (boolean, status with few values).
- Regularly run `EXPLAIN ANALYZE` to detect sequential scans and missing indexes.

### Query Design
- **Select only needed columns** — avoid `SELECT *`.
- **Use pagination** (`LIMIT`/`OFFSET` or cursor-based) for large datasets.
- **Batch operations**: Use `INSERT ... VALUES (...),(...)` and bulk updates.
- **Avoid N+1**: Use JOINs, subqueries, or DataLoader pattern.
- **Denormalize selectively**: Pre-compute aggregates in summary tables for read-heavy workloads.

### ORM Best Practices
- Disable lazy loading in production; use eager loading (`select_related`, `include`).
- Use raw SQL or query builders for complex reports.
- Enable query logging in staging to catch slow queries.

### NoSQL Considerations
- Design schemas around query patterns, not entities.
- Use partition keys that distribute load evenly.
- Avoid hot partitions; add write sharding if needed.

---

## 4. Scaling Strategies

### Vertical Scaling (Scale Up)
- Increase CPU/RAM/disk on existing instances.
- Pros: Simple, no code changes.
- Cons: Hard limit, expensive, single point of failure.
- Use for: Moderate growth, stateful services (databases).

### Horizontal Scaling (Scale Out)
- Add more instances behind a load balancer.
- Pros: Near-linear scale, fault tolerance.
- Cons: Requires stateless design, distributed systems complexity.
- Use for: Stateless web/API servers, microservices.

### Database Scaling
- **Read replicas**: Offload read traffic; use for reporting and analytics.
- **Sharding**: Partition data by tenant/region/hash; use for write-heavy workloads.
- **Partitioning**: Split large tables by date/range; improve query performance.

### Microservices & Decoupling
- Decompose monoliths by bounded context.
- Use message queues (Kafka, RabbitMQ, SQS) for async communication.
- Implement circuit breakers (Hystrix, Resilience4j) to prevent cascade failures.

### Auto-Scaling
- Configure CPU/memory-based auto-scaling policies.
- Use predictive scaling for known traffic patterns.
- Set minimum instances to handle baseline load; scale to zero only for non-critical jobs.

---

## 5. Cost Optimization

### Compute Rightsizing
- Analyze CPU/memory utilization; downsize over-provisioned instances.
- Use spot/preemptible instances for fault-tolerant batch workloads (up to 90% savings).
- Choose ARM-based instances (Graviton, Ampere) for better price-performance.

### Storage Tiering
- Move infrequently accessed data to cold storage (S3 Glacier, Azure Archive).
- Implement lifecycle policies to auto-transition objects.
- Compress data before storage; use columnar formats (Parquet, ORC) for analytics.

### Network Costs
- Use CDN to reduce origin bandwidth.
- Compress API responses (brotli).
- Avoid cross-region data transfer; deploy in a single region when possible.

### Serverless & Managed Services
- Use Lambda/Cloud Functions for spiky, event-driven workloads.
- Use managed databases (RDS, Cloud SQL) to reduce operational overhead.
- Evaluate serverless containers (Cloud Run, Fargate) for variable workloads.

### Monitoring & Governance
- Set budget alerts at 50%, 80%, and 100% of monthly spend.
- Tag all resources by team/project for cost attribution.
- Review and delete unused resources (orphaned volumes, idle load balancers).
- Use reserved instances or savings plans for predictable baseline load (30–60% savings).

### Cost-per-Transaction Tracking
- Instrument all services with cost metrics (cost per request, cost per user).
- Optimize the most expensive endpoints first.
- Cache aggressively for high-traffic, low-margin endpoints.

---

## Quick Reference Checklist

- [ ] Enable gzip/brotli compression
- [ ] Configure CDN for static assets
- [ ] Set up Redis/Memcached caching layer
- [ ] Add database indexes for slow queries
- [ ] Implement connection pooling
- [ ] Configure auto-scaling policies
- [ ] Set up monitoring and alerting
- [ ] Enable budget alerts and cost tagging
- [ ] Use spot instances for batch workloads
- [ ] Review and rightsize resources monthly
