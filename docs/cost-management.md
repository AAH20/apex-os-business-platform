# Cost Management

## 1. Architecture

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    subgraph Sources["Cost Sources"]
        A1[Cloud Bills]
        A2[API Usage]
        A3[Storage]
        A4[Compute]
    end

    subgraph Ingestion["Ingestion Layer"]
        B1[Cost Collector]
        B2[Event Stream]
        B3[Usage Meter]
    end

    subgraph Core["Cost Engine"]
        C1[Cost Aggregator]
        C2[Allocation Engine]
        C3[Anomaly Detector]
        C4[Forecast Model]
    end

    subgraph Output["Output Layer"]
        D1[Budget Alerts]
        D2[Cost Reports]
        D3[Optimization Tips]
        D4[Dashboards]
    end

    A1 & A2 & A3 & A4 --> B1
    B1 --> B2 --> B3 --> C1
    C1 --> C2 & C3 & C4
    C2 --> D1 & D2
    C3 --> D1 & D3
    C4 --> D2 & D4
```

## 2. Cost Tracking

- **Real-time metering**: Usage events streamed via Kafka; costs computed per transaction.
- **Tagging strategy**: Every resource tagged with `project`, `environment`, `team`, `service`.
- **Granularity**: Per-request, per-endpoint, per-model, per-tenant.
- **Storage**: TimescaleDB for time-series cost data; 90-day hot retention, 2-year cold.
- **Reconciliation**: Nightly job matches cloud invoices vs. tracked usage; drift >2% triggers alert.

## 3. Cost Allocation

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    subgraph Inputs["Allocation Inputs"]
        E1[Raw Costs]
        E2[Shared Resources]
        E3[Tag Metadata]
    end

    subgraph Rules["Allocation Rules"]
        F1[Direct 1:1]
        F2[Proportional]
        F3[Fixed Split]
        F4[Custom Formula]
    end

    subgraph Targets["Cost Centers"]
        G1[Team A]
        G2[Team B]
        G3[Platform]
        G4[Overhead]
    end

    E1 & E2 & E3 --> F1 & F2 & F3 & F4
    F1 & F2 & F3 & F4 --> G1 & G2 & G3 & G4
```

- **Direct costs**: Mapped 1:1 to cost center via tags.
- **Shared resources**: Distributed proportionally by usage share.
- **Unallocated**: Flagged daily; auto-assigned to platform overhead after 7 days.
- **Showback**: Monthly per-team cost report with trend and variance.

## 4. Cost Optimization

- **Idle resource detection**: Resources with <5% utilization for 7 days flagged for downsizing.
- **Spot/preemptible**: Non-critical workloads auto-migrated to spot instances.
- **Model routing**: Route requests to cheapest model meeting quality threshold.
- **Caching**: Semantic cache reduces redundant LLM calls; hit-rate target >30%.
- **Right-sizing**: Weekly recommendation engine suggests instance/type changes.
- **Anomaly detection**: 3-sigma rule on daily spend; alerts to team Slack channel.

## 5. Budget Management

```mermaid
%%{init: {'theme': 'dark'}}%%
stateDiagram-v2
    [*] --> Active: Budget Created
    Active --> Warning: Spend >= 80%
    Warning --> Critical: Spend >= 95%
    Critical --> Exceeded: Spend >= 100%
    Warning --> Active: Spend < 80%
    Critical --> Warning: Spend < 95%
    Exceeded --> [*]: Budget Reset
    Active --> [*]: Budget Closed
```

- **Budget types**: Monthly team budgets, quarterly project budgets, annual platform budget.
- **Enforcement**: Soft limit at 80% (alert), hard limit at 100% (throttle non-critical).
- **Forecasting**: Linear regression on trailing 30-day spend; projects month-end total.
- **Approval flow**: Budget increases require manager + finance sign-off via workflow.
- **Multi-currency**: All costs normalized to USD using daily FX rates.
