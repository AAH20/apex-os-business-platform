# Observability Guide — APEX-OS Business Platform

## 1. Metrics Strategy

### 1.1 Metric Types

| Type | Purpose | Examples |
|------|---------|----------|
| **Counter** | Monotonically increasing values | requests_total, errors_total, orders_created |
| **Gauge** | Point-in-time values that can go up or down | active_sessions, queue_depth, memory_usage_bytes |
| **Histogram** | Distribution of observed values | request_duration_seconds, response_size_bytes |
| **Summary** | Client-side aggregated quantiles | p99 latency per service instance |

### 1.2 Golden Signals (per service)

- **Latency**: p50/p95/p99 request duration (histogram)
- **Traffic**: requests per second by route and status code
- **Errors**: error rate as percentage of total requests (counter)
- **Saturation**: CPU, memory, disk, connection pool utilization (gauge)

### 1.3 RED Method (per endpoint)

- **R**ate: requests/sec
- **E**rrors: error count/sec
- **D**uration: latency percentiles

### 1.4 USE Method (per resource)

- **U**tilization: % of capacity used
- **S**aturation: queue length or wait time
- **E**rrors: error count for the resource

### 1.5 Labeling Conventions

- Use consistent label names: `service`, `route`, `status_code`, `method`, `environment`
- Keep cardinality low: no user IDs, no timestamps, no unbounded values in labels
- Target: < 100 label combinations per metric

### 1.6 Retention

- Raw metrics: 15 days at 15s resolution
- Downsampled (1m): 90 days
- Downsampled (1h): 1 year

---

## 2. Logging Strategy

### 2.1 Log Levels

| Level | Usage |
|-------|-------|
| **ERROR** | Immediate action required; data loss or outage |
| **WARN** | Degraded behavior; potential issue; retryable failures |
| **INFO** | Key business events; request lifecycle milestones |
| **DEBUG** | Detailed diagnostics; enabled per-service in staging only |

### 2.2 Structured Logging Format

All logs MUST be JSON with these required fields:

```json
{
  "timestamp": "2026-10-02T12:00:00.000Z",
  "level": "INFO",
  "service": "order-service",
  "trace_id": "abc123",
  "span_id": "def456",
  "message": "Order created successfully",
  "user_id": "u_789",
  "order_id": "ord_456",
  "duration_ms": 142
}
```

### 2.3 Log Field Standards

- `timestamp`: ISO 8601 UTC
- `level`: one of ERROR/WARN/INFO/DEBUG
- `service`: service name (kebab-case)
- `trace_id`: distributed trace identifier
- `span_id`: span within the trace
- `message`: human-readable description
- Additional fields: snake_case, no PII unless explicitly allowed

### 2.4 What to Log

**Always log:**
- Service startup/shutdown
- Inbound requests (method, route, status, duration)
- Outbound calls to dependencies (target, duration, status)
- Errors with stack traces (ERROR level)
- State transitions (order status, payment status)

**Never log:**
- Passwords, tokens, API keys, session secrets
- Full credit card numbers or CVV
- Unredacted PII (use field-level encryption or tokenization)
- Request/response bodies containing sensitive data

### 2.5 Log Sampling

- ERROR and WARN: 100% sampled
- INFO: 10% sampled in production (configurable per service)
- DEBUG: 0% in production; 100% in staging

### 2.6 Log Shipping

- Services write to stdout/stderr (12-factor)
- Container runtime or sidecar ships to centralized store
- Buffer locally on disk if upstream is unavailable (max 100MB, FIFO)

---

## 3. Tracing Strategy

### 3.1 Trace Context Propagation

- Use W3C Trace Context (`traceparent`, `tracestate` headers)
- Propagate across all service boundaries: HTTP, gRPC, message queues
- Inject into async jobs and scheduled tasks

### 3.2 Span Conventions

| Span Kind | When to Create |
|-----------|----------------|
| **SERVER** | Incoming request received |
| **CLIENT** | Outgoing call to another service |
| **PRODUCER** | Message published to queue |
| **CONSUMER** | Message consumed from queue |
| **INTERNAL** | Significant internal operation (DB transaction, cache operation) |

### 3.3 Span Attributes (OpenTelemetry semantic conventions)

- `http.method`, `http.route`, `http.status_code`
- `rpc.service`, `rpc.method`, `rpc.grpc_status_code`
- `db.system`, `db.operation`, `db.name`
- `messaging.system`, `messaging.destination`
- `service.name`, `service.version`, `deployment.environment`

### 3.4 Sampling

- **Head-based sampling**: 10% in production, 100% in staging
- **Tail-based sampling**: 100% of errors and slow requests (>p99)
- Always sample if `X-B3-Sampled: true` or `traceflags: 1` is set

### 3.5 Trace Retention

- Raw traces: 7 days
- Error traces: 30 days
- Sampled traces: 14 days

### 3.6 Critical Paths to Trace

1. User authentication flow
2. Order creation → payment → fulfillment
3. Webhook delivery and retry
4. Report generation (async jobs)
5. Data import/export pipelines

---

## 4. Alerting Strategy

### 4.1 Alert Severity Levels

| Severity | Response Time | Notification Channel | Example |
|----------|---------------|---------------------|---------|
| **P1 — Critical** | 5 minutes | Phone call + SMS + Slack | Complete service outage, data loss |
| **P2 — High** | 15 minutes | SMS + Slack | Elevated error rate, latency degradation |
| **P3 — Medium** | 1 hour | Slack | Resource saturation, non-critical failures |
| **P4 — Low** | Next business day | Email | Capacity warnings, minor anomalies |

### 4.2 Core Alerts

#### Availability
- **Service Down**: Health check fails for > 1 minute
- **Error Rate Spike**: 5xx rate > 5% for 5 minutes (P2)
- **Error Rate Critical**: 5xx rate > 20% for 2 minutes (P1)

#### Latency
- **p99 Latency**: p99 > 2s for 5 minutes (P2)
- **p99 Latency Critical**: p99 > 5s for 2 minutes (P1)

#### Saturation
- **CPU**: > 80% for 10 minutes (P3)
- **Memory**: > 85% for 10 minutes (P3)
- **Disk**: > 80% (P3), > 90% (P2)
- **Connection Pool**: > 80% utilization for 5 minutes (P2)

#### Business Metrics
- **Order Failure Rate**: > 2% for 10 minutes (P2)
- **Payment Failure Rate**: > 5% for 5 minutes (P1)
- **Queue Backlog**: > 1000 messages for 10 minutes (P2)

### 4.3 Alert Best Practices

- Alert on symptoms, not causes (user impact, not internal metrics)
- Every alert must have a runbook link
- Use multi-window, multi-burn-rate alerts to reduce flapping
- Set `for` duration to avoid transient spikes
- Group related alerts to prevent alert fatigue
- Silence maintenance windows in advance

### 4.4 Escalation Policy

1. Primary on-call receives alert
2. If unacknowledged in 5 min (P1) / 15 min (P2), escalate to secondary
3. If unacknowledged in 15 min (P1) / 30 min (P2), escalate to engineering manager
4. Post-incident: blameless review within 48 hours

---

## 5. Dashboard Strategy

### 5.1 Dashboard Hierarchy

| Dashboard | Audience | Refresh | Scope |
|-----------|----------|---------|-------|
| **Executive** | Leadership | 1h | Business KPIs, SLA compliance |
| **Service Overview** | All engineers | 30s | Per-service health at a glance |
| **Service Detail** | Service owners | 10s | Deep dive into one service |
| **Infrastructure** | Platform/SRE | 30s | Nodes, containers, networks |
| **Business** | Product/ops | 5m | Orders, revenue, user activity |

### 5.2 Executive Dashboard

- Monthly active users (trend)
- Order volume and revenue (daily/weekly/monthly)
- SLA compliance: uptime %, p99 latency, error rate
- Top 5 incidents this month
- Cost per transaction trend

### 5.3 Service Overview Dashboard

Per-service row showing:
- Request rate (req/s)
- Error rate (%)
- p50 / p95 / p99 latency
- CPU / memory utilization
- Pod/container count (desired vs. ready)
- Status indicator (green/yellow/red)

### 5.4 Service Detail Dashboard

- **Request volume** by route and status code (time series)
- **Latency heatmap** by route
- **Error breakdown** by type and route
- **Dependency map** with latency and error rates
- **Resource utilization**: CPU, memory, network I/O, disk I/O
- **Log stream** (recent ERROR/WARN entries)
- **Trace explorer** (recent slow/error traces)

### 5.5 Infrastructure Dashboard

- Cluster node count and health
- Pod restart count and OOM events
- Network throughput and errors
- Disk I/O and capacity
- Database connections, replication lag, slow queries
- Cache hit ratio and eviction rate
- Message queue depth and consumer lag

### 5.6 Business Dashboard

- Orders created / completed / cancelled (hourly)
- Payment success / failure rate
- Average order value
- User signups and active sessions
- Feature flag adoption rates
- Webhook delivery success rate

### 5.7 Dashboard Best Practices

- Every dashboard has an owner and a description
- Use consistent color coding: green = healthy, yellow = warning, red = critical
- Include time range selector (default: last 1 hour)
- Add annotations for deployments and incidents
- Avoid vanity metrics; every panel should answer a question
- Review and prune unused dashboards quarterly
- Export dashboard definitions as code (GitOps)

---

## Appendix: Tooling Reference

| Concern | Tool |
|---------|------|
| Metrics collection | Prometheus / VictoriaMetrics |
| Log aggregation | Loki / Elasticsearch |
| Tracing | Jaeger / Tempo |
| Alerting | Alertmanager / Grafana Alerting |
| Dashboards | Grafana |
| APM | OpenTelemetry Collector |
| Synthetic checks | Blackbox exporter / external probe |
| Incident management | PagerDuty / Opsgenie |
