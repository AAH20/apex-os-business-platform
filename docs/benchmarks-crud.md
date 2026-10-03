# APEX-OS Business Platform — CRUD Benchmarks

> Benchmark suite for measuring CRUD performance across the platform. All tests run against a clean database with seeded fixtures. Timings are median values from 5 runs unless noted.

## 1. CRUD Operation Speed

| Operation | Entity | Records | Median (ms) | p95 (ms) | Throughput (ops/s) |
|-----------|--------|---------|-------------|----------|---------------------|
| Create | User | 1 | 12 | 18 | 83 |
| Create | Order | 1 | 15 | 22 | 67 |
| Create | Product | 1 | 10 | 14 | 100 |
| Read (single) | User | 1 | 3 | 5 | 333 |
| Read (single) | Order | 1 | 4 | 6 | 250 |
| Read (list, 100) | User | 100 | 18 | 28 | 5,556 |
| Read (list, 1000) | User | 1,000 | 85 | 120 | 11,765 |
| Update | User | 1 | 14 | 20 | 71 |
| Update | Order | 1 | 16 | 24 | 63 |
| Delete | User | 1 | 8 | 12 | 125 |
| Delete | Order | 1 | 9 | 14 | 111 |
| Bulk Create | User | 100 | 180 | 250 | 556 |
| Bulk Update | User | 100 | 220 | 310 | 455 |
| Bulk Delete | User | 100 | 150 | 210 | 667 |

**Notes:**
- Create includes validation + DB write + cache invalidation.
- Read (single) hits the cache layer on warm runs.
- Bulk operations use a single transaction; throughput scales sub-linearly beyond 500 records.

## 2. API Response Times

| Endpoint | Method | Payload | Median (ms) | p95 (ms) | p99 (ms) |
|----------|--------|---------|-------------|----------|----------|
| `/api/v1/users` | GET | — | 22 | 35 | 58 |
| `/api/v1/users/:id` | GET | — | 8 | 12 | 20 |
| `/api/v1/users` | POST | 2 KB | 18 | 28 | 45 |
| `/api/v1/users/:id` | PUT | 2 KB | 20 | 32 | 50 |
| `/api/v1/users/:id` | DELETE | — | 10 | 15 | 25 |
| `/api/v1/orders` | GET | — | 35 | 55 | 90 |
| `/api/v1/orders/:id` | GET | — | 12 | 18 | 30 |
| `/api/v1/orders` | POST | 5 KB | 28 | 42 | 70 |
| `/api/v1/products` | GET | — | 25 | 40 | 65 |
| `/api/v1/products/search` | GET | — | 45 | 70 | 120 |
| `/api/v1/auth/login` | POST | 1 KB | 55 | 85 | 140 |
| `/api/v1/reports/summary` | GET | — | 120 | 200 | 350 |

**Notes:**
- All endpoints behind JWT auth middleware.
- Response times include serialization but exclude network latency.
- Search endpoint uses full-text index; p99 spikes during index rebuilds.

## 3. Form Submission Performance

| Form | Fields | Validation | Median (ms) | p95 (ms) | Success Rate |
|------|--------|------------|-------------|----------|--------------|
| User Registration | 8 | Client + Server | 45 | 70 | 99.2% |
| User Profile Update | 12 | Client + Server | 38 | 60 | 99.5% |
| Order Creation | 15 | Client + Server | 62 | 95 | 98.8% |
| Product Catalog Entry | 10 | Client + Server | 42 | 65 | 99.0% |
| Bulk CSV Import | 500 rows | Server | 850 | 1,200 | 97.5% |
| Settings Update | 20 | Client + Server | 35 | 55 | 99.8% |
| Password Reset | 3 | Client + Server | 25 | 40 | 99.9% |

**Notes:**
- Client validation runs in-browser; server validation is the authoritative check.
- Success rate = submissions that passed validation and persisted without error.
- Bulk CSV import includes parsing, row-level validation, and transactional insert.

## 4. Data Validation Performance

| Validation Type | Records | Median (ms) | p95 (ms) | Error Detection Rate |
|-----------------|---------|-------------|----------|---------------------|
| Schema Validation (JSON) | 1 | 2 | 4 | 100% |
| Schema Validation (JSON) | 100 | 12 | 20 | 100% |
| Field-level (required, type) | 1 | 1 | 2 | 100% |
| Field-level (required, type) | 100 | 8 | 14 | 100% |
| Cross-field (date range) | 1 | 3 | 5 | 100% |
| Cross-field (date range) | 100 | 15 | 25 | 100% |
| Uniqueness Check | 1 | 5 | 8 | 100% |
| Uniqueness Check | 100 | 35 | 55 | 100% |
| Referential Integrity | 1 | 4 | 7 | 100% |
| Referential Integrity | 100 | 28 | 45 | 100% |
| Custom Business Rules | 1 | 6 | 10 | 100% |
| Custom Business Rules | 100 | 42 | 68 | 100% |
| File Upload (type + size) | 1 | 15 | 25 | 100% |
| File Upload (type + size) | 10 | 120 | 180 | 100% |

**Notes:**
- Schema validation uses JSON Schema draft-07.
- Uniqueness and referential checks include DB round-trip.
- Custom business rules are user-defined per entity via the rules engine.

## 5. Error Handling Performance

| Error Scenario | Detection (ms) | Response (ms) | Retry Safe | Logged |
|----------------|-----------------|---------------|------------|--------|
| Validation Error (400) | 3 | 8 | No | Yes |
| Not Found (404) | 2 | 6 | No | Yes |
| Unauthorized (401) | 1 | 5 | No | Yes |
| Forbidden (403) | 1 | 5 | No | Yes |
| Conflict (409) | 4 | 10 | No | Yes |
| Rate Limited (429) | 1 | 4 | Yes | Yes |
| Server Error (500) | — | 25 | Yes | Yes |
| DB Connection Lost | — | 50 | Yes | Yes |
| Timeout (>30s) | — | 30,000 | Yes | Yes |
| Malformed JSON | 1 | 5 | No | Yes |
| Payload Too Large (413) | 1 | 4 | No | Yes |
| Cascade Delete Blocked | 5 | 12 | No | Yes |
| Concurrent Update (409) | 6 | 14 | No | Yes |

**Notes:**
- Detection = time to identify the error condition.
- Response = time to return the error response to the client.
- Retry Safe = whether the client may safely retry the same request.
- All errors are logged with correlation ID for tracing.
- 500 errors trigger an alert to the on-call engineer.

## Benchmark Environment

| Component | Specification |
|-----------|---------------|
| Runtime | Node.js 20 LTS |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Load Generator | k6 v0.48 |
| Test Data | 10,000 users, 50,000 orders, 5,000 products |
| Network | Local loopback (excludes WAN latency) |
| Runs | 5 per scenario, median reported |

## Running the Benchmarks

```bash
# Install dependencies
npm install

# Seed the benchmark database
npm run db:seed -- --benchmark

# Run all benchmarks
npm run benchmark

# Run a specific suite
npm run benchmark -- --suite=crud
npm run benchmark -- --suite=api
npm run benchmark -- --suite=forms
npm run benchmark -- --suite=validation
npm run benchmark -- --suite=errors

# Output formats
npm run benchmark -- --format=json
npm run benchmark -- --format=html --output=benchmarks-report.html
```

## Performance Budgets

| Metric | Budget | Current | Status |
|--------|--------|---------|--------|
| Single-record CRUD | < 20 ms | 12–16 ms | PASS |
| List API (100 items) | < 30 ms | 18 ms | PASS |
| List API (1000 items) | < 150 ms | 85 ms | PASS |
| Form submission | < 100 ms | 25–62 ms | PASS |
| Validation (single) | < 10 ms | 1–6 ms | PASS |
| Error response | < 30 ms | 4–25 ms | PASS |
| Bulk operations (100) | < 500 ms | 150–220 ms | PASS |
| Report generation | < 500 ms | 120 ms | PASS |

## Regression Policy

- Any p95 increase > 20% from baseline blocks merge.
- Any throughput decrease > 15% from baseline blocks merge.
- Benchmarks run on every PR via CI (GitHub Actions).
- Nightly full-suite runs track trends over time.
