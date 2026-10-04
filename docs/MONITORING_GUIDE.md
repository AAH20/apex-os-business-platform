# APEX-OS Business Platform — Monitoring Guide

## 1. Metrics to Collect

### 1.1 Golden Signals (per service)

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| Request rate | Counter | Requests/sec by route, method, status | `service`, `route`, `method`, `status` |
| Error rate | Counter | Failed requests (5xx, 4xx, exceptions) | `service`, `route`, `error_type` |
| Latency (p50/p95/p99) | Histogram | End-to-end request duration | `service`, `route`, `method` |
| Throughput | Counter | Bytes sent/received, records processed | `service`, `direction` |

### 1.2 Application Metrics

- **Queue depth**: pending jobs per queue (Celery, Sidekiq, etc.)
- **DB connections**: active/idle/waiting per pool
- **Cache hit ratio**: hits / (hits + misses) per cache cluster
- **Background job duration**: p50/p95/p99 per job type
- **Event lag**: consumer offset lag per topic/partition

### 1.3 Infrastructure Metrics

- CPU, memory, disk I/O, disk usage per node/container
- Network throughput and packet loss
- Container restarts and OOM kills
- Node/pod scheduling failures

### 1.4 Business Metrics (optional but recommended)

- Orders/minute, revenue/minute
- Active users, session count
- Payment success/failure rate
- Search query latency and zero-result rate

---

## 2. Logging Strategy

### 2.1 Structured Logging

All services MUST emit JSON logs to stdout. Never log to local files.

```json
{
  "timestamp": "2026-10-04T12:00:00.000Z",
  "level": "ERROR",
  "service": "orders-api",
  "trace_id": "abc123",
  "span_id": "def456",
  "message": "Failed to process order",
  "user_id": "u_789",
  "order_id": "ord_456",
  "duration_ms": 234,
  "error": "TimeoutError: DB connection timeout",
  "stack_trace": "..."
}
```

### 2.2 Log Levels

| Level | Usage |
|-------|-------|
| `DEBUG` | Verbose diagnostics; enabled only in dev/staging or via dynamic level toggle |
| `INFO` | Normal operational events (request completed, job started/finished) |
| `WARN` | Recoverable issues (retry attempted, deprecated API called, slow query) |
| `ERROR` | Operation failed; requires attention but not necessarily paging |
| `FATAL` | Unrecoverable; service is shutting down |

### 2.3 Log Aggregation

- **Pipeline**: App → Fluent Bit (DaemonSet) → Kafka → Logstash → Elasticsearch
- **Retention**: Hot 7 days, warm 30 days, cold 1 year (S3/GCS)
- **Sampling**: DEBUG logs sampled at 1% in production; ERROR+ always 100%
- **PII**: Scrub `email`, `phone`, `ssn`, `card_number` via Fluent Bit filter before ingestion

### 2.4 Log Correlation

Every log line MUST include `trace_id` and `span_id` (see Tracing section). Use the OpenTelemetry trace context propagator.

---

## 3. Tracing

### 3.1 Distributed Tracing Architecture

- **Instrument**: OpenTelemetry SDK in every service
- **Collector**: OpenTelemetry Collector (agent + gateway deployment)
- **Backend**: Jaeger for trace storage and UI
- **Sampling**: Head-based 10% in production; tail-based 100% for errors in staging

### 3.2 Span Creation

```python
# Python example
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process_order") as span:
    span.set_attribute("order.id", order_id)
    span.set_attribute("order.total", total)
    span.set_attribute("user.id", user_id)

    with tracer.start_as_current_span("validate_inventory"):
        validate_inventory(order)

    with tracer.start_as_current_span("charge_payment"):
        charge_payment(order)
```

### 3.3 Span Naming Conventions

- `{operation}` for top-level spans (e.g., `POST /orders`)
- `{entity}.{action}` for internal spans (e.g., `inventory.reserve`, `payment.charge`)
- `{external_service}.{operation}` for outbound calls (e.g., `stripe.create_charge`)

### 3.4 Standard Span Attributes

| Attribute | Description |
|-----------|-------------|
| `service.name` | Service identifier |
| `service.version` | Deployed version |
| `http.method` | HTTP method |
| `http.route` | Matched route |
| `http.status_code` | Response status |
| `db.system` | Database type (postgres, redis, etc.) |
| `db.statement` | Query (sanitized) |
| `messaging.system` | Message broker (kafka, rabbitmq) |
| `messaging.destination` | Topic/queue name |

### 3.5 Trace Context Propagation

- Use `traceparent` and `tracestate` headers (W3C Trace Context)
- Propagate across: HTTP, gRPC, message queues (inject into message headers)
- Baggage for tenant/customer ID (use sparingly — size limits)

---

## 4. Alerting

### 4.1 Alert Severity Levels

| Severity | Response Time | Channel | Example |
|----------|---------------|---------|---------|
| **P1 — Critical** | 5 min | Phone call + Slack #incidents | Full outage, data loss |
| **P2 — High** | 15 min | Slack #incidents + SMS | Degraded service, high error rate |
| **P3 — Medium** | 1 hour | Slack #alerts | Elevated latency, single AZ failure |
| **P4 — Low** | Next business day | Slack #alerts | Disk usage > 80%, cert expiry < 14 days |

### 4.2 Core Alert Rules

```yaml
# Prometheus alert examples
groups:
  - name: apex-os-critical
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
          / sum(rate(http_requests_total[5m])) by (service) > 0.05
        for: 2m
        labels:
          severity: P1
        annotations:
          summary: "High 5xx error rate on {{ $labels.service }}"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 2.0
        for: 5m
        labels:
          severity: P2
        annotations:
          summary: "p99 latency > 2s on {{ $labels.service }}"

      - alert: ServiceDown
        expr: up{job="apex-os-services"} == 0
        for: 1m
        labels:
          severity: P1
        annotations:
          summary: "{{ $labels.instance }} is down"

      - alert: DiskUsageHigh
        expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.15
        for: 10m
        labels:
          severity: P3
        annotations:
          summary: "Disk usage > 85% on {{ $labels.instance }}"
```

### 4.3 Alert Channels

- **Slack**: `#incidents` (P1/P2), `#alerts` (P3/P4)
- **PagerDuty**: P1 and P2 with escalation policies
- **Email**: Daily digest of P3/P4 alerts
- **Webhook**: Custom integrations (e.g., status page updates)

### 4.4 Escalation Policy

1. **Level 1**: On-call engineer (5 min ack timeout)
2. **Level 2**: Secondary on-call (10 min ack timeout)
3. **Level 3**: Engineering manager (15 min ack timeout)
4. **Level 4**: VP Engineering / CTO (30 min ack timeout)

### 4.5 Alert Hygiene

- Every alert MUST have a runbook link
- No alert without a clear action
- Review and tune thresholds monthly
- Silence windows for planned maintenance
- Group related alerts to prevent alert storms

---

## 5. Dashboards

### 5.1 Grafana Setup

- **Provisioning**: Dashboards as JSON in `monitoring/dashboards/` (GitOps)
- **Data sources**: Prometheus (metrics), Loki/Elasticsearch (logs), Jaeger (traces)
- **Refresh**: 15s for real-time, 1h for overview

### 5.2 Dashboard Hierarchy

| Dashboard | Audience | Contents |
|-----------|----------|----------|
| **Executive Overview** | Leadership | SLO status, revenue impact, active incidents |
| **Service Health** | SRE/On-call | Golden signals per service, dependency map |
| **Service Detail** | Service owners | Per-service metrics, logs, traces, deployments |
| **Infrastructure** | SRE | Node/pool/container metrics, capacity planning |
| **Business Metrics** | Product | Orders, users, conversion, feature usage |

### 5.3 Key Panels (Service Detail)

1. **Request rate** (req/s) — stacked by status code
2. **Error rate** (%) — with 5xx/4xx split
3. **Latency** — p50/p95/p99 lines
4. **Saturation** — CPU, memory, DB connections, queue depth
5. **Deployments** — annotation markers for releases
6. **Log volume** — errors/minute from Loki

### 5.4 Custom Dashboards

- Use Grafana variables (`$service`, `$environment`, `$time_range`)
- Export dashboards as JSON and version control them
- Use Grafana image renderer for scheduled PDF reports to Slack

---

## 6. Health Checks

### 6.1 Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 3

startupProbe:
  httpGet:
    path: /health/startup
    port: 8080
  failureThreshold: 30
  periodSeconds: 10
```

### 6.2 Health Check Endpoints

| Endpoint | Purpose | Checks |
|----------|---------|--------|
| `/health/live` | Liveness | Process is running, event loop not blocked |
| `/health/ready` | Readiness | DB reachable, cache reachable, migrations applied |
| `/health/startup` | Startup | All init tasks completed, config loaded |
| `/health/deep` | Deep health | All external dependencies, disk space, cert validity |

### 6.3 Health Check Best Practices

- Liveness MUST NOT check external dependencies (causes cascading restarts)
- Readiness SHOULD check dependencies but with short timeouts (1-2s)
- Deep health endpoint for load balancer pre-warming
- Return proper HTTP status: 200 (healthy), 503 (unhealthy)
- Include version, uptime, and dependency status in response body

---

## 7. SLOs and SLIs

### 7.1 Service Level Indicators (SLIs)

| SLI | Measurement | Target |
|-----|-------------|--------|
| **Availability** | Successful requests / total requests | 99.9% |
| **Latency (p99)** | Request duration < 500ms | 99% of requests |
| **Error rate** | 5xx responses / total responses | < 0.1% |
| **Throughput** | Orders processed per minute | > 1000/min |
| **Freshness** | Data replication lag | < 5 seconds |

### 7.2 Service Level Objectives (SLOs)

| Service | Availability SLO | Latency SLO | Error Budget |
|---------|-----------------|-------------|--------------|
| API Gateway | 99.95% | p99 < 200ms | 21.9 min/month |
| Orders Service | 99.9% | p99 < 500ms | 43.8 min/month |
| Payments Service | 99.99% | p99 < 1000ms | 4.4 min/month |
| Search Service | 99.5% | p99 < 2000ms | 3.65 hours/month |
| Notification Service | 99.0% | p99 < 5000ms | 7.3 hours/month |

### 7.3 Error Budget Policy

- **Budget remaining > 50%**: Normal operations, standard change approval
- **Budget remaining 25-50%**: Freeze non-critical releases, increase testing
- **Budget remaining < 25%**: All hands on reliability, only critical fixes
- **Budget exhausted**: Full stop on feature work until budget resets

### 7.4 SLO Burn Rate Alerts

```yaml
- alert: FastBurnRate
  expr: |
    (
      sum(rate(http_requests_total{status=~"5.."}[1h]))
      / sum(rate(http_requests_total[1h]))
    ) > 14.4 * 0.001  # 14.4x burn rate
  for: 2m
  labels:
    severity: P1
```

---

## 8. Incident Response

### 8.1 Incident Lifecycle

```
Detect → Triage → Mitigate → Resolve → Postmortem
```

### 8.2 Roles

| Role | Responsibility |
|------|---------------|
| **Incident Commander (IC)** | Coordinates response, makes decisions, communicates status |
| **Ops Lead** | Executes technical mitigation (rollback, scale, failover) |
| **Comms Lead** | Updates status page, internal stakeholders, customers |
| **Scribe** | Documents timeline, decisions, and actions taken |

### 8.3 Severity Classification

| Severity | Definition | Example |
|----------|------------|---------|
| **SEV1** | Complete outage or data loss | All users cannot access platform |
| **SEV2** | Major feature degraded | Checkout failing for > 10% of users |
| **SEV3** | Minor feature degraded | Search slow but functional |
| **SEV4** | Minimal impact | Single user issue, cosmetic bug |

### 8.4 Response Playbook

1. **Acknowledge** the alert within SLA (5 min for P1)
2. **Assess** impact: who is affected, what is the blast radius
3. **Communicate**: Post in #incidents, update status page
4. **Mitigate**: Rollback last deploy, scale up, failover, feature flag off
5. **Verify**: Confirm metrics return to normal
6. **Resolve**: Mark incident resolved, schedule postmortem within 24h

### 8.5 Postmortem Template

```markdown
# Incident Postmortem: [Title]

- **Date**: YYYY-MM-DD
- **Duration**: HH:MM — HH:MM (X hours Y minutes)
- **Severity**: SEV1/SEV2/SEV3
- **Author**: [Name]
- **Status**: Draft / Reviewed / Published

## Summary
[2-3 sentence summary]

## Impact
- Users affected: X
- Revenue impact: $X
- Data loss: Yes/No

## Timeline (UTC)
| Time | Event |
|------|-------|
| HH:MM | Alert fired |
| HH:MM | IC acknowledged |
| HH:MM | Mitigation applied |
| HH:MM | Incident resolved |

## Root Cause
[Detailed explanation]

## Contributing Factors
- [Factor 1]
- [Factor 2]

## Action Items
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action] | [Name] | [Date] | Open |

## Lessons Learned
- What went well
- What could be improved
```

---

## 9. Runbooks

### 9.1 High Error Rate

**Trigger**: `HighErrorRate` alert fires

1. Check Grafana Service Detail dashboard for the affected service
2. Identify which routes/endpoints have elevated errors
3. Check recent deployments: `kubectl rollout history deployment/<service>`
4. If errors started after deploy → **rollback**: `kubectl rollout undo deployment/<service>`
5. If no recent deploy → check logs in Kibana/Loki for error patterns
6. Check downstream dependencies (DB, cache, external APIs)
7. If dependency issue → enable circuit breaker / fallback
8. If cannot mitigate quickly → scale up: `kubectl scale deployment/<service> --replicas=10`
9. Communicate status in #incidents

### 9.2 High Latency

**Trigger**: `HighLatency` alert fires (p99 > threshold)

1. Check if latency is global or per-endpoint
2. Check infrastructure saturation (CPU, memory, DB connections)
3. Check for slow queries: enable `pg_stat_statements`, review slow query log
4. Check cache hit ratio — if low, investigate cache eviction or key design
5. Check for lock contention or connection pool exhaustion
6. If single AZ → check AZ health, consider traffic shift
7. If database → check for missing indexes, run `EXPLAIN ANALYZE`
8. Scale horizontally if saturation is the cause

### 9.3 Service Down

**Trigger**: `ServiceDown` alert fires

1. Check pod status: `kubectl get pods -n <namespace> -l app=<service>`
2. Check pod logs: `kubectl logs <pod> --previous` (for crashed pods)
3. Check events: `kubectl describe pod <pod>`
4. Common causes:
   - OOMKilled → increase memory limits
   - CrashLoopBackOff → check config, env vars, secrets
   - ImagePullBackOff → verify image tag and registry credentials
5. If node issue → cordon and drain: `kubectl cordon <node> && kubectl drain <node>`
6. If cannot restore → rollback to last known good version

### 9.4 Database Connection Exhaustion

**Trigger**: `DBConnectionsHigh` alert fires

1. Check current connections: `SELECT count(*) FROM pg_stat_activity;`
2. Check for long-running queries: `SELECT * FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '30 seconds';`
3. Kill blocking queries if safe: `SELECT pg_terminate_backend(pid);`
4. Increase pool size temporarily (if connections < max_connections)
5. Check for connection leaks in application code
6. Enable PgBouncer for connection pooling if not already in use
7. Review recent schema changes that might cause lock contention

### 9.5 Certificate Expiry

**Trigger**: `CertExpiringSoon` alert fires (< 14 days)

1. Check cert expiry: `openssl s_client -connect <host>:443 -servername <host> 2>/dev/null | openssl x509 -noout -dates`
2. If using cert-manager → check Certificate resource status
3. If manual → renew cert and update secret: `kubectl create secret tls <secret> --cert=cert.pem --key=key.pem --dry-run=client -o yaml | kubectl apply -f -`
4. Verify new cert is served: repeat step 1
5. Update runbook with new expiry date

---

## 10. Tools

### 10.1 Monitoring Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| **Metrics** | Prometheus | Time-series metrics collection and alerting |
| **Visualization** | Grafana | Dashboards and exploration |
| **Logging** | Elasticsearch + Kibana (ELK) | Log storage, search, and analysis |
| **Log Shipping** | Fluent Bit | Lightweight log forwarder |
| **Tracing** | Jaeger | Distributed trace storage and UI |
| **Tracing SDK** | OpenTelemetry | Instrumentation library |
| **Alerting** | Alertmanager | Alert routing, grouping, silencing |
| **On-call** | PagerDuty | Escalation policies and scheduling |
| **Status Page** | Statuspage.io / Cachet | Customer-facing incident communication |
| **SLO Tracking** | Grafana SLO / Sloth | SLO and error budget monitoring |
| **Synthetic Monitoring** | Blackbox Exporter | Endpoint availability and latency probes |
| **Profiling** | Pyroscope / Parca | Continuous profiling |
| **Chaos Engineering** | Litmus / Chaos Mesh | Resilience testing |

### 10.2 Prometheus Configuration

```yaml
# prometheus.yml (key sections)
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - /etc/prometheus/rules/*.yml

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]

scrape_configs:
  - job_name: 'apex-os-services'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names: ['production']
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: service
```

### 10.3 Grafana Provisioning

```yaml
# provisioning/datasources/prometheus.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true
    editable: false

  - name: Loki
    type: loki
    url: http://loki:3100

  - name: Jaeger
    type: jaeger
    url: http://jaeger:16686
```

### 10.4 ELK Stack Sizing (Production)

| Component | Nodes | CPU | Memory | Disk |
|-----------|-------|-----|--------|------|
| Elasticsearch (hot) | 3 | 8 | 32 GB | 500 GB SSD |
| Elasticsearch (warm) | 2 | 4 | 16 GB | 2 TB HDD |
| Logstash | 2 | 4 | 8 GB | 100 GB |
| Kibana | 1 | 2 | 4 GB | 50 GB |
| Kafka | 3 | 4 | 8 GB | 500 GB |

### 10.5 Jaeger Deployment

```yaml
# Simplified Jaeger all-in-one (dev/staging)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jaeger
  template:
    metadata:
      labels:
        app: jaeger
    spec:
      containers:
        - name: jaeger
          image: jaegertracing/all-in-one:latest
          ports:
            - containerPort: 16686  # UI
            - containerPort: 14268  # Collector (HTTP)
          env:
            - name: COLLECTOR_OTLP_ENABLED
              value: "true"
```

---

## Appendix A: Quick Reference

### Key URLs (Production)

| System | URL |
|--------|-----|
| Grafana | https://grafana.apex-os.internal |
| Prometheus | https://prometheus.apex-os.internal |
| Jaeger | https://jaeger.apex-os.internal |
| Kibana | https://kibana.apex-os.internal |
| PagerDuty | https://apex-os.pagerduty.com |
| Status Page | https://status.apex-os.com |

### Key Commands

```bash
# Check service health
curl -s https://api.apex-os.com/health/ready | jq .

# View logs (last 50 lines, errors only)
kubectl logs -n production deploy/orders-api --tail=50 | grep ERROR

# Check pod resource usage
kubectl top pods -n production --sort-by=memory

# Port-forward to Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Query Prometheus
curl -s 'http://prometheus:9090/api/v1/query?query=up' | jq .
```

### On-Call Checklist

- [ ] PagerDuty app installed and notifications enabled
- [ ] VPN access working
- [ ] SSH access to production jump host
- [ ] Grafana, Kibana, Jaeger bookmarked
- [ ] Incident response runbook reviewed
- [ ] Escalation policy contacts saved in phone
