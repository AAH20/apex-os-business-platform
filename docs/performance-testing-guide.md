# Performance Testing Guide

## 1. Performance Testing Strategy

### Objectives
- Validate system behavior under expected and peak workloads
- Establish performance baselines for regression detection
- Identify bottlenecks before they impact users
- Ensure SLAs and SLOs are met consistently

### Scope
- **APIs**: REST endpoints, GraphQL resolvers, WebSocket connections
- **Frontend**: Page load, time to interactive, rendering performance
- **Database**: Query latency, connection pool utilization, lock contention
- **Infrastructure**: CPU, memory, network I/O, disk throughput
- **Third-party integrations**: Payment gateways, email services, external APIs

### Test Environment
- Mirror production topology (same instance types, scaling rules, caching layers)
- Use production-like data volumes (anonymized snapshots)
- Isolate from production to avoid user impact
- Run in CI on every release candidate; full suite nightly

### Key Metrics
| Metric | Description |
|--------|-------------|
| Latency (p50, p95, p99) | Response time percentiles |
| Throughput | Requests per second (RPS) |
| Error rate | Percentage of failed requests |
| Resource utilization | CPU, memory, disk, network |
| Concurrent users | Simultaneous active sessions |

### Tools
- **k6**: Scriptable load tests in JavaScript/TypeScript
- **Artillery**: YAML-based scenario testing
- **Lighthouse CI**: Frontend performance budgets
- **Prometheus + Grafana**: Metrics collection and visualization
- **Jaeger**: Distributed tracing for bottleneck analysis

### CI Integration
- Run smoke tests on every PR (single VU, 30s)
- Run full load suite on merge to main
- Run stress and endurance tests on release candidates
- Fail builds that exceed performance budgets

---

## 2. Load Testing

### Purpose
Verify the system performs within defined budgets under expected traffic patterns.

### Test Scenarios

#### Baseline Load
- Single virtual user (VU) hitting each endpoint
- Establishes single-request latency floor
- Run for 5 minutes to warm caches

#### Expected Load
- Simulate normal production traffic (e.g., 100 concurrent users)
- Ramp up over 2 minutes, sustain for 10 minutes
- Validate p95 latency and error rate stay within budget

#### Peak Load
- Simulate known peak events (e.g., 500 concurrent users)
- Ramp up over 5 minutes, sustain for 15 minutes
- Validate auto-scaling triggers correctly
- Confirm no cascading failures

#### Traffic Patterns
- **Steady**: Constant RPS over time
- **Ramp**: Gradual increase to target load
- **Wave**: Sinusoidal variation to simulate daily cycles
- **Burst**: Sudden spike followed by sustained load

### Load Test Structure (k6 example)
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up
    { duration: '10m', target: 100 },  // Sustained
    { duration: '2m', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],   // 95% under 500ms
    http_req_failed: ['rate<0.01'],     // Error rate under 1%
  },
};

export default function () {
  const res = http.get('https://api.example.com/health');
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(1);
}
```

### Pass Criteria
- p95 latency within budget for all endpoints
- Error rate below 0.1%
- No memory leaks (stable heap usage)
- Auto-scaling responds within 2 minutes

---

## 3. Stress Testing

### Purpose
Find the breaking point and validate graceful degradation under extreme load.

### Test Scenarios

#### Breaking Point Discovery
- Start at 2x expected peak load
- Increase by 50% every 5 minutes until failure
- Record the maximum sustainable RPS
- Document failure modes (timeouts, 503s, OOM)

#### Spike Testing
- Instant jump from 0 to 10x expected load
- Hold for 2 minutes, then drop to normal
- Validate recovery time and error handling
- Ensure circuit breakers activate correctly

#### Soak Spike
- Sustained 3x load for 30 minutes
- Monitor for resource exhaustion
- Validate connection pool recovery

#### Degradation Validation
- Disable one service instance during peak load
- Confirm traffic reroutes without user impact
- Validate health checks and failover

### Stress Test Configuration
```javascript
export const options = {
  stages: [
    { duration: '5m', target: 1000 },   // 2x peak
    { duration: '5m', target: 1500 },   // 3x peak
    { duration: '5m', target: 2000 },   // 4x peak
    { duration: '5m', target: 2500 },   // 5x peak
    { duration: '10m', target: 0 },     // Recovery
  ],
};
```

### Pass Criteria
- System degrades gracefully (no crashes)
- Error rate increases proportionally with load
- Recovery completes within 5 minutes after load stops
- No data corruption or inconsistency

---

## 4. Endurance Testing

### Purpose
Detect memory leaks, connection pool exhaustion, and performance degradation over time.

### Test Scenarios

#### Standard Soak
- Run at 70% of expected peak load for 8 hours
- Monitor memory, connections, file descriptors
- Validate latency remains stable throughout

#### Extended Soak
- Run at 50% of expected peak load for 24-48 hours
- Detect slow memory leaks
- Validate log rotation and disk usage

#### Connection Pool Exhaustion
- Simulate connection leaks by holding connections open
- Validate pool timeout and recovery
- Confirm no permanent connection loss

#### Cache Degradation
- Run with cache hit rate artificially lowered
- Validate database can handle increased load
- Confirm cache warms up correctly after flush

### Monitoring During Soak
- Heap usage trend (should plateau, not grow unboundedly)
- Database connection count (should stabilize)
- Response time variance (should not increase)
- Garbage collection frequency and duration

### Pass Criteria
- Memory usage stable (±10% variance) after warmup
- No connection pool exhaustion
- p95 latency does not degrade more than 20% over test duration
- No disk space or file descriptor leaks

---

## 5. Performance Budgets

### API Response Times
| Endpoint Type | p50 | p95 | p99 |
|---------------|-----|-----|-----|
| Health check | 10ms | 50ms | 100ms |
| Authentication | 100ms | 250ms | 500ms |
| CRUD operations | 150ms | 400ms | 800ms |
| Search/query | 200ms | 500ms | 1000ms |
| Report generation | 500ms | 2000ms | 5000ms |
| File upload | 1000ms | 3000ms | 10000ms |

### Frontend Budgets
| Metric | Budget |
|--------|--------|
| First Contentful Paint (FCP) | < 1.0s |
| Largest Contentful Paint (LCP) | < 2.5s |
| Time to Interactive (TTI) | < 3.5s |
| Cumulative Layout Shift (CLS) | < 0.1 |
| Total page weight | < 2MB |
| JavaScript bundle size | < 500KB (gzipped) |

### Throughput Budgets
| Tier | Concurrent Users | RPS |
|------|-----------------|-----|
| Small | 100 | 500 |
| Medium | 500 | 2500 |
| Large | 1000 | 5000 |
| Enterprise | 5000 | 25000 |

### Error Rate Budgets
| Severity | Threshold |
|----------|-----------|
| Client errors (4xx) | < 1% |
| Server errors (5xx) | < 0.1% |
| Timeouts | < 0.5% |
| Total error rate | < 1% |

### Resource Utilization Budgets
| Resource | Warning | Critical |
|----------|---------|----------|
| CPU | 70% | 85% |
| Memory | 75% | 90% |
| Disk I/O | 70% | 85% |
| Network bandwidth | 60% | 80% |
| DB connections | 70% | 90% |

### Budget Enforcement
- **CI gates**: Fail builds exceeding p95 latency budgets
- **Alerting**: Page on-call when warning thresholds breached
- **Dashboards**: Real-time visibility into all budget metrics
- **Reviews**: Quarterly budget review based on production data

---

## Quick Reference

| Test Type | Frequency | Duration | Load Level |
|-----------|-----------|----------|------------|
| Smoke | Every PR | 30s | 1 VU |
| Load | Every merge | 15m | Expected |
| Stress | Release candidate | 30m | 2-5x peak |
| Endurance | Weekly | 8-24h | 70% peak |
| Spike | Monthly | 10m | 10x peak |
