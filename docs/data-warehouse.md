# APEX-OS Data Warehouse

## 1. Architecture

```mermaid
graph TB
    subgraph Sources["Source Systems"]
        A1[(PostgreSQL<br/>OLTP)]
        A2[(MongoDB<br/>Events)]
        A3[(Stripe API)]
        A4[(Kafka<br/>Streams)]
    end

    subgraph Ingestion["Ingestion Layer"]
        B1[Airbyte / CDC]
        B2[Kafka Connect]
        B3[dbt Seed]
    end

    subgraph Storage["Storage Layer"]
        C1[(S3 Data Lake<br/>Parquet)]
        C2[(Snowflake<br/>Warehouse)]
    end

    subgraph Transform["Transform Layer"]
        D1[dbt Models]
        D2[Great Expectations]
    end

    subgraph Serving["Serving Layer"]
        E1[Metabase / BI]
        E2[Reverse ETL]
        E3[ML Feature Store]
    end

    A1 --> B1
    A2 --> B2
    A3 --> B1
    A4 --> B2
    B1 --> C1
    B2 --> C1
    B3 --> C2
    C1 --> D1
    C2 --> D1
    D1 --> D2
    D2 --> E1
    D2 --> E2
    D2 --> E3

    classDef source fill:#1a1a2e,stroke:#e94560,color:#fff
    classDef ingest fill:#16213e,stroke:#0f3460,color:#fff
    classDef store fill:#1a1a2e,stroke:#533483,color:#fff
    classDef transform fill:#16213e,stroke:#e94560,color:#fff
    classDef serve fill:#1a1a2e,stroke:#0f3460,color:#fff

    class A1,A2,A3,A4 source
    class B1,B2,B3 ingest
    class C1,C2 store
    class D1,D2 transform
    class E1,E2,E3 serve
```

---

## 2. ETL Pipeline

### 2.1 Batch Pipeline (Nightly)

```mermaid
flowchart LR
    A[Extract<br/>Airbyte] --> B[Land<br/>S3 Raw]
    B --> C[Validate<br/>GE Suites]
    C --> D[Transform<br/>dbt]
    D --> E[Load<br/>Snowflake]
    E --> F[Post-run<br/>Tests]

    classDef step fill:#16213e,stroke:#e94560,color:#fff
    class A,B,C,D,E,F step
```

### 2.2 Streaming Pipeline (Real-time)

```mermaid
flowchart LR
    A[Kafka] --> B[Flink / ksqlDB]
    B --> C[S3 Iceberg]
    C --> D[Snowflake<br/>Streaming Ingestion]

    classDef step fill:#16213e,stroke:#533483,color:#fff
    class A,B,C,D step
```

### 2.3 Pipeline Stages

| Stage | Tool | Schedule | SLA |
|-------|------|----------|-----|
| Extract | Airbyte CDC | Continuous | 5 min lag |
| Land | S3 (Parquet) | Per batch | — |
| Validate | Great Expectations | Per batch | Block on fail |
| Transform | dbt | 02:00 UTC | 04:00 UTC |
| Load | Snowflake | 04:00 UTC | 06:00 UTC |
| Test | dbt tests | 06:00 UTC | 06:30 UTC |

---

## 3. Data Modeling

### 3.1 Layered Architecture

```mermaid
graph TD
    subgraph Bronze["Bronze — Raw"]
        BR1[raw_orders]
        BR2[raw_customers]
        BR3[raw_payments]
    end

    subgraph Silver["Silver — Cleansed"]
        SV1[stg_orders]
        SV2[stg_customers]
        SV3[stg_payments]
    end

    subgraph Gold["Gold — Business"]
        GD1[fct_orders]
        GD2[dim_customers]
        GD3[dim_products]
        GD4[mart_revenue_daily]
    end

    BR1 --> SV1
    BR2 --> SV2
    BR3 --> SV3
    SV1 --> GD1
    SV2 --> GD2
    SV3 --> GD1
    SV3 --> GD4
    GD1 --> GD4

    classDef bronze fill:#1a1a2e,stroke:#cd7f32,color:#fff
    classDef silver fill:#16213e,stroke:#c0c0c0,color:#fff
    classDef gold fill:#1a1a2e,stroke:#ffd700,color:#fff

    class BR1,BR2,BR3 bronze
    class SV1,SV2,SV3 silver
    class GD1,GD2,GD3,GD4 gold
```

### 3.2 Dimensional Model (Star Schema)

```mermaid
erDiagram
    FACT_ORDERS {
        order_id PK
        customer_id FK
        product_id FK
        date_id FK
        quantity INT
        unit_price DECIMAL
        discount DECIMAL
        total_amount DECIMAL
    }
    DIM_CUSTOMERS {
        customer_id PK
        name STRING
        email STRING
        segment STRING
        created_at TIMESTAMP
    }
    DIM_PRODUCTS {
        product_id PK
        name STRING
        category STRING
        price DECIMAL
    }
    DIM_DATE {
        date_id PK
        date DATE
        week INT
        month INT
        quarter INT
        year INT
    }
    FACT_ORDERS ||--|| DIM_CUSTOMERS : "placed by"
    FACT_ORDERS ||--|| DIM_PRODUCTS : "contains"
    FACT_ORDERS ||--|| DIM_DATE : "on date"
```

### 3.3 Naming Conventions

| Layer | Prefix | Example |
|-------|--------|---------|
| Bronze | `raw_` | `raw_orders` |
| Silver | `stg_` | `stg_orders` |
| Gold Fact | `fct_` | `fct_orders` |
| Gold Dim | `dim_` | `dim_customers` |
| Gold Mart | `mart_` | `mart_revenue_daily` |

---

## 4. Data Governance

### 4.1 Access Control

```mermaid
graph LR
    subgraph Roles["RBAC Roles"]
        R1[analyst_ro]
        R2[analyst_rw]
        R3[engineer_admin]
    end

    subgraph Schemas["Snowflake Schemas"]
        S1[bronze]
        S2[silver]
        S3[gold]
        S4[analytics]
    end

    R1 -->|SELECT| S3
    R1 -->|SELECT| S4
    R2 -->|SELECT, INSERT| S2
    R2 -->|SELECT| S3
    R3 -->|ALL| S1
    R3 -->|ALL| S2
    R3 -->|ALL| S3

    classDef role fill:#16213e,stroke:#e94560,color:#fff
    classDef schema fill:#1a1a2e,stroke:#533483,color:#fff

    class R1,R2,R3 role
    class S1,S2,S3,S4 schema
```

### 4.2 Data Quality Framework

| Check Type | Tool | Scope | Action |
|------------|------|-------|--------|
| Schema | dbt | All models | Block pipeline |
| Nulls | GE | Critical columns | Warn / Block |
| Uniqueness | dbt | PKs | Block |
| Referential | dbt | FKs | Block |
| Freshness | GE | Source tables | Alert |
| Volume | GE | Daily aggregates | Alert |
| Custom | GE | Business rules | Block |

### 4.3 PII Handling

- **Classification**: Automated scanning via `presidio` + manual tagging
- **Masking**: Dynamic data masking in Snowflake for `analyst_ro`
- **Retention**: 7-year financial, 2-year behavioral, 90-day raw events
- **Right to deletion**: Automated purge workflow triggered by API

### 4.4 Lineage

```mermaid
graph LR
    A[raw_orders] --> B[stg_orders]
    B --> C[fct_orders]
    C --> D[mart_revenue_daily]
    D --> E[Metabase Dashboard]

    classDef node fill:#16213e,stroke:#0f3460,color:#fff
    class A,B,C,D,E node
```

---

## 5. Analytics

### 5.1 BI & Reporting

```mermaid
graph TB
    subgraph Consumers["Analytics Consumers"]
        C1[Metabase<br/>Self-serve BI]
        C2[Executive<br/>Dashboards]
        C3[Embedded<br/>Analytics]
        C4[Data Science<br/>Notebooks]
    end

    subgraph Marts["Analytics Marts"]
        M1[mart_revenue_daily]
        M2[mart_customer_ltv]
        M3[mart_product_performance]
        M4[mart_cohort_analysis]
    end

    M1 --> C1
    M1 --> C2
    M2 --> C1
    M2 --> C4
    M3 --> C1
    M3 --> C3
    M4 --> C4

    classDef consumer fill:#1a1a2e,stroke:#e94560,color:#fff
    classDef mart fill:#16213e,stroke:#533483,color:#fff

    class C1,C2,C3,C4 consumer
    class M1,M2,M3,M4 mart
```

### 5.2 Key Metrics

| Domain | Metric | Grain | Refresh |
|--------|--------|-------|---------|
| Revenue | MRR / ARR | Daily | 06:00 UTC |
| Revenue | ARPU | Monthly | 06:00 UTC |
| Customers | LTV | Cohort | Daily |
| Customers | Churn Rate | Weekly | 06:00 UTC |
| Product | NPS | Monthly | 06:00 UTC |
| Product | Conversion Funnel | Daily | 06:00 UTC |

### 5.3 Reverse ETL

```mermaid
flowchart LR
    A[Snowflake<br/>Gold] --> B[Census / Hightouch]
    B --> C[HubSpot]
    B --> D[Stripe]
    B --> E[Slack]

    classDef dw fill:#1a1a2e,stroke:#533483,color:#fff
    classDef tool fill:#16213e,stroke:#e94560,color:#fff

    class A dw
    class B,C,D,E tool
```

### 5.4 ML Feature Store

- **Store**: Snowflake + Feast
- **Features**: Customer embeddings, product affinity, session aggregates
- **Serving**: Online (Redis) for real-time inference, Offline (Snowflake) for training
- **Versioning**: dbt + MLflow integration
