# ML Platform

## 1. ML Architecture

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    subgraph Data Layer
        DB[(Postgres)]
        S3[(S3 / Data Lake)]
        K[Kafka / Event Stream]
    end

    subgraph Feature Store
        FS[Feast Feature Store]
        FS_Online[(Online Store<br/>Redis)]
        FS_Offline[(Offline Store<br/>Parquet)]
    end

    subgraph Training
        TR[Training Pipeline<br/>Kubeflow / Airflow]
        EXP[Experiment Tracker<br/>MLflow]
        REG[(Model Registry)]
    end

    subgraph Serving
        API[API Gateway]
        INF[Inference Service<br/>Triton / TorchServe]
        CB[Canary / Shadow]
    end

    subgraph Monitoring
        MON[Prometheus + Grafana]
        EVT[Evidently / Drift Detector]
        AL[Alertmanager]
    end

    DB --> FS
    S3 --> FS
    K --> FS
    FS --> FS_Online
    FS --> FS_Offline
    FS_Offline --> TR
    TR --> EXP
    TR --> REG
    REG --> INF
    FS_Online --> INF
    API --> INF
    INF --> CB
    INF --> MON
    INF --> EVT
    MON --> AL
    EVT --> AL
```

## 2. Model Training

- **Orchestration**: Kubeflow Pipelines / Airflow DAGs for reproducible training runs.
- **Experiment Tracking**: MLflow tracks parameters, metrics, artifacts, and model versions.
- **Data**: Training datasets pulled from the offline feature store (Parquet on S3).
- **Validation**: Each run is evaluated against a holdout set; metrics logged to MLflow.
- **Registration**: Models that pass quality gates are promoted to the Model Registry with stage labels (`Staging` → `Production`).
- **Reproducibility**: Every training run pins data snapshot, code commit, and dependency versions.

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart TD
    A[Load Training Data] --> B[Feature Engineering]
    B --> C[Train Model]
    C --> D[Evaluate on Holdout]
    D --> E{Quality Gate}
    E -->|Pass| F[Log to MLflow]
    E -->|Fail| G[Alert & Stop]
    F --> H[Register Model]
    H --> I[Stage: Staging]
    I --> J[Integration Tests]
    J --> K[Stage: Production]
```

## 3. Model Serving

- **Inference Server**: Triton Inference Server or TorchServe for GPU-accelerated batch/real-time inference.
- **API Gateway**: REST/gRPC endpoints with auth, rate limiting, and request validation.
- **Online Features**: Low-latency feature lookup from Redis-backed online store.
- **Deployment Strategy**: Canary releases — 5% traffic to new model, auto-promote if error rate < threshold.
- **Shadow Mode**: New model receives traffic but responses are discarded; used for pre-launch validation.
- **Scaling**: Horizontal pod autoscaling based on GPU utilization and request queue depth.

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    Client --> GW[API Gateway]
    GW --> Auth[Auth / Rate Limit]
    Auth --> Router[Traffic Router]
    Router -->|95%| V1[Model v1<br/>Production]
    Router -->|5%| V2[Model v2<br/>Canary]
    V1 --> R[(Redis<br/>Online Features)]
    V2 --> R
    V1 --> Resp[Response]
    V2 --> Resp
```

## 4. Feature Store

- **Framework**: Feast — open-source feature store for managing, storing, and serving features.
- **Offline Store**: Parquet files on S3 — used for training data generation and batch scoring.
- **Online Store**: Redis — sub-millisecond feature lookup for real-time inference.
- **Feature Definitions**: Versioned, declarative feature definitions in code (Python SDK).
- **Point-in-Time Correctness**: Training datasets generated with `get_historical_features()` prevent label leakage.
- **Streaming Features**: Kafka → Flink → online store for real-time aggregations (e.g., session counts).

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart TD
    subgraph Sources
        PG[(Postgres)]
        KAFKA[Kafka]
    end

    subgraph Feast
        DEF[Feature Definitions<br/>Python SDK]
        TRF[Transformation<br/>Flink / dbt]
    end

    subgraph Stores
        OFF[(Offline Store<br/>S3 Parquet)]
        ON[(Online Store<br/>Redis)]
    end

    PG --> DEF
    KAFKA --> TRF
    TRF --> ON
    DEF --> OFF
    DEF --> ON
```

## 5. Model Monitoring

- **Infrastructure Metrics**: Prometheus scrapes GPU utilization, latency (p50/p95/p99), throughput, and error rates.
- **Data Drift**: Evidently / custom detectors compare training vs. production feature distributions (PSI, KS test).
- **Prediction Drift**: Monitor output distribution shifts and confidence score degradation.
- **Model Performance**: Ground truth joined back to predictions for accuracy/F1/AUC tracking.
- **Alerting**: Alertmanager routes to Slack/PagerDuty with severity-based escalation.
- **Dashboards**: Grafana dashboards per model version with SLO burn-rate alerts.

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    subgraph Collect
        P[Prometheus]
        E[Evidently]
        L[Label Joiner]
    end

    subgraph Analyze
        DRIFT[Drift Detection<br/>PSI / KS]
        PERF[Performance Metrics<br/>Accuracy / AUC]
        SLO[SLO Burn Rate]
    end

    subgraph Act
        G[Grafana Dashboard]
        AM[Alertmanager]
        PD[PagerDuty / Slack]
    end

    P --> DRIFT
    P --> SLO
    E --> DRIFT
    L --> PERF
    DRIFT --> G
    PERF --> G
    SLO --> G
    DRIFT --> AM
    PERF --> AM
    SLO --> AM
    AM --> PD
```
