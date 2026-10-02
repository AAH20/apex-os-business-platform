# Big Data Model — APEX-OS Business Platform

## 1. Lakehouse Schema Design

Medallion architecture (Bronze → Silver → Gold) on object storage with Delta Lake / Apache Iceberg.

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    subgraph Sources["Sources"]
        A1[(OLTP DB)]
        A2[Events / IoT]
        A3[Files / S3]
        A4[3rd-party APIs]
    end

    subgraph Bronze["Bronze — Raw"]
        B1[raw_transactions]
        B2[raw_events]
        B3[raw_customers]
    end

    subgraph Silver["Silver — Cleansed"]
        S1[dim_customer]
        S2[dim_product]
        S3[fact_orders]
        S4[fact_events]
    end

    subgraph Gold["Gold — Curated"]
        G1[agg_daily_sales]
        G2[agg_customer_360]
        G3[ml_features]
    end

    A1 --> B1
    A2 --> B2
    A3 --> B3
    A4 --> B3
    B1 --> S3
    B2 --> S4
    B3 --> S1
    B3 --> S2
    S1 --> G2
    S2 --> G1
    S3 --> G1
    S3 --> G2
    S4 --> G3
    S1 --> G3
```

**Table conventions**

| Layer | Format | Partition | Retention |
|-------|--------|-----------|-----------|
| Bronze | Parquet / JSON | `ingestion_date` | 90 days |
| Silver | Delta / Iceberg | `event_date` | 2 years |
| Gold | Delta / Iceberg | `report_date` | 7 years |

---

## 2. Star Schema Patterns

Optimized for BI queries — denormalized dimensions, additive facts.

```mermaid
%%{init: {'theme': 'dark'}}%%
erDiagram
    fact_orders {
        bigint order_id PK
        bigint customer_key FK
        bigint product_key FK
        bigint date_key FK
        bigint store_key FK
        decimal quantity
        decimal unit_price
        decimal discount
        decimal sales_amount
        decimal cost_amount
    }
    dim_customer {
        bigint customer_key PK
        string customer_id
        string name
        string segment
        string region
    }
    dim_product {
        bigint product_key PK
        string sku
        string product_name
        string category
        string brand
    }
    dim_date {
        bigint date_key PK
        date full_date
        int year
        int quarter
        int month
        int day_of_week
    }
    dim_store {
        bigint store_key PK
        string store_id
        string store_name
        string city
        string country
    }
    fact_orders ||--|| dim_customer : "customer_key"
    fact_orders ||--|| dim_product : "product_key"
    fact_orders ||--|| dim_date : "date_key"
    fact_orders ||--|| dim_store : "store_key"
```

**Design rules**
- Surrogate keys (`*_key`) — bigint, monotonically increasing.
- Degenerate dimensions (order_number, ticket_id) stay in the fact.
- Junk dimensions for low-cardinality flags.
- Conformed dimensions shared across fact tables.

---

## 3. Data Vault Patterns

Hub-Link-Satellite for auditability, parallel loading, and source-system independence.

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    subgraph Hubs["Hubs — Business Keys"]
        H_CUST[hub_customer]
        H_PROD[hub_product]
        H_ORDER[hub_order]
    end

    subgraph Links["Links — Relationships"]
        L_ORDER_CUST[link_order_customer]
        L_ORDER_PROD[link_order_product]
    end

    subgraph Sats["Satellites — Descriptive"]
        S_CUST[sat_customer_details]
        S_PROD[sat_product_details]
        S_ORDER[sat_order_details]
        S_CUST_HIST[sat_customer_history]
    end

    H_CUST --> L_ORDER_CUST
    H_ORDER --> L_ORDER_CUST
    H_ORDER --> L_ORDER_PROD
    H_PROD --> L_ORDER_PROD
    H_CUST --> S_CUST
    H_CUST --> S_CUST_HIST
    H_PROD --> S_PROD
    H_ORDER --> S_ORDER
```

**Satellite split rules**
- One satellite per source system.
- Split by rate of change (fast vs. slow attributes).
- Hash-diff for change detection; no updates, only inserts.

---

## 4. Streaming Data Schema

Kafka / Kinesis event envelopes with schema registry (Avro / Protobuf).

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    subgraph Producers["Producers"]
        P1[Web App]
        P2[Mobile App]
        P3[Backend Services]
    end

    subgraph Topics["Kafka Topics"]
        T1[orders.created]
        T2[orders.updated]
        T3[customer.events]
        T4[product.inventory]
    end

    subgraph Consumers["Consumers"]
        C1[Stream Processor]
        C2[Real-time OLAP]
        C3[ML Inference]
    end

    subgraph Sinks["Sinks"]
        K1[(Delta Lake)]
        K2[(Redis)]
        K3[(Feature Store)]
    end

    P1 --> T1
    P2 --> T1
    P3 --> T2
    P3 --> T3
    P3 --> T4
    T1 --> C1
    T2 --> C1
    T3 --> C2
    T4 --> C3
    C1 --> K1
    C2 --> K2
    C3 --> K3
```

**Event envelope (Avro)**

```json
{
  "event_id": "uuid",
  "event_type": "orders.created",
  "occurred_at": "2026-10-02T10:00:00Z",
  "source": "web-checkout",
  "trace_id": "abc-123",
  "payload": { "order_id": 1001, "customer_id": 55, "total": 249.99 }
}
```

**Schema rules**
- Backward-compatible evolution (add optional fields only).
- Schema Registry enforces compatibility at publish time.
- Dead-letter queue for schema violations.

---

## 5. Metadata Management

Unified catalog covering schema, lineage, quality, and discovery.

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    subgraph Ingestion["Metadata Sources"]
        M1[Schema Registry]
        M2[Delta / Iceberg Catalog]
        M3[Airflow / Dagster]
        M4[Data Quality Tests]
    end

    subgraph Catalog["Unified Catalog"]
        C[(Metadata Store)]
        C1[Schema Registry]
        C2[Lineage Graph]
        C3[Data Quality]
        C4[Business Glossary]
    end

    subgraph Consumption["Consumers"]
        U1[Data Discovery UI]
        U2[Impact Analysis]
        U3[Access Control]
        U4[CI/CD Gates]
    end

    M1 --> C1
    M2 --> C2
    M3 --> C2
    M4 --> C3
    C1 --> C
    C2 --> C
    C3 --> C
    C4 --> C
    C --> U1
    C --> U2
    C --> U3
    C --> U4
```

**Key metadata artifacts**

| Artifact | Tool | Purpose |
|----------|------|---------|
| Schema definitions | Confluent Schema Registry | Versioned Avro/Protobuf |
| Table catalog | Unity Catalog / Hive Metastore | Table & partition discovery |
| Lineage | OpenLineage / DataHub | Column-level impact analysis |
| Quality rules | Soda / Great Expectations | Automated data tests |
| Glossary | DataHub / Collibra | Business term ownership |

**Governance hooks**
- Schema change → CI validation → auto-approve or manual gate.
- Lineage graph powers downstream impact alerts.
- Quality scores gate Gold-layer promotion.
