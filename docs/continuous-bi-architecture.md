# Continuous BI Platform Architecture

## 1. Real-Time Dashboard Architecture

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1e3a5f', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#4a9eff', 'lineColor': '#4a9eff', 'secondaryColor': '#2d2d2d', 'tertiaryColor': '#1a1a2e', 'background': '#0d1117', 'mainBkg': '#1e3a5f', 'secondBkg': '#2d2d2d', 'textColor': '#e0e0e0', 'fontSize': '14px'}}}%%
flowchart LR
    subgraph Sources["Data Sources"]
        DB[(Operational DB)]
        API[API Events]
        LOG[Log Streams]
    end

    subgraph Ingestion["Ingestion Layer"]
        KC[Kafka Connect]
        CDC[CDC Debezium]
    end

    subgraph Processing["Stream Processing"]
        KS[Kafka Streams]
        FLINK[Apache Flink]
    end

    subgraph Serving["Serving Layer"]
        WS[WebSocket Server]
        SSE[SSE Gateway]
        PUSH[Push Service]
    end

    subgraph Client["Client Layer"]
        UI[React Dashboard]
        MOB[Mobile App]
        EMB[Embedded Widgets]
    end

    DB --> CDC
    API --> KC
    LOG --> KC
    CDC --> KS
    KC --> KS
    KS --> FLINK
    FLINK --> WS
    FLINK --> SSE
    FLINK --> PUSH
    WS <--> UI
    SSE <--> MOB
    PUSH --> EMB
```

## 2. Streaming ETL Architecture

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1e3a5f', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#4a9eff', 'lineColor': '#4a9eff', 'secondaryColor': '#2d2d2d', 'tertiaryColor': '#1a1a2e', 'background': '#0d1117', 'mainBkg': '#1e3a5f', 'secondBkg': '#2d2d2d', 'textColor': '#e0e0e0', 'fontSize': '14px'}}}%%
flowchart TD
    subgraph Extract["Extract Layer"]
        SRC1[(PostgreSQL)]
        SRC2[(MongoDB)]
        SRC3[S3 Files]
        SRC4[External APIs]
        CDC[Debezium CDC]
        BATCH[Batch Crawler]
    end

    subgraph Queue["Message Queue"]
        K1[raw-events]
        K2[cdc-changes]
        K3[file-drops]
    end

    subgraph Transform["Transform Layer"]
        VAL[Data Validator]
        ENR[Enricher]
        AGG[Aggregator]
        DEDUP[Deduplicator]
        NORM[Normalizer]
    end

    subgraph Load["Load Layer"]
        DW[(Data Warehouse)]
        OLAP[(OLAP Cube)]
        IDX[(Search Index)]
    end

    SRC1 --> CDC
    SRC2 --> CDC
    SRC3 --> BATCH
    SRC4 --> BATCH
    CDC --> K2
    BATCH --> K1
    BATCH --> K3
    K1 --> VAL
    K2 --> VAL
    K3 --> VAL
    VAL --> DEDUP
    DEDUP --> NORM
    NORM --> ENR
    ENR --> AGG
    AGG --> DW
    AGG --> OLAP
    AGG --> IDX
```

## 3. Query Engine Architecture

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1e3a5f', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#4a9eff', 'lineColor': '#4a9eff', 'secondaryColor': '#2d2d2d', 'tertiaryColor': '#1a1a2e', 'background': '#0d1117', 'mainBkg': '#1e3a5f', 'secondBkg': '#2d2d2d', 'textColor': '#e0e0e0', 'fontSize': '14px'}}}%%
flowchart TD
    subgraph API["Query API Layer"]
        GW[API Gateway]
        AUTH[Auth Middleware]
        RATE[Rate Limiter]
        QP[Query Parser]
    end

    subgraph Engine["Query Engine"]
        PLANNER[Query Planner]
        OPT[Optimizer]
        EXEC[Executor]
        MERGE[Result Merger]
    end

    subgraph Storage["Storage Layer"]
        CACHE[(Redis Cache)]
        OLAP[(ClickHouse)]
        DRUID[(Druid)]
        ES[(Elasticsearch)]
    end

    subgraph Compute["Compute Layer"]
        PRE[Pre-aggregator]
        MVIEW[Materialized Views]
        ADHOC[Ad-hoc Compute]
    end

    GW --> AUTH
    AUTH --> RATE
    RATE --> QP
    QP --> PLANNER
    PLANNER --> OPT
    OPT --> EXEC
    EXEC --> CACHE
    CACHE -->|miss| OLAP
    CACHE -->|miss| DRUID
    CACHE -->|miss| ES
    OLAP --> MERGE
    DRUID --> MERGE
    ES --> MERGE
    PRE --> MVIEW
    MVIEW --> OLAP
    ADHOC --> DRUID
    MERGE --> GW
```

## 4. Caching Architecture

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1e3a5f', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#4a9eff', 'lineColor': '#4a9eff', 'secondaryColor': '#2d2d2d', 'tertiaryColor': '#1a1a2e', 'background': '#0d1117', 'mainBkg': '#1e3a5f', 'secondBkg': '#2d2d2d', 'textColor': '#e0e0e0', 'fontSize': '14px'}}}%%
flowchart LR
    subgraph Client["Client Tier"]
        BROWSER[Browser Cache]
        CDN[CDN Edge Cache]
    end

    subgraph App["Application Tier"]
        L1[L1 In-Memory - Caffeine]
        L2[L2 Distributed - Redis]
        L3[L3 Persistent - Disk]
    end

    subgraph Data["Data Tier"]
        L4[L4 Result Cache - Redis Cluster]
        L5[L5 Materialized - ClickHouse]
    end

    subgraph Invalidation["Invalidation"]
        PUB[Pub/Sub - Kafka]
        EVICT[Evictor Service]
        TTL[TTL Manager]
    end

    BROWSER --> CDN
    CDN --> L1
    L1 -->|miss| L2
    L2 -->|miss| L3
    L3 -->|miss| L4
    L4 -->|miss| L5
    PUB --> EVICT
    EVICT --> L1
    EVICT --> L2
    EVICT --> L4
    TTL --> L2
    TTL --> L4
```

## 5. Multi-Tenant Architecture

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': {'primaryColor': '#1e3a5f', 'primaryTextColor': '#e0e0e0', 'primaryBorderColor': '#4a9eff', 'lineColor': '#4a9eff', 'secondaryColor': '#2d2d2d', 'tertiaryColor': '#1a1a2e', 'background': '#0d1117', 'mainBkg': '#1e3a5f', 'secondBkg': '#2d2d2d', 'textColor': '#e0e0e0', 'fontSize': '14px'}}}%%
flowchart TD
    subgraph Edge["Edge Layer"]
        LB[Load Balancer]
        GW[API Gateway]
    end

    subgraph Tenant["Tenant Resolution"]
        RES[Tenant Resolver]
        CTX[Tenant Context]
        QUOTA[Quota Manager]
    end

    subgraph Isolation["Isolation Layer"]
        subgraph Pool["Shared Pool - Row Level"]
            S1[Schema: shared_t1]
            S2[Schema: shared_t2]
            S3[Schema: shared_t3]
        end
        subgraph Dedicated["Dedicated Pool"]
            D1[Dedicated DB: tenant_a]
            D2[Dedicated DB: tenant_b]
        end
    end

    subgraph Services["Shared Services"]
        AUTH[Auth Service]
        BILL[Billing Service]
        AUDIT[Audit Service]
        NOTIF[Notification Service]
    end

    subgraph DataPlane["Data Plane"]
        DW[(Shared Warehouse)]
        OLAP[(Shared OLAP)]
        QUEUE[Kafka - Tenant Topics]
    end

    LB --> GW
    GW --> RES
    RES --> CTX
    CTX --> QUOTA
    CTX --> S1
    CTX --> S2
    CTX --> S3
    CTX --> D1
    CTX --> D2
    S1 --> DW
    S2 --> DW
    S3 --> DW
    D1 --> DW
    D2 --> DW
    DW --> OLAP
    CTX --> QUEUE
    GW --> AUTH
    GW --> BILL
    GW --> AUDIT
    GW --> NOTIF
```
