# IoT Architecture & Platform Guide

APEX-OS Business Platform — IoT subsystem covering device lifecycle, data ingestion, real-time processing, and analytics.

---

## 1. IoT Architecture

Layered edge-to-cloud architecture:

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TB
    subgraph EDGE["Edge Layer"]
        direction LR
        SENSOR["Sensors & Devices"]
        ACTUATOR["Actuators"]
        GATEWAY["Edge Gateway\n(Local Aggregation"]
        SENSOR --> GATEWAY
        ACTUATOR --> GATEWAY
    end
    subgraph INGEST["Ingestion Layer"]
        direction LR
        LB["Load Balancer"]
        MQTT["MQTT Broker\n(Mosquitto/EMQX)"]
        KAFKA["Kafka Cluster\n(Event Streaming)"]
        LB --> MQTT --> KAFKA
    end
    subgraph RT["Real-Time Processing"]
        direction LR
        FLINK["Flink / Spark Streaming"]
        RULE["Rule Engine"]
        CEP["Complex Event Processing"]
        FLINK --> RULE
        FLINK --> CEP
    end
    subgraph STORE["Storage Layer"]
        direction LR
        TSDB[("Time-Series DB\n(InfluxDB/TimescaleDB)")]
        DW[("Data Warehouse\n(Snowflake/BigQuery)")]
        OBJ[("Object Storage\n(S3/Data Lake)")]
    end
    subgraph ANALYTICS["Analytics & ML"]
        direction LR
        DASH["Dashboards\n(Grafana)"]
        ML["ML Platform\n(Training + Inference)"]
        ALERT["Alerting & Notifications"]
    end
    EDGE --> LB
    KAFKA --> FLINK
    FLINK --> TSDB
    FLINK --> RULE --> ALERT
    KAFKA --> DW
    KAFKA --> OBJ
    TSDB --> DASH
    DW --> ML --> DASH
    ML --> ALERT
```

**Key principles:**

- **Edge autonomy:** Gateways buffer, filter, and act locally when cloud connectivity drops.
- **Event-driven backbone:** Kafka as the single source of truth; consumers are decoupled.
- **Tiered storage:** Hot data in TSDB, cold data in object storage, analytics in the warehouse.
- **Exactly-once semantics:** Idempotent producers + transactional consumers prevent duplicates.

---

## 2. Device Management

### 2.1 Device Lifecycle

```mermaid
%%{init: {'theme': 'dark'}}%%
stateDiagram-v2
    [*] --> Provisioned: Manufacture + flash firmware
    Provisioned --> Registered: Claim via cloud registry
    Registered --> Active: Successful handshake
    Active --> Suspended: Anomaly / policy violation
    Suspended --> Active: Admin re-activation
    Active --> Retired: End-of-life / decommission
    Suspended --> Retired: Admin decommission
    Retired --> [*]
```

### 2.2 Core Capabilities

| Capability | Description | Technology |
|------------|-------------|------------|
| **Provisioning** | Zero-touch enrollment using X.509 certs or TPM-based identity | AWS IoT Core / Azure IoT Hub JITP |
| **Registry** | Device registry with metadata, tags, group hierarchy | PostgreSQL + GraphQL API |
| **OTA Firmware** | Delta updates with rollback, signed images, staged rollout | Mender / RAUC |
| **Shadow / Twin** | Desired vs. reported state reconciliation | Azure IoT Shadow / Digital Twin |
| **Monitoring** | Heartbeat, connectivity, battery, health metrics | Prometheus + custom agent |
| **Remote Config** | Push configuration changes, feature flags | MQTT control channel |
| **Certificate Mgmt** | Automated rotation, revocation via CRL/OCSP | HashiCorp Vault / ACME |
| **Grouping** | Fleet segmentation by region, model, custom tags | Tag-based dynamic groups |

### 2.3 Device Identity & Security

- Every device has a unique X.509 certificate burned during provisioning.
- Device identity is bound to hardware (TPM / secure element) where available.
- Mutual TLS for all cloud connections.
- Least-privilege topic ACLs (devices can only publish to their own namespaces).
- Certificate rotation every 90 days, automated via renewal agent.

### 2.4 API Surface

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant Admin as Admin UI
    participant API as Device API
    participant Registry as Registry DB
    participant Device as Edge Device
    Admin->>API: Create device (model, tags)
    API->>Registry: Store identity + generate cert
    API-->>Admin: Return device ID + cert
    Admin->>Device: Flash cert + credentials
    Device->>API: Connect (mTLS + handshake)
    API->>Registry: Mark device ACTIVE
    API-->>Device: Ack + initial config
    loop Health checks
        Device->>API: Heartbeat every 30s
        API->>Registry: Update last_seen
    end
```

---

## 3. Data Ingestion

### 3.1 Protocol Support

| Protocol | Use Case | Default Port |
|----------|----------|-------------|
| **MQTT 5.0** | Telemetry from constrained devices | 8883 (TLS) |
| **MQTT over WebSocket** | Browser / mobile apps | 443 |
| **CoAP** | UDP-based, ultra-low-power (LoRaWAN, NB-IoT) | 5684 (DTLS) |
| **HTTP/REST** | Bulk uploads, firmware callbacks | 443 |
| **gRPC** | High-throughput internal services | 50051 |
| **LoRaWAN** | Long-range, low-power via gateways | Via packet forwarder |

### 3.2 Message Format

All telemetry follows a canonical schema (JSON / Protobuf):

```json
{
  "device_id": "dev-01HX3K...",
  "ts": 1727800000000,
  "type": "telemetry",
  "metrics": { "temperature": 23.4, "humidity": 58.2, "pressure": 1013.2 },
  "metadata": { "firmware": "2.1.0", "rssi": -72, "battery": 87 }
}
```

- **Protobuf** for high-frequency sensors (bandwidth-efficient).
- **JSON Schema** registry enforces contract validation at the edge gateway.
- **Avro** used for Kafka topic schemas with Confluent Schema Registry.

### 3.3 Ingestion Pipeline

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    D["Devices"] --> GW["Edge Gateway\n(Buffer + Filter"]
    GW --> V["Schema Validation"]
    V --> E["Enrichment\n(Geo, Tenant, Tags)"]
    E --> RT["Routing\n(Topic per data class)"]
    RT --> T1["kafka-telemetry"]
    RT --> T2["kafka-events"]
    RT --> T3["kafka-commands"]
    T1 --> S1["Stream Processor"]
    T2 --> S1
    T3 --> S2["Command Dispatcher"]
```

### 3.4 Throughput & Scaling

- MQTT brokers scale horizontally via EMQX clustering (10M+ concurrent connections).
- Kafka partitions by `device_id % N` for ordered per-device processing.
- Backpressure handled via consumer lag monitoring + auto-scaling consumers.
- Dead-letter queue (DLQ) for poison messages after 3 retries.

---

## 4. Real-Time Processing

### 4.1 Stream Processing Architecture

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TB
    KAFKA["Kafka Topics"] --> SRC["Flink Source\n(Consumer Group)"]
    SRC --> PARSE["Parse + Validate"]
    PARSE --> DEDUP["Deduplication\n(Event ID + Window)"]
    DEDUP --> WIN["Windowing\n(Tumbling / Sliding / Session)"]
    WIN --> AGG["Aggregations\n(Avg, Sum, Count, Min/Max)"]
    AGG --> RULE["Rule Engine\n(Threshold / Trend)"]
    RULE --> ANOMALY["Anomaly Detection\n(ML Model)"]
    ANOMALY --> OUT{"Output Router"}
    OUT --> ALERT["Alert Service\n(PagerDuty / Slack / SMS)"]
    OUT --> TSDB_SINK["TSDB Sink"]
    OUT --> NOTIF["Push Notification\n(Firebase / APNs)"]
    OUT --> CMD["Command Dispatch\n(to Device)"]
```

### 4.2 Processing Patterns

| Pattern | Example | Implementation |
|---------|---------|----------------|
| **Filtering** | Drop readings outside physical bounds | Flink `filter()` |
| **Windowed Aggregation** | 5-min avg temperature per zone | Flink `window(TumblingEventTimeWindows)` |
| **Sessionization** | Detect device power-on cycles | Flink `EventTimeSessionWindows` |
| **CEP** | "Temp spike followed by pressure drop within 60s" | Flink CEP `Pattern` API |
| **Enrichment** | Join telemetry with device metadata | Async I/O to registry cache |
| **Anomaly Detection** | Isolation Forest on metric vectors | Flink ML + model serving |

### 4.3 Latency Targets

| Stage | Target Latency |
|-------|---------------|
| Device → Gateway | < 100 ms |
| Gateway → Kafka | < 200 ms |
| Kafka → Rule evaluation | < 500 ms |
| Alert dispatched | < 1 s end-to-end |

### 4.4 Fault Tolerance

- Kafka replication factor 3, min.insync.replicas=2.
- Flink checkpoints to distributed storage (S3/HDFS) every 30s.
- Savepoints for stateful job upgrades with zero data loss.
- Idempotent sinks prevent duplicate writes on replay.

---

## 5. Analytics

### 5.1 Analytics Stack

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TB
    subgraph Batch["Batch Analytics"]
        direction LR
        SPARK["Spark Jobs\n(ETL + Aggregations)"]
        DBT["dbt Models\n(Data Transform)"]
        SCHED["Airflow\n(Orchestration)"]
        SCHED --> SPARK --> DBT
    end
    subgraph Warehouse["Data Warehouse"]
        direction LR
        DWH[("Columnar Store\n(Snowflake/BigQuery)")]
        DBT --> DWH
    end
    subgraph Serving["Serving Layer"]
        direction LR
        OLAP["OLAP Engine\n(Druid/ClickHouse)"]
        FEAT["Feature Store\n(Feast)"]
        API2["Analytics API\n(GraphQL/REST)"]
    end
    subgraph Visualization["Visualization"]
        direction LR
        BI["BI Dashboards\n(Metabase/Looker)"]
        GRAF["Real-time\n(Grafana)"]
        JUP["Notebooks\n(Jupyter)"]
    end
    subgraph MLops["ML Pipeline"]
        direction LR
        TRAIN["Model Training\n(SageMaker/Vertex)"]
        REG["Model Registry\n(MLflow)"]
        INFER["Batch Inference"]
        SERV["Real-time Serving\n(Seldon/Triton)"]
        MON["Drift Monitoring"]
        TRAIN --> REG --> INFER
        REG --> SERV
        SERV --> MON
    end
    DWH --> OLAP --> API2
    DWH --> FEAT
    OLAP --> BI
    FEAT --> TRAIN
    API2 --> JUP
    INFER --> DWH
```

### 5.2 Analytics Use Cases

| Use Case | Description | Data Source |
|----------|-------------|-------------|
| **Operational Dashboards** | Live fleet health, connectivity, battery status | TSDB + Grafana |
| **Predictive Maintenance** | Forecast failure probability from vibration/temp trends | Feature Store → ML |
| **Energy Optimization** | Analyze consumption patterns, identify waste | Warehouse → dbt |
| **Fleet Utilization** | Device uptime, deployment ROI, geospatial heatmaps | OLAP → Metabase |
| **Anomaly Investigation** | Drill into alerts, replay events, root-cause analysis | Notebook + raw events |
| **SLA Reporting** | Uptime %, MTTR, compliance reporting | Warehouse → BI |

### 5.3 Real-Time vs. Batch

| Aspect | Real-Time (Flink) | Batch (Spark) |
|--------|-------------------|---------------|
| **Latency** | Sub-second | Minutes to hours |
| **Data volume** | Per-event | Petabyte-scale scans |
| **Use case** | Alerts, live dashboards | Training data, deep analysis |
| **State** | In-memory + RocksDB | Disk-based shuffles |
| **Output** | TSDB, push notifications | Warehouse, reports |

### 5.4 ML Pipeline

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    RAW["Raw Events\n(Kafka/S3)"] --> FE["Feature Engineering\n(Flink + Spark)"]
    FE --> FS["Feature Store\n(Online + Offline)"]
    FS --> TRAIN["Training\n(AutoML / Custom)"]
    TRAIN --> EVAL["Evaluation\n(Backtest + A/B)"]
    EVAL --> REG["Registry\n(MLflow)"]
    REG --> DEPLOY{"Deploy"}
    DEPLOY --> ONLINE["Online Serving\n(Triton)"]
    DEPLOY --> BATCH["Batch Scoring\n(Spark)"]
    ONLINE --> FEED["Feedback Loop\n(Rewards + Labels)"]
    BATCH --> FEED
    FEED --> FS
```

### 5.5 Data Retention

| Tier | Storage | Retention |
|------|---------|-----------|
| **Hot** | InfluxDB / TimescaleDB | 30 days |
| **Warm** | Apache Parquet on S3 | 1 year |
| **Cold** | Glacier / Archive | 7 years (compliance) |

Automated lifecycle policies move data between tiers based on age and access patterns.
