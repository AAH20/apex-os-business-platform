# Continuous Business Intelligence Research

## 1. Platform Comparison

| Dimension | Looker | Tableau | Power BI | Sisense | ThoughtSpot |
|---|---|---|---|---|---|
| **Vendor** | Google Cloud | Salesforce | Microsoft | Perforce | ThoughtSpot Inc. |
| **Core Model** | LookML semantic layer | VizQL + Hyper engine | DAX + Composite models | ElastiCube in-memory | Search + SpotIQ AI |
| **Real-time** | Live connection to BigQuery/DW | Live connections + WDC | Streaming datasets + DirectQuery | Live models + ElastiCube refresh | Liveboards + in-memory engine |
| **Data Volume** | Unlimited (pushdown to DW) | Hyper extracts (billions of rows) | 200K rows push; unlimited DQ | 1B records per ElastiCube | Billions of rows in-memory |
| **Streaming Native** | No (DW-dependent) | No (live query only) | Yes (REST API, ASA, PubNub) | No (live connection) | No (in-memory cache) |
| **AI/ML** | Gemini-powered agents | Einstein Copilot | Copilot + AutoML | Fusion AI (NL, anomaly) | SpotIQ automated insights |
| **Embedding** | iframe + JS SDK + Extensions | Extensions API + Embed SDK | Power BI Embedded | Compose SDK (REST/GraphQL) | Liveboard embed + SDK |
| **Governance** | Git-versioned LookML | Tableau Catalog | Microsoft Purview | Row-level security | Object/row/column security |
| **Deployment** | SaaS (GCP) | SaaS / On-prem | SaaS / Fabric | Cloud / On-prem / K8s | SaaS / On-prem |
| **Pricing** | Custom (platform + user) | Creator/Explorer/Viewer | Pro/PPU/Fabric | Custom (workspace-based) | Custom (user-based) |
| **Best For** | Governed semantic analytics | Visual exploration | Microsoft ecosystem | Embedded SaaS analytics | Search-driven self-service |

### Key Differentiators

- **Looker**: LookML modeling language provides a Git-versioned, code-first semantic layer. Queries push down to the underlying DW (BigQuery, Snowflake, Redshift). No data movement into the BI layer.
- **Tableau**: VizQL compiles visualizations into native queries. Hyper engine provides 10-20x columnar compression. Live connections to Databricks SQL, Snowflake, BigQuery with full analytical functionality.
- **Power BI**: Native streaming datasets (REST API, Azure Stream Analytics, PubNub). Fabric Real-Time Intelligence (Eventstreams, Eventhouse, KQL). DirectQuery with automatic page refresh up to 1-second intervals.
- **Sisense**: ElastiCube columnar in-memory engine with In-Chip (FPGA) acceleration. Live models for real-time DW queries. Strong multi-tenant embedded analytics with white-labeling.
- **ThoughtSpot**: Search-driven analytics with SpotIQ AI engine. In-memory calculation engine analyzes billions of rows in seconds. Liveboards with AI-generated insights and anomaly detection.

---

## 2. Real-Time BI Architecture

```mermaid
graph TB
    subgraph Sources["Data Sources"]
        IOT[IoT / Sensors]
        WEB[Web / Mobile Apps]
        DB[(Operational DB)]
        API[External APIs]
        LOG[Log Streams]
    end
    subgraph Ingestion["Ingestion Layer"]
        KAFKA[Apache Kafka / Kinesis]
        EH[Event Hubs / IoT Hub]
        CDC[CDC Debezium]
    end
    subgraph Processing["Stream Processing"]
        FLINK[Apache Flink / Spark Streaming]
        ASA[Azure Stream Analytics]
        KSQL[ksqlDB / Kafka Streams]
    end
    subgraph Storage["Serving Storage"]
        OLAP[ClickHouse / Druid / Pinot]
        DW[(Cloud Data Warehouse)]
        CACHE[Redis / In-Memory Cache]
        MV[Materialized Views]
    end
    subgraph BI["BI Platform Layer"]
        LOOKER[Looker]
        TABLEAU[Tableau]
        POWERBI[Power BI]
        SISENSE[Sisense]
        THOUGHTSPOT[ThoughtSpot]
    end
    subgraph Delivery["Delivery Layer"]
        DASH[Real-Time Dashboards]
        ALERT[Alerts / Notifications]
        EMBED[Embedded Analytics]
        API_OUT[API / Webhooks]
    end
    IOT --> KAFKA
    WEB --> KAFKA
    DB --> CDC
    API --> EH
    LOG --> KAFKA
    KAFKA --> FLINK
    KAFKA --> KSQL
    EH --> ASA
    CDC --> KAFKA
    FLINK --> OLAP
    FLINK --> MV
    KSQL --> OLAP
    ASA --> POWERBI
    OLAP --> CACHE
    MV --> DW
    OLAP --> LOOKER
    DW --> LOOKER
    DW --> TABLEAU
    DW --> SISENSE
    CACHE --> THOUGHTSPOT
    DW --> THOUGHTSPOT
    LOOKER --> DASH
    TABLEAU --> DASH
    POWERBI --> DASH
    SISENSE --> EMBED
    THOUGHTSPOT --> DASH
    FLINK --> ALERT
    ASA --> ALERT
    THOUGHTSPOT --> ALERT
    LOOKER --> API_OUT
    SISENSE --> API_OUT
    style Sources fill:#1a1a2e,stroke:#e94560,color:#fff
    style Ingestion fill:#16213e,stroke:#0f3460,color:#fff
    style Processing fill:#1a1a2e,stroke:#e94560,color:#fff
    style Storage fill:#16213e,stroke:#0f3460,color:#fff
    style BI fill:#0f3460,stroke:#533483,color:#fff
    style Delivery fill:#1a1a2e,stroke:#e94560,color:#fff
```

---

## 3. Streaming Data Patterns

### 3.1 Lambda Architecture (Batch + Speed)

```mermaid
graph LR
    subgraph Speed["Speed Layer (Hot Path)"]
        S1[Stream Ingest] --> S2[Stream Processor]
        S2 --> S3[Real-Time View]
    end
    subgraph Batch["Batch Layer (Cold Path)"]
        B1[Raw Data Lake] --> B2[Batch Processing]
        B2 --> B3[Batch View]
    end
    subgraph Serving["Serving Layer"]
        SV[Merge / Query Engine]
    end
    S3 --> SV
    B3 --> SV
    SV --> CLIENT[BI Dashboard]
    style Speed fill:#1a1a2e,stroke:#e94560,color:#fff
    style Batch fill:#16213e,stroke:#0f3460,color:#fff
    style Serving fill:#0f3460,stroke:#533483,color:#fff
```

### 3.2 Kappa Architecture (Stream-Only)

```mermaid
graph LR
    SRC[Event Sources] --> LOG[(Unified Log / Kafka)]
    LOG --> PROC[Stream Processor]
    PROC --> VIEW[Real-Time Materialized View]
    VIEW --> DASH[BI Dashboard]
    LOG -.->|Replay| PROC
    style SRC fill:#1a1a2e,stroke:#e94560,color:#fff
    style LOG fill:#16213e,stroke:#0f3460,color:#fff
    style PROC fill:#1a1a2e,stroke:#e94560,color:#fff
    style VIEW fill:#0f3460,stroke:#533483,color:#fff
    style DASH fill:#16213e,stroke:#0f3460,color:#fff
```

### 3.3 Key Streaming Patterns

| Pattern | Description | Use Case |
|---|---|---|
| **CDC** | Stream DB changes via log-based capture | Keep BI in sync with operational DB |
| **Materialized Views** | Pre-computed rollups updated on insert | Sub-second dashboard queries |
| **Fan-Out** | One stream consumed by multiple processors | Simultaneous analytics + alerting |
| **Stream-Table Join** | Enrich events with static reference data | Add customer/product dimensions |
| **Log Compaction** | Keep only latest value per key | Current state dashboards |
| **Windowed Aggregation** | Tumbling/hopping/session windows | Time-series KPIs |
| **Push Dataset** | REST API streaming to BI service | Power BI real-time tiles |

### 3.4 Processing Semantics

- **Event Time**: When the event actually occurred (source timestamp)
- **Processing Time**: When the system processes the event
- **Watermarks**: Progress indicators for event-time completeness
- **Late Data**: Events arriving after watermark — define allowed lateness
- **Corrections**: Updates/reversals that change prior results

---

## 4. Dashboard Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        UI[Dashboard UI]
        WS[WebSocket / SSE Client]
        POLL[Polling Fallback]
    end
    subgraph Edge["Edge / API Gateway"]
        AUTH[Auth / RBAC]
        RATE[Rate Limiter]
        CACHE[CDN / Edge Cache]
    end
    subgraph App["Application Layer"]
        QUERY[Query Engine]
        AGG[Aggregation Service]
        ALERT_SVC[Alert Engine]
        REAL[Real-Time Service]
    end
    subgraph Data["Data Layer"]
        HOT[Hot Store - Redis/Memory]
        WARM[Warm Store - OLAP]
        COLD[Cold Store - Data Lake]
    end
    UI --> WS
    UI --> POLL
    WS --> AUTH
    POLL --> AUTH
    AUTH --> RATE
    RATE --> CACHE
    CACHE --> QUERY
    CACHE --> REAL
    QUERY --> AGG
    AGG --> HOT
    AGG --> WARM
    REAL --> HOT
    HOT --> WARM
    WARM --> COLD
    ALERT_SVC --> HOT
    style Client fill:#1a1a2e,stroke:#e94560,color:#fff
    style Edge fill:#16213e,stroke:#0f3460,color:#fff
    style App fill:#0f3460,stroke:#533483,color:#fff
    style Data fill:#1a1a2e,stroke:#e94560,color:#fff
```

### Dashboard Freshness States

| State | Indicator | User Action |
|---|---|---|
| **Provisional** | Window still accepting data | Wait for decision-safe |
| **Decision-Safe** | Completeness rule passed | Safe to act |
| **Stale** | Data age exceeds contract | Refresh / investigate |
| **Partial** | Source/partition missing | Check source health |
| **Revised** | Late event changed prior value | Review change |
| **Disconnected** | Live delivery stopped | Auto-reconnect |

### Performance Tiers

| Tier | Latency | Architecture |
|---|---|---|
| **Sub-second** | < 1s | WebSocket push + in-memory pre-aggregation |
| **Near-real-time** | 1-30s | SSE + materialized views (5-10s windows) |
| **Periodic** | 1-5 min | Polling API + query cache (60s TTL) |

---

## 5. Integration Requirements

### 5.1 Data Source Connectivity

| Source Type | Looker | Tableau | Power BI | Sisense | ThoughtSpot |
|---|---|---|---|---|---|
| Cloud DW (BigQuery, Snowflake, Redshift) | Native | Native | Native | Native | Native |
| RDBMS (Postgres, MySQL, SQL Server) | Native | Native | Native | Native | Native |
| Streaming (Kafka, Kinesis) | Via DW | Via DW | Native (ASA) | Via DW | Via DW |
| APIs / REST | Action Hub | WDC | Power Query | REST connector | Via DW |
| Files (CSV, Excel) | Limited | Native | Native | Native | Limited |
| SaaS (Salesforce, etc.) | Native | Native | Native | Native | Native |

### 5.2 Authentication & Security

- **SSO/SAML**: All five platforms support enterprise SSO
- **OAuth 2.0**: API access and embedded analytics
- **Row-Level Security (RLS)**: Looker (user attributes), Tableau (user filters), Power BI (RLS roles), Sisense (data security), ThoughtSpot (row-level permissions)
- **Column-Level Security**: ThoughtSpot native; others via data model design
- **Multi-Tenancy**: Sisense (strongest), Looker (Git branches), Power BI (workspaces)

### 5.3 API & Embedding

| Capability | Looker | Tableau | Power BI | Sisense | ThoughtSpot |
|---|---|---|---|---|---|
| REST API | Full | Full | Full | Full + GraphQL | Full |
| JavaScript SDK | Embed SDK | Embed SDK | JavaScript API | Compose SDK | Liveboard SDK |
| iframe Embed | Yes | Yes | Yes | Yes | Yes |
| Custom Viz | Extensions API | Extensions API | Custom Visuals | Plugin API | Developer Tools |
| Webhooks | Action Hub | Webhooks | Data Activator | Webhooks | Webhooks |

### 5.4 Operational Requirements

| Requirement | Implementation |
|---|---|
| **High Availability** | Multi-node clustering, auto-failover, health checks |
| **Scalability** | Horizontal scaling of stream processors and query nodes |
| **Monitoring** | Consumer lag, watermark delay, query latency, freshness SLA |
| **Backpressure** | Bounded queues, load shedding, auto-scaling consumers |
| **Idempotency** | Event IDs, deduplication, exactly-once processing |
| **Reconciliation** | Periodic batch correction against authoritative source |
| **Disaster Recovery** | Stream replay from log, checkpoint restore, multi-region |
| **Data Quality** | Schema validation, constraint enforcement, DLQ for bad records |

### 5.5 Technology Stack Reference

| Layer | Technologies |
|---|---|
| **Ingestion** | Kafka, Kinesis, Event Hubs, IoT Hub, Debezium CDC |
| **Processing** | Flink, Spark Streaming, ksqlDB, Stream Analytics |
| **Serving** | ClickHouse, Druid, Pinot, TimescaleDB, Redis |
| **Warehouse** | BigQuery, Snowflake, Redshift, Databricks |
| **Orchestration** | Airflow, Dagster, Prefect, Fabric Data Factory |
| **BI** | Looker, Tableau, Power BI, Sisense, ThoughtSpot |
| **Delivery** | WebSocket, SSE, REST API, GraphQL |

---

## Summary

Continuous BI requires a streaming-first architecture with pre-aggregation, low-latency serving, and push-based delivery. The choice of BI platform depends on the existing data stack, governance needs, and embedding requirements. Power BI leads in native streaming; Looker leads in governed semantics; Tableau leads in visual exploration; Sisense leads in embedded analytics; ThoughtSpot leads in AI-driven search.
