# Reporting

## 1. Reporting Architecture

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    subgraph Sources
        DB[(PostgreSQL)]
        API[REST API]
        EXT[External Feeds]
    end

    subgraph Pipeline
        ING[Ingestion Layer]
        PROC[Processing Engine]
        CACHE[(Cache Store)]
    end

    subgraph Reporting
        BUILDER[Report Builder]
        SCHED[Scheduler]
        RENDER[Render Engine]
    end

    subgraph Distribution
        EMAIL[Email]
        SLACK[Slack]
        WEB[Webhooks]
        EXPORT[File Export]
    end

    DB --> ING
    API --> ING
    EXT --> ING
    ING --> PROC
    PROC --> CACHE
    CACHE --> BUILDER
    BUILDER --> RENDER
    SCHED --> BUILDER
    RENDER --> EMAIL
    RENDER --> SLACK
    RENDER --> WEB
    RENDER --> EXPORT
```

## 2. Report Types

| Type | Description | Data Source | Refresh |
|------|-------------|-------------|---------|
| **Summary** | High-level KPIs and aggregates | Cached | Hourly |
| **Detail** | Row-level transactional data | Live DB | On-demand |
| **Trend** | Time-series with comparisons | Cached | Daily |
| **Ad-hoc** | User-defined queries | Live DB | On-demand |
| **Scheduled** | Recurring distribution reports | Cached | Cron-based |
| **Real-time** | Live dashboards and alerts | Streaming | Continuous |

### Report Type Selection

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    START[Report Request] --> Q1{Need live data?}
    Q1 -->|Yes| Q2{Row-level detail?}
    Q1 -->|No| Q3{Time-series?}
    Q2 -->|Yes| DETAIL[Detail Report]
    Q2 -->|No| ADHOC[Ad-hoc Report]
    Q3 -->|Yes| TREND[Trend Report]
    Q3 -->|No| Q4{Recurring?}
    Q4 -->|Yes| SCHEDULED[Scheduled Report]
    Q4 -->|No| SUMMARY[Summary Report]
```

## 3. Report Builder

The Report Builder provides a programmatic and UI-driven interface for constructing reports.

### Builder Pipeline

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    A[Define Source] --> B[Select Fields]
    B --> C[Apply Filters]
    C --> D[Add Aggregations]
    D --> E[Configure Formatting]
    E --> F[Preview]
    F --> G{Satisfactory?}
    G -->|No| B
    G -->|Yes| H[Save / Schedule]
```

### Builder API

```python
from apex.reporting import ReportBuilder

report = (
    ReportBuilder()
    .source("transactions")
    .fields(["id", "amount", "date", "status"])
    .filter(status="completed", date__gte="2026-01-01")
    .aggregate(total="sum(amount)", count="count(id)")
    .format("pdf")
    .schedule(cron="0 8 * * *")
    .distribute(["email:team@example.com", "slack:#reports"])
    .build()
)
```

### Builder Components

- **Source Selector** — Choose data source (table, view, API endpoint)
- **Field Picker** — Select and alias columns
- **Filter Engine** — Apply WHERE clauses with AND/OR logic
- **Aggregation** — SUM, COUNT, AVG, MIN, MAX, GROUP BY
- **Formatting** — Column widths, headers, number formats
- **Visualization** — Charts, tables, pivot grids

## 4. Report Scheduling

### Schedule Configuration

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    CRON[Cron Expression] --> PARSE[Parse Schedule]
    PARSE --> VALID{Valid?}
    VALID -->|No| ERR[Error]
    VALID -->|Yes| QUEUE[Add to Queue]
    QUEUE --> TRIGGER[Trigger at Time]
    TRIGGER --> EXEC[Execute Report]
    EXEC --> DIST[Distribute Results]
```

### Schedule Types

| Type | Cron Pattern | Use Case |
|------|-------------|----------|
| Hourly | `0 * * * *` | Operational dashboards |
| Daily | `0 8 * * *` | Morning summaries |
| Weekly | `0 8 * * 1` | Monday week-in-review |
| Monthly | `0 8 1 * *` | Month-end reports |
| Custom | User-defined | Special schedules |

### Scheduler Behavior

- **Timezone-aware** — All schedules respect the organization timezone
- **Retry logic** — Failed reports retry up to 3 times with exponential backoff
- **Concurrency limit** — Max 10 concurrent report executions
- **Missed run handling** — Catch-up execution for missed schedules within 24h

## 5. Report Distribution

### Distribution Channels

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    R[Report Output] --> C1[Email]
    R --> C2[Slack]
    R --> C3[Webhook]
    R --> C4[File Storage]
    R --> C5[In-app]

    C1 --> F1[PDF / CSV Attachment]
    C2 --> F2[Message + Link]
    C3 --> F3[JSON Payload]
    C4 --> F4[S3 / GCS / Local]
    C5 --> F5[Dashboard Widget]
```

### Distribution Configuration

```yaml
distributions:
  - type: email
    recipients: ["team@example.com"]
    format: pdf
    subject: "Daily Report - {date}"

  - type: slack
    channel: "#reports"
    format: link
    message: "Report ready: {report_url}"

  - type: webhook
    url: "https://api.example.com/reports"
    format: json
    headers:
      Authorization: "Bearer ${WEBHOOK_TOKEN}"

  - type: s3
    bucket: "reports-bucket"
    prefix: "daily/{date}/"
    format: csv
```

### Delivery Guarantees

- **At-least-once delivery** — Failed deliveries are retried
- **Idempotency** — Duplicate deliveries are suppressed via dedup keys
- **Access control** — Recipients only see reports they are authorized for
- **Audit trail** — All distribution events are logged with timestamps and status
