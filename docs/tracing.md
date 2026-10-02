# APEX-OS Tracing Guide

## 1. Tracing Architecture

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','secondaryColor':'#16213e','tertiaryColor':'#0f3460','background':'#0d1117','mainBkg':'#1a1a2e','nodeBorder':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#e94560','titleColor':'#e0e0e0','edgeLabelBackground':'#16213e'}}}%%
flowchart LR
    subgraph Client["Client Layer"]
        C1[Web App]
        C2[Mobile App]
        C3[CLI Tool]
    end
    subgraph Gateway["API Gateway"]
        GW[Envoy Proxy]
    end
    subgraph Services["Microservices"]
        S1[Auth Service]
        S2[Order Service]
        S3[Payment Service]
        S4[Inventory Service]
        S5[Notification Service]
    end
    subgraph Infra["Infrastructure"]
        DB[(PostgreSQL)]
        CACHE[(Redis)]
        MQ[Kafka]
        OBJ[(S3)]
    end
    subgraph Observability["Observability Stack"]
        OTEL[OpenTelemetry Collector]
        JAEGER[Jaeger]
        PROM[Prometheus]
        GRAF[Grafana]
        LOKI[Loki]
    end
    C1 & C2 & C3 --> GW
    GW --> S1 & S2 & S3 & S4 & S5
    S1 & S2 & S3 & S4 & S5 --> DB & CACHE & MQ & OBJ
    S1 & S2 & S3 & S4 & S5 -.->|OTLP| OTEL
    GW -.->|OTLP| OTEL
    OTEL --> JAEGER & PROM
    JAEGER --> GRAF
    PROM --> GRAF
    GRAF --> LOKI
```

### Component Roles

| Component | Role |
|-----------|------|
| OpenTelemetry SDK | Instrumentation in each service |
| OTEL Collector | Receives, processes, exports telemetry |
| Jaeger | Distributed trace storage & query |
| Prometheus | Metrics aggregation |
| Grafana | Unified dashboards |
| Loki | Log correlation |

---

## 2. Span Management

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','secondaryColor':'#16213e','tertiaryColor':'#0f3460','background':'#0d1117','mainBkg':'#1a1a2e','nodeBorder':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#e94560','titleColor':'#e0e0e0','edgeLabelBackground':'#16213e'}}}%%
flowchart TD
    ROOT["Root Span: POST /api/orders"]
    ROOT --> SVC1["Auth Span"]
    ROOT --> SVC2["Order Span"]
    ROOT --> SVC3["Payment Span"]
    SVC2 --> DB1["DB Span: INSERT orders"]
    SVC2 --> CACHE1["Cache Span: SET session"]
    SVC3 --> EXT["HTTP Span: Stripe API"]
    SVC3 --> MQ1["Kafka Span: publish event"]
    style ROOT fill:#e94560,stroke:#ff6b6b,color:#fff
    style SVC1 fill:#0f3460,stroke:#4fc3f7,color:#e0e0e0
    style SVC2 fill:#0f3460,stroke:#4fc3f7,color:#e0e0e0
    style SVC3 fill:#0f3460,stroke:#4fc3f7,color:#e0e0e0
    style DB1 fill:#16213e,stroke:#26de81,color:#e0e0e0
    style CACHE1 fill:#16213e,stroke:#26de81,color:#e0e0e0
    style EXT fill:#16213e,stroke:#fd9644,color:#e0e0e0
    style MQ1 fill:#16213e,stroke:#fd9644,color:#e0e0e0
```

### Span Lifecycle

1. **Creation** — Root span created at entry point (HTTP/gRPC handler)
2. **Context Propagation** — Trace context injected into headers (`traceparent`, `tracestate`)
3. **Child Spans** — Each downstream call creates a child span linked via `parentSpanId`
4. **Events & Attributes** — Key timestamps and metadata attached to spans
5. **Completion** — Span closed with status (OK/ERROR) and exported via OTLP

### Span Attributes Convention

| Attribute | Description | Example |
|-----------|-------------|---------|
| `http.method` | HTTP method | `POST` |
| `http.route` | Route path | `/api/orders` |
| `http.status_code` | Response code | `201` |
| `db.system` | Database type | `postgresql` |
| `db.statement` | Query (sampled) | `INSERT INTO orders...` |
| `messaging.system` | Message broker | `kafka` |
| `service.name` | Service identifier | `order-service` |
| `deployment.environment` | Environment | `production` |

---

## 3. Sampling Strategy

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','secondaryColor':'#16213e','tertiaryColor':'#0f3460','background':'#0d1117','mainBkg':'#1a1a2e','nodeBorder':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#e94560','titleColor':'#e0e0e0','edgeLabelBackground':'#16213e'}}}%%
flowchart TD
    START[Incoming Request] --> CHECK{Error?}
    CHECK -->|Yes| ALWAYS[Always Sample 100%]
    CHECK -->|No| HEAD{Head-based Sampling}
    HEAD -->|trace_id % 100 < 10| KEEP[Keep Trace]
    HEAD -->|else| DROP[Drop Trace]
    KEEP --> TAIL{Tail-based Sampling}
    TAIL -->|latency > 500ms| SLOW[Slow Trace Kept]
    TAIL -->|latency <= 500ms| NORMAL[Normal Trace Kept]
    SLOW --> EXPORT[Export to Jaeger]
    NORMAL --> EXPORT
    ALWAYS --> EXPORT
    style START fill:#0f3460,stroke:#4fc3f7,color:#e0e0e0
    style CHECK fill:#e94560,stroke:#ff6b6b,color:#fff
    style HEAD fill:#e94560,stroke:#ff6b6b,color:#fff
    style TAIL fill:#e94560,stroke:#ff6b6b,color:#fff
    style ALWAYS fill:#26de81,stroke:#26de81,color:#fff
    style KEEP fill:#26de81,stroke:#26de81,color:#fff
    style DROP fill:#fd9644,stroke:#fd9644,color:#fff
    style SLOW fill:#26de81,stroke:#26de81,color:#fff
    style NORMAL fill:#26de81,stroke:#26de81,color:#fff
    style EXPORT fill:#0f3460,stroke:#4fc3f7,color:#e0e0e0
```

### Sampling Layers

| Layer | Strategy | Rate | Purpose |
|-------|----------|------|---------|
| Head-based | Deterministic (trace_id hash) | 10% | Baseline traffic coverage |
| Error-based | Always sample errors | 100% | Capture all failures |
| Slow-request | Latency threshold | 100% if >500ms | Debug performance issues |
| Tail-based | Post-decision in collector | Configurable | Retain interesting traces |

### Configuration

```yaml
processors:
  probabilistic_sampler:
    sampling_percentage: 10
  tail_sampling:
    decision_wait: 10s
    num_traces: 100000
    expected_new_traces_per_sec: 1000
    policies:
      - name: errors-policy
        type: status_code
        status_code: {status_codes: [ERROR]}
      - name: slow-requests-policy
        type: latency
        latency: {threshold_ms: 500}
```

---

## 4. Analytics

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','secondaryColor':'#16213e','tertiaryColor':'#0f3460','background':'#0d1117','mainBkg':'#1a1a2e','nodeBorder':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#e94560','titleColor':'#e0e0e0','edgeLabelBackground':'#16213e'}}}%%
flowchart LR
    subgraph Sources["Data Sources"]
        T[Traces]
        M[Metrics]
        L[Logs]
    end
    subgraph Processing["Stream Processing"]
        FLINK[Apache Flink]
        KSQL[KSQL]
    end
    subgraph Storage["Analytics Store"]
        CLICK[(ClickHouse)]
        ELASTIC[(Elasticsearch)]
    end
    subgraph Serving["Query Layer"]
        API[Analytics API]
        DASH[Grafana]
    end
    T & M & L --> FLINK
    T & M & L --> KSQL
    FLINK --> CLICK
    KSQL --> ELASTIC
    CLICK --> API
    ELASTIC --> API
    API --> DASH
```

### Key Metrics Derived from Traces

| Metric | Calculation | Use Case |
|--------|-------------|----------|
| Request Rate | `count(spans) / time_window` | Traffic monitoring |
| Error Rate | `count(error spans) / count(all spans)` | SLA tracking |
| P50/P95/P99 Latency | Percentile of span durations | Performance SLOs |
| Dependency Graph | Service-to-service edge weights | Architecture analysis |
| Critical Path | Longest path in trace tree | Bottleneck identification |

### Alert Rules

```yaml
groups:
  - name: tracing-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(spans_total{status="ERROR"}[5m]) / rate(spans_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
      - alert: HighLatency
        expr: histogram_quantile(0.99, rate(span_duration_bucket[5m])) > 1000
        for: 5m
        labels:
          severity: warning
```

---

## 5. Visualization

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','secondaryColor':'#16213e','tertiaryColor':'#0f3460','background':'#0d1117','mainBkg':'#1a1a2e','nodeBorder':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#e94560','titleColor':'#e0e0e0','edgeLabelBackground':'#16213e'}}}%%
flowchart TD
    subgraph GrafanaDashboards["Grafana Dashboards"]
        D1[Service Overview]
        D2[Trace Explorer]
        D3[Dependency Map]
        D4[SLO Compliance]
        D5[Error Analysis]
    end
    subgraph JaegerUI["Jaeger UI"]
        J1[Trace Timeline]
        J2[Trace Graph]
        J3[Compare Traces]
    end
    subgraph Custom["Custom Views"]
        V1[Flame Graph]
        V2[Heatmap]
        V3[Service Mesh]
    end
    D1 --> J1
    D2 --> J2
    D3 --> V3
    D4 --> V2
    D5 --> V1
```

### Dashboard Panels

| Panel | Type | Data Source | Refresh |
|-------|------|-------------|---------|
| Request Rate | Time series | Prometheus | 10s |
| Error Rate | Gauge | Prometheus | 10s |
| P99 Latency | Time series | Prometheus | 30s |
| Service Map | Node graph | Jaeger | 30s |
| Trace List | Table | Jaeger | On-demand |
| Flame Graph | Flamegraph | Jaeger | On-demand |

### Trace Waterfall View

```
┌─────────────────────────────────────────────────────────────────┐
│ POST /api/orders  [120ms]                                       │
├─────────────────────────────────────────────────────────────────┤
│ ├─ Auth Service  [8ms]                                          │
│ │   └─ DB Query  [3ms]                                          │
│ ├─ Order Service  [85ms]                                        │
│ │   ├─ DB INSERT  [12ms]                                        │
│ │   ├─ Cache SET  [2ms]                                         │
│ │   └─ Payment Service  [65ms]                                  │
│ │       ├─ Stripe API  [55ms]                                   │
│ │       └─ Kafka Publish  [5ms]                                 │
│ └─ Notification  [15ms]                                         │
└─────────────────────────────────────────────────────────────────┘
```

### Log–Trace Correlation

```json
{
  "timestamp": "2026-10-02T10:30:00Z",
  "trace_id": "abc123def456",
  "span_id": "span789",
  "service": "order-service",
  "message": "Order created successfully",
  "level": "info"
}
```

---

## Quick Reference

| Task | Command / Link |
|------|----------------|
| View traces | `http://jaeger.apexos.local:16686` |
| Dashboards | `http://grafana.apexos.local:3000` |
| OTLP endpoint | `http://otel-collector:4317` |
| Collector config | `/etc/otel-collector/config.yaml` |
| Sampling rate | `OTEL_TRACES_SAMPLER_ARG=0.1` |
