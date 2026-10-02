# Alerting

## 1. Architecture

```mermaid
flowchart TD
    classDef src fill:#1e3a5f,stroke:#4a9eff,color:#e0e0e0
    classDef proc fill:#3d2b00,stroke:#ffaa00,color:#e0e0e0
    classDef store fill:#1a3a1a,stroke:#44cc44,color:#e0e0e0
    classDef route fill:#3a1a3a,stroke:#cc44cc,color:#e0e0e0
    classDef notify fill:#3a1a1a,stroke:#ff4444,color:#e0e0e0

    subgraph Sources
        A1[Prometheus]:::src
        A2[Alertmanager]:::src
        A3[Custom Exporters]:::src
        A4[Log Aggregator]:::src
    end

    subgraph Processing
        B1[Rule Evaluator]:::proc
        B2[Threshold Engine]:::proc
        B3[Anomaly Detector]:::proc
    end

    subgraph Storage
        C1[(Alert State DB)]:::store
        C2[(Silence Registry)]:::store
        C3[(Alert History)]:::store
    end

    subgraph Routing
        D1[Severity Router]:::route
        D2[Team Router]:::route
        D3[Time-based Router]:::route
    end

    subgraph Notification
        E1[Slack]:::notify
        E2[PagerDuty]:::notify
        E3[Email]:::notify
        E4[Webhook]:::notify
        E5[SMS]:::notify
    end

    A1 --> B1
    A2 --> B1
    A3 --> B2
    A4 --> B3
    B1 --> C1
    B2 --> C1
    B3 --> C1
    C1 --> D1
    C2 --> D1
    D1 --> D2
    D2 --> D3
    D3 --> E1
    D3 --> E2
    D3 --> E3
    D3 --> E4
    D3 --> E5
    E1 --> C3
    E2 --> C3
```

## 2. Alert Rules

| Rule ID | Name | Condition | Severity | Duration |
|---------|------|-----------|----------|----------|
| R-001 | High CPU | `cpu_usage > 90%` | warning | 5m |
| R-002 | Critical CPU | `cpu_usage > 95%` | critical | 2m |
| R-003 | Memory Pressure | `mem_available < 10%` | warning | 5m |
| R-004 | Disk Full | `disk_free < 5%` | critical | 1m |
| R-005 | Service Down | `up == 0` | critical | 0m |
| R-006 | High Latency | `p99_latency > 2000ms` | warning | 3m |
| R-007 | Error Rate Spike | `error_rate > 5%` | critical | 2m |
| R-008 | DB Connections | `db_connections > 80%` | warning | 5m |
| R-009 | Queue Depth | `queue_messages > 10000` | warning | 5m |
| R-010 | SSL Expiry | `ssl_expiry_days < 14` | warning | 1h |
| R-011 | Pod Crash Loop | `restart_count > 5 in 10m` | critical | 0m |
| R-012 | API 5xx Burst | `5xx_rate > 10%` | critical | 1m |

## 3. Alert Routing

```mermaid
flowchart LR
    classDef crit fill:#4a1010,stroke:#ff2222,color:#ffffff
    classDef warn fill:#4a3a10,stroke:#ffaa00,color:#ffffff
    classDef info fill:#1a2a4a,stroke:#4488ff,color:#ffffff

    A[Alert Fired] --> B{Severity?}
    B -->|critical| C[On-Call Engineer]
    B -->|warning| D[Team Channel]
    B -->|info| E[Dashboard Only]

    C --> F{Resolved?}
    D --> F
    F -->|Yes| G[Auto-Close]
    F -->|No, 15m| H[Escalate to TL]
    F -->|No, 30m| I[Escalate to Manager]

    H --> J[PagerDuty]
    I --> J
    G --> K[Log Resolution]

    class C,H,I crit
    class D warn
    class E,G,K info
```

### Routing Table

| Severity | Primary Route | Secondary Route | Business Hours | After Hours |
|----------|--------------|-----------------|----------------|-------------|
| critical | PagerDuty (on-call) | Slack #alerts-critical | Immediate | Immediate |
| warning | Slack #alerts-warning | Email team lead | < 5 min | < 15 min |
| info | Dashboard | Log only | Batch | Batch |

## 4. Alert Escalation

```mermaid
flowchart TD
    classDef l1 fill:#2a1a00,stroke:#ff8800,color:#ffffff
    classDef l2 fill:#3a1a00,stroke:#ff4400,color:#ffffff
    classDef l3 fill:#3a0a0a,stroke:#ff0000,color:#ffffff

    A[Alert Triggered] --> B[L1: On-Call Engineer]
    B -->|Ack within 5m| C[Monitor]
    B -->|No ack 5m| D[L2: Team Lead]
    D -->|Ack within 10m| C
    D -->|No ack 10m| E[L3: Engineering Manager]
    E -->|Ack within 15m| C
    E -->|No ack 15m| F[L4: Director]
    F -->|Ack within 30m| C
    F -->|No ack 30m| G[Incident Commander]

    class B l1
    class D l2
    class E,F,G l3
```

### Escalation Policy

| Level | Role | Timeout | Action |
|-------|------|---------|--------|
| L1 | On-Call Engineer | 5 min | PagerDuty + Slack DM |
| L2 | Team Lead | 10 min | PagerDuty + Phone |
| L3 | Engineering Manager | 15 min | PagerDuty + Phone |
| L4 | Director | 30 min | Executive bridge |

## 5. Alert Suppression

```mermaid
flowchart TD
    classDef sup fill:#1a2a1a,stroke:#22aa22,color:#e0e0e0
    classDef act fill:#2a1a1a,stroke:#aa2222,color:#e0e0e0

    A[Incoming Alert] --> B{Matches Silence?}
    B -->|Yes| C[Suppress]:::sup
    B -->|No| D{Maintenance Window?}
    D -->|Yes| E[Defer]:::sup
    D -->|No| F{Duplicate?}
    F -->|Yes, < 5m| G[Group]:::sup
    F -->|No| H[Route to Handler]:::act

    C --> I[Log Suppressed]
    E --> I
    G --> I
```

### Suppression Rules

| Type | Scope | Duration | Auto-Expire |
|------|-------|----------|-------------|
| Silence | Single alert/rule | 1-24h | Yes |
| Maintenance | Service/group | Scheduled window | Yes |
| Grouping | Related alerts | 5 min window | No |
| Dependency | Downstream of known issue | Until parent resolves | Yes |
| Flapping | Alert toggling > 10x/hour | 30 min | Yes |

### Suppression Commands

```bash
# Silence a rule for 2 hours
apex alert silence --rule R-005 --duration 2h --reason "DB migration"

# Silence all alerts for a service during maintenance
apex alert silence --service payments --duration 4h --reason "v2.1 deploy"

# List active silences
apex alert silence --list

# Expire a silence early
apex alert silence --expire <silence-id>
```
