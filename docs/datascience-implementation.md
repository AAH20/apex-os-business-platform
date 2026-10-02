# Data Science Implementation

## 1. MLOps Pipeline

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','primaryBorderColor':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#0f3460','edgeLabelBackground':'#1a1a2e'}}}%%
flowchart TD
    subgraph Data["Data Layer"]
        D1[(Raw Data)]
        D2[Data Validation]
        D3[Feature Store]
    end
    subgraph Training["Training Layer"]
        T1[Experiment Tracking]
        T2[Distributed Training]
        T3[Hyperparameter Tuning]
        T4[Model Evaluation]
    end
    subgraph Registry["Model Registry"]
        R1[Version Control]
        R2[Staging]
        R3[Production]
        R4[Archived]
    end
    subgraph Serving["Serving Layer"]
        S1[Model Serving]
        S2[Shadow Deployment]
        S3[Canary Release]
        S4[A/B Testing]
    end
    subgraph Monitoring["Monitoring Layer"]
        M1[Drift Detection]
        M2[Performance Metrics]
        M3[Alerting]
        M4[Retrigger Pipeline]
    end
    D1 --> D2 --> D3
    D3 --> T1 --> T2 --> T3 --> T4
    T4 --> R1
    R1 --> R2 --> R3
    R3 --> S1
    S1 --> S2 --> S3 --> S4
    S4 --> M1
    M1 --> M2 --> M3
    M3 -->|Drift Detected| M4
    M4 -->|Retrain| T1
    style Data fill:#16213e,stroke:#0f3460,color:#e0e0e0
    style Training fill:#1a1a2e,stroke:#4fc3f7,color:#e0e0e0
    style Registry fill:#0f3460,stroke:#4fc3f7,color:#e0e0e0
    style Serving fill:#16213e,stroke:#0f3460,color:#e0e0e0
    style Monitoring fill:#1a1a2e,stroke:#e94560,color:#e0e0e0
```

### Pipeline Stages

| Stage | Tool | Output |
|-------|------|--------|
| Data Validation | Great Expectations | Validation report |
| Feature Engineering | Feast | Feature vectors |
| Experiment Tracking | MLflow | Run metadata |
| Training | PyTorch / Ray | Trained model |
| Registry | MLflow Registry | Versioned model |
| Serving | Triton / Seldon | REST/gRPC endpoint |
| Monitoring | Evidently / Prometheus | Drift & metrics |

---

## 2. Feature Engineering Patterns

### Feature Store Architecture

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','primaryBorderColor':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#0f3460','edgeLabelBackground':'#1a1a2e'}}}%%
flowchart LR
    subgraph Sources["Data Sources"]
        S1[(OLTP DB)]
        S2[(OLAP Warehouse)]
        S3[Streaming Kafka]
    end
    subgraph Transform["Transformations"]
        T1[Batch Features]
        T2[Streaming Features]
        T3[On-Demand Features]
    end
    subgraph Store["Feature Store"]
        F1[(Offline Store\nParquet/S3)]
        F2[(Online Store\nRedis/DynamoDB)]
    end
    subgraph Consumers["Consumers"]
        C1[Training]
        C2[Serving]
        C3[Analytics]
    end
    S1 --> T1
    S2 --> T1
    S3 --> T2
    T1 --> F1
    T2 --> F2
    T3 --> F2
    F1 --> C1
    F2 --> C2
    F1 --> C3
    style Sources fill:#16213e,stroke:#0f3460,color:#e0e0e0
    style Transform fill:#1a1a2e,stroke:#4fc3f7,color:#e0e0e0
    style Store fill:#0f3460,stroke:#4fc3f7,color:#e0e0e0
    style Consumers fill:#16213e,stroke:#0f3460,color:#e0e0e0
```

### Core Patterns

**Point-in-Time Correctness**
- Use event timestamps, not ingestion timestamps
- Prevent training-serving skew with time-travel joins
- Validate feature freshness before serving

**Feature Categories**

| Category | Example | Storage | TTL |
|----------|---------|---------|-----|
| Batch | Daily aggregates | Parquet/S3 | 30 days |
| Streaming | Real-time counters | Redis | 1 hour |
| On-Demand | Request context | In-memory | Per-request |
| Embedding | User vectors | Faiss/Milvus | 7 days |

**Feature Pipeline Contract**
```python
@feature_view(
    entities=[user_id],
    ttl=timedelta(hours=24),
    online=True,
)
def user_features(user_events):
    return {
        "total_orders_7d": aggregate(user_events, window="7d"),
        "avg_order_value_30d": mean(user_events.amount, window="30d"),
        "last_active_days": days_since(user_events[-1].timestamp),
    }
```

---

## 3. Model Registry Architecture

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','primaryBorderColor':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#0f3460','edgeLabelBackground':'#1a1a2e'}}}%%
flowchart TD
    subgraph CI["CI/CD Pipeline"]
        C1[Code Push]
        C2[Unit Tests]
        C3[Model Training]
        C4[Model Evaluation]
        C5[Register Model]
    end
    subgraph States["Model States"]
        direction LR
        ST1[None] --> ST2[Staging]
        ST2 --> ST3[Production]
        ST3 --> ST4[Archived]
        ST4 --> ST1
    end
    subgraph Artifacts["Artifacts"]
        A1[Model Binary]
        A2[Dependencies]
        A3[Training Data Hash]
        A4[Metrics JSON]
        A5[Lineage Graph]
    end
    subgraph Deploy["Deployment"]
        DP1[Shadow]
        DP2[Canary 5%]
        DP3[Canary 50%]
        DP4[Full Rollout]
    end
    C1 --> C2 --> C3 --> C4 --> C5
    C5 --> ST2
    ST2 -->|Promote| ST3
    ST3 -->|Deprecate| ST4
    C5 --- A1 & A2 & A3 & A4 & A5
    ST3 --> DP1 --> DP2 --> DP3 --> DP4
    style CI fill:#16213e,stroke:#0f3460,color:#e0e0e0
    style States fill:#1a1a2e,stroke:#4fc3f7,color:#e0e0e0
    style Artifacts fill:#0f3460,stroke:#4fc3f7,color:#e0e0e0
    style Deploy fill:#16213e,stroke:#0f3460,color:#e0e0e0
```

### Registry Metadata Schema

```json
{
  "model_id": "fraud-detection",
  "version": "42",
  "stage": "production",
  "metrics": {"auc": 0.94, "precision": 0.89, "recall": 0.82},
  "training_data": {"hash": "sha256:abc123", "rows": 1500000},
  "hyperparams": {"lr": 0.001, "epochs": 50, "batch_size": 256},
  "dependencies": {"torch": "2.1.0", "feast": "0.34.0"},
  "lineage": {"parent_version": 41, "experiment_id": "exp-2024-001"},
  "approved_by": "data-science-lead",
  "deployed_at": "2024-01-15T10:30:00Z"
}
```

### Promotion Criteria

| From | To | Criteria |
|------|----|----------|
| None | Staging | CI passes, evaluation complete |
| Staging | Production | AUC > 0.90, no data drift, peer review |
| Production | Archived | Superseded by newer version |
| Archived | None | Re-validated and re-registered |

---

## 4. A/B Testing Framework

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','primaryBorderColor':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#0f3460','edgeLabelBackground':'#1a1a2e'}}}%%
flowchart TD
    subgraph Config["Experiment Config"]
        E1[Experiment Definition]
        E2[Traffic Split]
        E3[Success Metrics]
        E4[Guardrail Metrics]
    end
    subgraph Assignment["Assignment"]
        A1[Hash User ID]
        A2[Bucket Assignment]
        A3[Consistent Routing]
    end
    subgraph Execution["Execution"]
        X1[Control - Model A]
        X2[Treatment - Model B]
        X3[Feature Flags]
    end
    subgraph Analysis["Analysis"]
        AN1[Metric Collection]
        AN2[Statistical Test]
        AN3[Significance Check]
        AN4[Decision]
    end
    subgraph Decision["Decision"]
        DC1[Roll Back]
        DC2[Full Rollout]
        DC3[Iterate]
    end
    E1 --> E2 --> E3
    E1 --> E4
    E2 --> A1 --> A2 --> A3
    A3 --> X1 & X2
    X1 --> AN1
    X2 --> AN1
    AN1 --> AN2 --> AN3 --> AN4
    AN4 -->|Not Significant| DC1
    AN4 -->|Significant Win| DC2
    AN4 -->|Inconclusive| DC3
    style Config fill:#16213e,stroke:#0f3460,color:#e0e0e0
    style Assignment fill:#1a1a2e,stroke:#4fc3f7,color:#e0e0e0
    style Execution fill:#0f3460,stroke:#4fc3f7,color:#e0e0e0
    style Analysis fill:#16213e,stroke:#0f3460,color:#e0e0e0
    style Decision fill:#1a1a2e,stroke:#e94560,color:#e0e0e0
```

### Experiment Configuration

```yaml
experiment:
  name: "recommendation-model-v2"
  id: "exp-rec-2024-001"
  hypothesis: "Neural CF improves CTR by 5%"
  start_date: "2024-01-15"
  end_date: "2024-02-15"
  traffic_allocation: 100
  variants:
    control:
      model: "collaborative-filtering-v1"
      weight: 50
    treatment:
      model: "neural-cf-v2"
      weight: 50
  metrics:
    primary: "ctr"
    secondary: ["conversion_rate", "revenue_per_user"]
    guardrails: ["latency_p99", "error_rate"]
  significance:
    alpha: 0.05
    power: 0.80
    mde: 0.05
```

### Statistical Tests

| Scenario | Test | Notes |
|----------|------|-------|
| Continuous metric | Welch's t-test | Unequal variances |
| Proportion metric | Chi-squared / Z-test | CTR, conversion |
| Multiple variants | Bonferroni correction | Family-wise error |
| Sequential testing | Always-valid p-values | Early stopping |

---

## 5. Monitoring and Observability

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','primaryBorderColor':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#0f3460','edgeLabelBackground':'#1a1a2e'}}}%%
flowchart TD
    subgraph Signals["Signal Collection"]
        S1[Prediction Logs]
        S2[Feature Logs]
        S3[Ground Truth]
        S4[Latency Metrics]
    end
    subgraph Detection["Detection"]
        D1[Data Drift\nPSI/KS Test]
        D2[Concept Drift\nError Rate Shift]
        D3[Feature Drift\nDistribution Shift]
        D4[Performance Drift\nMetric Degradation]
    end
    subgraph Alerting["Alerting"]
        A1[Threshold Alerts]
        A2[Anomaly Detection]
        A3[Slack/PagerDuty]
    end
    subgraph Response["Response"]
        R1[Auto-Rollback]
        R2[Retrain Trigger]
        R3[Human Review]
    end
    S1 & S2 --> D1 & D3
    S3 --> D2 & D4
    S4 --> D4
    D1 & D2 & D3 & D4 --> A1 & A2
    A1 & A2 --> A3
    A3 --> R1 & R2 & R3
    style Signals fill:#16213e,stroke:#0f3460,color:#e0e0e0
    style Detection fill:#1a1a2e,stroke:#4fc3f7,color:#e0e0e0
    style Alerting fill:#0f3460,stroke:#4fc3f7,color:#e0e0e0
    style Response fill:#16213e,stroke:#e94560,color:#e0e0e0
```

### Monitoring Layers

| Layer | What | Tool | Frequency |
|-------|------|------|-----------|
| Infrastructure | CPU/GPU, memory, disk | Prometheus | 15s |
| Serving | Latency, throughput, errors | Envoy/StatsD | Real-time |
| Data | Schema, distribution, nulls | Evidently | Hourly |
| Model | Prediction distribution, confidence | Custom | Real-time |
| Business | Revenue, conversion, retention | BI Dashboard | Daily |

### Drift Detection Methods

| Drift Type | Method | Threshold | Action |
|------------|--------|-----------|--------|
| Data Drift | PSI | > 0.2 | Alert + retrain |
| Feature Drift | KS test | p < 0.01 | Alert |
| Concept Drift | Error rate CUSUM | 3σ shift | Auto-rollback |
| Performance | Rolling AUC | < 0.85 | Retrain |

### Alert Routing

```
severity: critical
  condition: error_rate > 5% OR latency_p99 > 500ms
  action: auto-rollback + page on-call

severity: warning
  condition: psi > 0.2 OR auc_drop > 0.03
  action: slack #ml-alerts + create ticket

severity: info
  condition: feature_freshness > 2x expected
  action: slack #ml-ops
```

### Retrigger Policy

```yaml
retraining:
  trigger:
    schedule: "0 2 * * 0"  # Weekly
    drift_threshold: 0.25
    performance_threshold: 0.85
  validation:
    min_auc: 0.88
    max_psi: 0.15
    min_samples: 10000
  deployment:
    strategy: canary
    stages: [5, 25, 50, 100]
    stage_duration: 30m
    auto_promote: true
    rollback_on_failure: true
```
