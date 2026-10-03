# New Projects Monitoring

## 1. Metrics Collection

### 1.1 Infrastructure Metrics
- **CPU / Memory / Disk / Network** — collected via node_exporter (host-level) and cAdvisor (container-level).
- **Retention**: 15s resolution for 7 days, 1m resolution for 90 days.
- **Labels**: `env`, `service`, `instance`, `region`.

### 1.2 Application Metrics
- **Request rate** — `http_requests_total` (counter, per route/method/status).
- **Latency** — `http_request_duration_seconds` (histogram, p50/p95/p99).
- **Error rate** — `http_errors_total` (counter, per status code class).
- **Throughput** — bytes in/out per endpoint.
- **Queue depth** — pending jobs per worker pool.
- **DB connections** — active/idle/waiting per pool.
- **Cache hit ratio** — hits / (hits + misses) per cache tier.

### 1.3 Business Metrics
- **Active projects** — count of projects in `active` state.
- **New project creation rate** — projects created per hour.
- **Onboarding completion** — % of new projects reaching "first deploy" within 24h.
- **User signups** — new accounts per day.
- **Feature adoption** — usage counts per core feature flag.

### 1.4 Collection Stack
- **Prometheus** — scrape targets every 15s; remote-write to long-term storage.
- **OpenTelemetry SDK** — embedded in all services; exports to OTel Collector.
- **StatsD** — legacy fallback for non-instrumented services.

---

## 2. Alerting Rules

### 2.1 Severity Levels
| Level | Description | Response SLA |
|-------|-------------|--------------|
| P1 | Service down / data loss | 5 min |
| P2 | Degraded performance / elevated errors | 15 min |
| P3 | Non-critical anomaly | 1 hour |
| P4 | Informational / capacity warning | Next business day |

### 2.2 Alert Rules (Prometheus / Alertmanager)

```yaml
groups:
  - name: new-projects-service
    rules:
      # P1 — Service down
      - alert: NewProjectsDown
        expr: up{job="new-projects"} == 0
        for: 1m
        labels: { severity: P1 }
        annotations:
          summary: "New Projects service is down"

      # P1 — High error rate
      - alert: HighErrorRate
        expr: |
          sum(rate(http_errors_total[5m])) / sum(rate(http_requests_total[5m])) > 0.05
        for: 2m
        labels: { severity: P1 }
        annotations:
          summary: "Error rate above 5%"

      # P2 — Latency degradation
      - alert: HighLatency
        expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 2.0
        for: 5m
        labels: { severity: P2 }
        annotations:
          summary: "p99 latency above 2s"

      # P2 — DB connection pool exhaustion
      - alert: DBPoolExhausted
        expr: db_connections_active / db_connections_max > 0.85
        for: 3m
        labels: { severity: P2 }
        annotations:
          summary: "DB connection pool > 85% utilized"

      # P2 — Queue backlog
      - alert: QueueBacklog
        expr: queue_depth > 1000
        for: 5m
        labels: { severity: P2 }
        annotations:
          summary: "Job queue backlog exceeds 1000"

      # P3 — Disk space warning
      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.15
        for: 10m
        labels: { severity: P3 }
        annotations:
          summary: "Disk space below 15%"

      # P3 — Certificate expiry
      - alert: CertExpiringSoon
        expr: cert_expiry_days < 14
        for: 1h
        labels: { severity: P3 }
        annotations:
          summary: "TLS certificate expires in < 14 days"

      # P4 — Unusual signup drop
      - alert: SignupDrop
        expr: |
          rate(user_signups_total[1h]) < 0.5 * rate(user_signups_total[1h] offset 1d)
        for: 30m
        labels: { severity: P4 }
        annotations:
          summary: "Signup rate dropped > 50% vs yesterday"
```

### 2.3 Notification Routing
- **P1/P2** → PagerDuty → on-call engineer + Slack `#alerts-critical`.
- **P3** → Slack `#alerts-warning`.
- **P4** → Slack `#alerts-info` (no page).
- **Escalation**: unacknowledged P1 escalates to team lead after 10 min.

---

## 3. Dashboard Design

### 3.1 Dashboard Stack
- **Grafana** — primary visualization; provisioned via JSON in `monitoring/dashboards/`.
- **Refresh**: 10s (real-time), 1m (overview), 5m (capacity).

### 3.2 Dashboard Hierarchy

#### 3.2.1 Executive Overview
- Active projects (gauge).
- New projects created / 24h (stat).
- Signups / 24h (stat).
- Overall service health (green/yellow/red).
- Monthly recurring revenue (stat).

#### 3.2.2 Service Health (per service)
- Request rate (time series, by route).
- Error rate % (time series, by status class).
- p50/p95/p99 latency (time series).
- Saturation: CPU, memory, DB connections, queue depth.
- Apdex score (time series).

#### 3.2.3 New Projects Pipeline
- Projects created per hour (bar).
- Onboarding funnel: signup → project created → first deploy → active.
- Time-to-first-deploy distribution (histogram).
- Abandoned onboarding count.

#### 3.2.4 Infrastructure
- Node CPU/memory/disk/network (grid of time series).
- Container resource usage (per pod).
- DB: connections, slow queries, replication lag.
- Cache: hit ratio, evictions, memory.

#### 3.2.5 Capacity & Forecasting
- Resource utilization trends (7d / 30d).
- Projected disk growth (linear regression).
- Projected DB connection growth.
- Cost per active project.

### 3.3 Panel Conventions
- **Red threshold lines** on all latency/error panels.
- **Annotations** for deploys (via Grafana annotation API).
- **Variables**: `$env`, `$service`, `$region` for multi-tenant filtering.
- **Links**: each panel links to corresponding logs (Loki) and traces (Tempo).

---

## 4. Log Aggregation

### 4.1 Architecture
```
App → Fluent Bit (DaemonSet) → Kafka → Logstash → Elasticsearch
                                         ↓
                                    Loki (query)
```

### 4.2 Log Format
- **Structured JSON** — all services emit JSON logs.
- **Required fields**:
  ```json
  {
    "timestamp": "2026-10-02T12:00:00.000Z",
    "level": "info|warn|error|debug",
    "service": "new-projects-api",
    "trace_id": "abc123",
    "span_id": "def456",
    "request_id": "req-789",
    "user_id": "u-456",
    "project_id": "p-789",
    "message": "Project created",
    "duration_ms": 42,
    "env": "production"
  }
  ```

### 4.3 Retention & Tiering
| Tier | Storage | Retention | Use Case |
|------|---------|-----------|----------|
| Hot | Elasticsearch (SSD) | 7 days | Real-time search, dashboards |
| Warm | Elasticsearch (HDD) | 30 days | Incident investigation |
| Cold | S3 (Parquet) | 1 year | Compliance, audit |
| Archive | S3 Glacier | 7 years | Legal hold |

### 4.4 Log Pipelines
- **Fluent Bit** — tail container logs, parse JSON, enrich with Kubernetes metadata.
- **Kafka** — buffer layer; decouples producers from consumers.
- **Logstash** — transform, route, drop PII fields.
- **Elasticsearch** — indexed by `service`, `level`, `trace_id`, `project_id`.
- **Loki** — lightweight alternative for label-based log queries.

### 4.5 Key Queries (Loki LogQL)
```logql
# Errors for a specific project
{service="new-projects-api"} |= "project_id=p-789" | json | level="error"

# Slow requests
{service="new-projects-api"} | json | duration_ms > 1000

# Full request trace
{service="new-projects-api"} |= "trace_id=abc123"
```

### 4.6 PII Handling
- **Redact at source** — services never log raw PII.
- **Logstash filter** — regex-based redaction for legacy services.
- **Field-level encryption** — sensitive fields encrypted before indexing.
- **Access control** — RBAC on Elasticsearch indices; audit log for all queries.

---

## 5. Tracing

### 5.1 Architecture
```
App (OTel SDK) → OTel Collector → Tempo (storage)
                                    ↓
                              Grafana (trace view)
```

### 5.2 Instrumentation
- **OpenTelemetry SDK** — auto-instrumentation for HTTP, gRPC, DB, cache, message queues.
- **Custom spans** — business operations: `project.create`, `project.deploy`, `user.onboard`.
- **Context propagation** — trace context via `traceparent` header across all service boundaries.
- **Sampling**:
  - **Head-based**: 10% for normal traffic, 100% for errors.
  - **Tail-based**: 100% for requests > 1s or containing errors.

### 5.3 Span Conventions
- **Span names**: `{service}.{operation}` (e.g., `new-projects.create-project`).
- **Required attributes**:
  - `service.name`, `service.version`
  - `deployment.environment`
  - `http.method`, `http.route`, `http.status_code`
  - `db.system`, `db.operation`, `db.statement` (sanitized)
  - `messaging.system`, `messaging.operation`
  - `project.id`, `user.id` (for business correlation)
- **Events**: log-style annotations within spans (e.g., `cache.miss`, `retry.attempt`).

### 5.4 Trace-Driven Workflows
- **Error triage** — click error span → see full trace → identify failing service → jump to logs.
- **Latency analysis** — flame graph per request; identify slowest span.
- **Dependency mapping** — service graph from trace data (via Grafana or Jaeger).
- **SLO tracking** — error budget burn rate from trace-derived SLIs.

### 5.5 Storage & Retention
- **Tempo** — object storage backend (S3); 14-day retention.
- **Trace-to-logs** — `trace_id` injected into all logs; bidirectional linking in Grafana.
- **Trace-to-metrics** — RED metrics (Rate, Errors, Duration) derived from spans.

### 5.6 Key Metrics from Traces
| Metric | Type | Description |
|--------|------|-------------|
| `traces_total` | Counter | Total spans sampled |
| `trace_duration_seconds` | Histogram | End-to-end request duration |
| `span_errors_total` | Counter | Spans with error status |
| `service_dependencies` | Gauge | Active service-to-service edges |

---

## Appendix: Tooling Summary

| Layer | Tool | Purpose |
|-------|------|---------|
| Metrics | Prometheus, node_exporter, cAdvisor | Collection & storage |
| Alerting | Alertmanager, PagerDuty | Routing & notification |
| Dashboards | Grafana | Visualization |
| Logs | Fluent Bit, Kafka, Elasticsearch, Loki | Aggregation & search |
| Traces | OpenTelemetry, Tempo | Distributed tracing |
| SLOs | Grafana SLO / Pyrra | Error budget tracking |
