# APEX-OS Business Platform — Performance Tuning Guide

> **Version:** 2.0.0 | **Last Updated:** 2026-10-02

---

## 1. Performance Optimization

### 1.1 General Principles
- **Measure first**: Profile with APM (OpenTelemetry, Datadog) before optimizing.
- **Set SLOs**: p95 < 200ms, p99 < 500ms, error rate < 0.1%.
- **Budget enforcement**: CI checks for bundle size, Lighthouse score, API latency.

### 1.2 Backend (Node.js)
- **Async I/O**: Use async/await for all I/O-bound operations.
- **Connection pooling**: Reuse DB and HTTP connections; avoid per-request creation.
- **Batch operations**: Group inserts/updates (500–1000 rows per batch).
- **Lazy loading**: Defer non-critical work (emails, webhooks) to background workers.
- **Compression**: Enable brotli/gzip middleware for responses > 1KB.
- **Keep-alive**: Configure HTTP keep-alive; tune `max_keepalive_requests`.
- **V8 tuning**: Set `--max-old-space-size` and `--max-semi-space-size` via `NODE_OPTIONS`.
- **Thread pool**: Increase `UV_THREADPOOL_SIZE` (default 4 → 16) for I/O-heavy workloads.

### 1.3 Background Jobs (BullMQ)
- Use a job queue for long-running tasks; set concurrency based on downstream capacity.
- Implement idempotency keys for retry safety.
- Configure exponential backoff with max delay caps.

---

## 2. Caching Strategy

### 2.1 Cache Layers

| Layer | Tool | TTL | Use Case |
|-------|------|-----|----------|
| CDN | CloudFront / Cloudflare | 1h–24h | Static assets, public API |
| In-process | LRU / node-cache | 30s–5m | Config, feature flags |
| Distributed | Redis | 5m–24h | Sessions, query results |
| Browser | Cache-Control | Varies | Static assets, API responses |

### 2.2 Cache Invalidation
- **TTL + explicit purge**: Set TTL as safety net; purge on mutation events.
- **Versioned keys**: Embed entity version (e.g., `user:42:v3`) for safe invalidation.
- **Pub/sub invalidation**: Use Redis pub/sub to clear local caches across pods.

### 2.3 Cache Patterns
- **Cache-aside**: Check cache → fall back to DB → populate cache.
- **Read-through**: Cache layer handles DB fetch transparently.
- **Write-through**: Write to cache and DB synchronously.
- **Refresh-ahead**: Proactively refresh hot keys before expiry.

### 2.4 Anti-patterns
- **Cache stampede**: Use request coalescing / single-flight for hot keys.
- **Thundering herd**: Add jitter to TTLs (±10%).
- **Large keys**: Keep values < 1MB; split large objects.

### 2.5 Redis Configuration
```
maxmemory: 75% of available RAM
maxmemory-policy: allkeys-lru
maxmemory-samples: 5
appendonly: yes
appendfsync: everysec
lazyfree-lazy-eviction: yes
io-threads: 4
```

---

## 3. Database Optimization

### 3.1 Indexing
- Index all columns in `WHERE`, `JOIN`, `ORDER BY`, `GROUP BY`.
- Use composite indexes for multi-column queries; order by selectivity.
- Use covering indexes for index-only scans.
- Use partial indexes for soft-deleted records (`WHERE deleted_at IS NULL`).
- Use GIN indexes for JSONB columns.
- Monitor slow query log; aim for < 1% slow queries.

### 3.2 Query Optimization
- Use `EXPLAIN ANALYZE` to inspect query plans.
- Avoid `SELECT *`; fetch only needed columns.
- Use cursor-based pagination for large result sets.
- Replace N+1 queries with JOINs or batch fetching.
- Use prepared statements to avoid re-parsing.

### 3.3 PostgreSQL Parameters

| Parameter | Recommended | Rationale |
|-----------|-------------|-----------|
| `shared_buffers` | 25% of RAM | Cache frequently accessed data |
| `effective_cache_size` | 75% of RAM | Planner's cache assumption |
| `work_mem` | 16–32MB | Per-sort/hash operation |
| `maintenance_work_mem` | 64–128MB | VACUUM, CREATE INDEX |
| `max_connections` | 200 (with PgBouncer) | Burst traffic |
| `random_page_cost` | 1.1 (SSD) | Encourage index scans |
| `effective_io_concurrency` | 200 (SSD) | Parallel I/O |
| `checkpoint_completion_target` | 0.9 | Spread checkpoint I/O |

### 3.4 Connection Pooling (PgBouncer)
- Use **transaction pooling** for short-lived API queries.
- `default_pool_size: 20`, `max_client_conn: 1000`.
- Reduces PostgreSQL backend process overhead.

### 3.5 Maintenance
- Daily: `ANALYZE` high-write tables.
- Weekly: `VACUUM ANALYZE`, reindex.
- Monitor bloat and index fragmentation.
- Use read replicas for read-heavy workloads.

---

## 4. API Optimization

### 4.1 Response Optimization
- **Pagination**: Enforce max page size (100); use cursor-based for large datasets.
- **Field filtering**: Support `?fields=id,name,status` to reduce payload.
- **Compression**: Enable brotli (preferred) or gzip.
- **ETags**: Return `ETag`; honor `If-None-Match` for 304 responses.
- **Partial responses**: Support `206 Partial Content` for large downloads.

### 4.2 Request Optimization
- **Batching**: Provide batch endpoints to reduce round trips.
- **Idempotency**: Support `Idempotency-Key` header for safe retries.
- **Rate limiting**: Return `429` with `Retry-After`; use token bucket.
- **Validation**: Fail fast on invalid input; return structured errors.

### 4.3 Transport
- **HTTP/2 or HTTP/3**: Enable multiplexing and header compression.
- **Keep-alive**: Reuse connections; set `keep_alive_timeout: 65s`.
- **TLS session resumption**: Reduce handshake overhead.

### 4.4 Framework Tuning (Fastify)
- `keepAliveTimeout: 65000`, `connectionTimeout: 30000`
- `trustProxy: true` for correct client IP behind ingress
- Register `@fastify/compress` with brotli support
- Register `@fastify/rate-limit` with API key-based key generator
- Graceful shutdown: close DB pool, Redis, queue on `SIGTERM`

### 4.5 Monitoring
- Track p50/p95/p99 latency per endpoint.
- Alert on error rate > 0.1% or p99 > SLO.
- Log slow requests with query plans.

---

## 5. Frontend Optimization

### 5.1 Bundle Optimization
- **Code splitting**: Route-based and component-based lazy loading.
- **Tree shaking**: Remove dead code; use ES modules.
- **Minification**: Minify JS/CSS; source maps only in dev.
- **Dependency audit**: Remove unused libraries; prefer lightweight alternatives.
- **Bundle analysis**: Use `webpack-bundle-analyzer` or `source-map-explorer`.

### 5.2 Rendering Performance
- **Virtualization**: Use virtual lists (react-window, TanStack Virtual) for large lists.
- **Memoization**: `React.memo`, `useMemo`, `useCallback` judiciously.
- **Avoid unnecessary renders**: Lift state down; use context selectors.
- **Concurrent features**: `useTransition` and `useDeferredValue` for non-urgent updates.

### 5.3 Asset Optimization
- **Images**: WebP/AVIF; responsive `srcset`; lazy-load below-fold.
- **Fonts**: `font-display: swap`; subset fonts; preload critical fonts.
- **Static assets**: CDN with long cache headers + content hash filenames.
- **Preload/prefetch**: Preload critical resources; prefetch likely next routes.

### 5.4 Network Optimization
- **Service workers**: Cache static assets; stale-while-revalidate.
- **Prefetching**: Prefetch data for likely next navigation.
- **Debounce/throttle**: Debounce search inputs; throttle scroll/resize.
- **Optimistic UI**: Update UI immediately; reconcile on server response.

### 5.5 Core Web Vitals
- **LCP** < 2.5s: Optimize hero images and server response.
- **FID** < 100ms: Minimize main-thread work; use web workers.
- **CLS** < 0.1: Reserve space for dynamic content.

### 5.6 Monitoring
- Use `web-vitals` library for production CWV reporting.
- Set up Real User Monitoring (RUM) for regression detection.
- Run Lighthouse CI on every PR; fail on budget violations.

---

## Quick Reference Checklist

- [ ] Profile and set SLOs before optimizing
- [ ] Enable compression (brotli/gzip) at all layers
- [ ] Implement multi-layer caching with TTL + invalidation
- [ ] Index all query columns; monitor slow queries
- [ ] Use PgBouncer with transaction pooling
- [ ] Use connection pooling and short transactions
- [ ] Paginate all list endpoints; enforce max page size
- [ ] Code-split and lazy-load frontend routes
- [ ] Optimize images (WebP, responsive, lazy-load)
- [ ] Set performance budgets in CI
- [ ] Monitor p95/p99 latency and Core Web Vitals
