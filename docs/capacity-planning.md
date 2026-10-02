# Capacity Planning

## 1. Architecture

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TB
    subgraph Sources["Data Sources"]
        M[Metrics / Prometheus]
        L[Logs / Loki]
        T[Traces / Tempo]
        B[Business Events]
    end

    subgraph Forecast["Forecasting Engine"]
        H[Historical Aggregator]
        ML[ML Forecaster]
        S[Seasonality Detector]
        H --> ML
        S --> ML
    end

    subgraph Decision["Decision Layer"]
        P[Policy Engine]
        R[Risk Scorer]
        P --> R
    end

    subgraph Actions["Scaling Actions"]
        HPA[Horizontal Pod Autoscaler]
        VPA[Vertical Pod Autoscaler]
        CA[Cluster Autoscaler]
        Q[Queue Scaler]
    end

    subgraph Guardrails["Guardrails"]
        BUD[Budget Guard]
        MAX[Max Replicas]
        COOLDOWN[Cooldown Timer]
    end

    M --> H
    L --> H
    T --> H
    B --> S
    ML --> P
    R --> HPA
    R --> VPA
    R --> CA
    R --> Q
    BUD --> P
    MAX --> P
    COOLDOWN --> P
```

## 2. Resource Forecasting

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    A[Raw Metrics] --> B[Window Aggregator]
    B --> C[Trend Analysis]
    C --> D{Forecast Model}
    D -->|Short-term| E[ARIMA / Prophet]
    D -->|Long-term| F[LSTM / XGBoost]
    D -->|Event-driven| G[Regression + Calendar]
    E --> H[Confidence Interval]
    F --> H
    G --> H
    H --> I[Capacity Recommendation]
```

**Forecasting inputs:**
- Historical utilization (CPU, memory, I/O, network)
- Business seasonality (hourly, daily, weekly, monthly)
- Growth trends (linear, exponential, step)
- Planned events (launches, campaigns, holidays)

**Output:** Projected resource demand with 80%/95%/99% confidence bands.

## 3. Scaling Strategy

```mermaid
%%{init: {'theme': 'dark'}}%%
stateDiagram-v2
    [*] --> Normal
    Normal --> ScaleUp: Util > 70% for 3min
    Normal --> ScaleDown: Util < 30% for 10min
    ScaleUp --> Normal: Util < 60% for 5min
    ScaleUp --> Emergency: Util > 90% for 1min
    Emergency --> Normal: Util < 70% for 5min
    ScaleDown --> Normal: Util > 50% for 2min
    Emergency --> CircuitBreaker: Error rate > 5%
    CircuitBreaker --> Normal: Error rate < 1% for 5min
```

**Scaling tiers:**

| Tier | Trigger | Action | Cooldown |
|------|---------|--------|----------|
| Reactive | CPU/Mem threshold | HPA ±1 replica | 60s |
| Predictive | Forecast > 80% | Pre-scale +2 replicas | 300s |
| Scheduled | Known event | Pre-scale to target | Event-based |
| Emergency | Saturation | Max replicas + alert | 30s |

## 4. Cost Optimization

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TB
    subgraph Identify["Identify Waste"]
        IDLE[Idle Resources]
        OVERSIZE[Oversized Packets]
        SPOT[Spot Interruptible]
        RESERVED[Reserved Capacity]
    end

    subgraph Optimize["Optimize"]
        RIGHT[Right-size Requests]
        BIN[Bin Packing]
        SPOTMIG[Spot Migration]
        SAVINGS[Savings Plan Purchase]
    end

    subgraph Validate["Validate"]
        SLO[SLO Check]
        BUDGET[Budget Alert]
        REPORT[Cost Report]
    end

    IDLE --> RIGHT
    OVERSIZE --> RIGHT
    SPOT --> SPOTMIG
    RESERVED --> SAVINGS
    RIGHT --> BIN
    SPOTMIG --> BIN
    SAVINGS --> BIN
    BIN --> SLO
    SLO --> BUDGET
    BUDGET --> REPORT
```

**Levers:**
- Right-size resource requests vs. actual usage
- Bin-packing to maximize node utilization
- Spot/preemptible instances for stateless workloads
- Reserved instances for predictable baseline
- Auto-shutdown of non-production environments

## 5. Monitoring

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    subgraph Collect["Collection"]
        PROM[Prometheus]
        GRAF[Grafana]
        ALERT[Alertmanager]
    end

    subgraph Dashboards["Dashboards"]
        CAP[Capacity Overview]
        FORE[Forecast vs Actual]
        COST[Cost per Request]
        SLO[SLO / Error Budget]
    end

    subgraph Alerts["Alerts"]
        A1[Forecast Breach]
        A2[Cost Anomaly]
        A3[SLO Burn Rate]
        A4[Scaling Failure]
    end

    PROM --> GRAF
    GRAF --> CAP
    GRAF --> FORE
    GRAF --> COST
    GRAF --> SLO
    PROM --> ALERT
    ALERT --> A1
    ALERT --> A2
    ALERT --> A3
    ALERT --> A4
```

**Key metrics:**
- `capacity_forecast_utilization_ratio` — predicted vs. actual
- `cost_per_1k_requests` — unit economics
- `scaling_latency_seconds` — time to scale
- `resource_headroom_percent` — available capacity
- `slo_burn_rate` — error budget consumption

**Alert routing:** PagerDuty for SLO burn, Slack for forecast/cost warnings.
