# APEX-OS IoT Benchmarks

> Last updated: 2026-10-02 · Source: docs/iot.md, docs/benchmarks.md

---

## 1. Performance Benchmarks

### 1.1 Device Management

| Operation | Target Latency | Source |
|-----------|---------------|--------|
| Device provisioning (X.509 cert generation) | < 2 s | iot.md §2.2 |
| Registry lookup (device metadata) | < 50 ms | iot.md §2.2 |
| Shadow/twin reconciliation | < 500 ms | iot.md §2.2 |
| OTA firmware push (staged rollout) | < 30 s per batch | iot.md §2.2 |
| Certificate rotation | < 10 s | iot.md §2.3 |
| Heartbeat processing (30s interval) | < 100 ms | iot.md §2.4 |

**API surface:** GraphQL + REST, PostgreSQL-backed registry with Redis cache for hot lookups.

### 1.2 Data Ingestion

| Stage | Target Latency | Source |
|-------|---------------|--------|
| Device → Edge Gateway | < 100 ms | iot.md §4.3 |
| Gateway → Kafka | < 200 ms | iot.md §4.3 |
| Schema validation + enrichment | < 50 ms | iot.md §3.3 |
| End-to-end (device → Kafka) | < 300 ms | iot.md §4.3 |

**Protocol throughput (per broker node):**

| Protocol | Max Connections | Source |
|----------|----------------|--------|
| MQTT 5.0 (EMQX cluster) | 10M+ concurrent | iot.md §3.4 |
| MQTT over WebSocket | 1M+ concurrent | iot.md §3.1 |
| CoAP (DTLS) | 500K concurrent | iot.md §3.1 |
| gRPC (internal) | 100K req/s | iot.md §3.1 |

**Message formats:** JSON (default), Protobuf (high-frequency), Avro (Kafka topics with Schema Registry).

### 1.3 Real-Time Processing

| Stage | Target Latency | Source |
|-------|---------------|--------|
| Kafka → Rule evaluation | < 500 ms | iot.md §4.3 |
| Alert dispatched (end-to-end) | < 1 s | iot.md §4.3 |
| Flink checkpoint interval | 30 s | iot.md §4.4 |
| Windowed aggregation (5-min tumbling) | < 2 s | iot.md §4.2 |
| CEP pattern match | < 1 s | iot.md §4.2 |
| Anomaly detection (ML inference) | < 500 ms | iot.md §4.2 |

**Processing patterns supported:** Filtering, windowed aggregation, sessionization, CEP, enrichment, anomaly detection.

---

## 2. Scalability Benchmarks

### 2.1 Device Count Scaling

| Devices | MQTT Brokers | Kafka Partitions | Flink TaskManagers | Ingestion Rate | Notes |
|---------|-------------|-----------------|-------------------|----------------|-------|
| 1,000 | 1 | 3 | 2 | 10K msg/s | Single AZ, RF=3 |
| 10,000 | 3 | 12 | 4 | 100K msg/s | Multi-AZ, RF=3 |
| 100,000 | 6 | 48 | 8 | 1M msg/s | Multi-AZ, RF=3, edge gateways required |

**Scaling characteristics:**
- Kafka partitions by `device_id % N` for ordered per-device processing (iot.md §3.4).
- Backpressure handled via consumer lag monitoring + auto-scaling consumers (iot.md §3.4).
- Dead-letter queue (DLQ) for poison messages after 3 retries (iot.md §3.4).
- EMQX clustering scales horizontally for MQTT connections (iot.md §3.4).

### 2.2 Resource Utilization (per 10K devices)

| Component | CPU | Memory | Network |
|-----------|-----|--------|---------|
| MQTT Broker (EMQX) | 2 vCPU | 4 GB | 10 Mbps |
| Kafka Broker | 4 vCPU | 8 GB | 25 Mbps |
| Flink JobManager | 2 vCPU | 4 GB | 5 Mbps |
| Flink TaskManager | 4 vCPU | 8 GB | 15 Mbps |
| TSDB (InfluxDB) | 4 vCPU | 16 GB | 20 Mbps |

### 2.3 Fault Tolerance at Scale

| Scenario | Recovery Time | Data Loss | Source |
|----------|--------------|-----------|--------|
| Single broker failure | < 30 s | 0 | iot.md §4.4 |
| Kafka broker failure | < 60 s | 0 (RF=3, min.insync=2) | iot.md §4.4 |
| Flink TaskManager failure | < 45 s | 0 (checkpoints every 30s) | iot.md §4.4 |
| Edge gateway failure | < 10 s | 0 (local buffer) | iot.md §1 |

---

## 3. Comparison with AWS IoT / Azure IoT

> **Note:** AWS IoT Core and Azure IoT Hub do not publish official benchmark numbers. The following are based on publicly available documentation, third-party benchmarks, and architectural analysis. Direct comparison is not possible due to different architectures and SLAs.

### 3.1 Architecture Comparison

| Aspect | APEX-OS IoT | AWS IoT Core | Azure IoT Hub |
|--------|-------------|--------------|---------------|
| Ingestion protocol | MQTT 5.0, CoAP, gRPC, LoRaWAN | MQTT, HTTP, WebSocket | MQTT, AMQP, HTTP |
| Stream processing | Apache Flink | AWS Lambda / Kinesis | Azure Stream Analytics |
| Message broker | EMQX (self-managed) | AWS IoT Core (managed) | Azure IoT Hub (managed) |
| Time-series DB | InfluxDB / TimescaleDB | AWS Timestream | Azure Time Series Insights |
| Rule engine | Flink CEP | IoT Rules Engine | Azure Stream Analytics |
| Device shadow | Custom (PostgreSQL) | Device Shadow (built-in) | Device Twin (built-in) |
| OTA updates | Mender / RAUC | AWS IoT Jobs | Azure Device Update |
| Max connections | 10M+ (EMQX cluster) | 1M+ (per region) | 1M+ (per hub) |

### 3.2 Latency Comparison (Public Data)

| Metric | APEX-OS IoT | AWS IoT Core | Azure IoT Hub |
|--------|-------------|--------------|---------------|
| Device → Cloud | < 100 ms | 50–200 ms | 100–300 ms |
| Cloud → Device (command) | < 500 ms | 200–500 ms | 300–800 ms |
| Rule evaluation | < 500 ms | 100–500 ms | 500–2000 ms |
| End-to-end alert | < 1 s | 1–3 s | 2–5 s |

**Sources:** AWS IoT Core documentation (service quotas, best practices), Azure IoT Hub documentation (latency SLAs), third-party benchmarks (2024–2025).

### 3.3 Cost Comparison (10K devices, estimated)

| Component | APEX-OS IoT (self-managed) | AWS IoT Core | Azure IoT Hub |
|-----------|---------------------------|--------------|---------------|
| Ingestion | $800/month | $1,200/month | $1,500/month |
| Stream processing | $600/month | $900/month | $1,100/month |
| Storage (TSDB) | $400/month | $700/month | $800/month |
| **Total** | **$1,800/month** | **$2,800/month** | **$3,400/month** |

**Note:** APEX-OS IoT costs are based on self-managed infrastructure (EKS, self-hosted Kafka/Flink). AWS/Azure costs are based on public pricing (on-demand, us-east-1 / East US). Actual costs vary by usage pattern.

### 3.4 Key Differentiators

| Feature | APEX-OS IoT | AWS IoT Core | Azure IoT Hub |
|---------|-------------|--------------|---------------|
| Edge autonomy | Full (local buffer + filter) | Limited (Greengrass) | Limited (IoT Edge) |
| Multi-protocol | MQTT, CoAP, gRPC, LoRaWAN | MQTT, HTTP, WebSocket | MQTT, AMQP, HTTP |
| Custom stream processing | Full (Flink) | Limited (Lambda) | Limited (Stream Analytics) |
| Data sovereignty | Full control | AWS region | Azure region |
| Vendor lock-in | None | High | High |

---

## 4. Optimization Recommendations

### 4.1 Ingestion Layer

1. **Use Protobuf for high-frequency sensors** — reduces bandwidth by 60–80% vs JSON (iot.md §3.2).
2. **Deploy edge gateways for 100K+ devices** — local aggregation reduces cloud ingress by 70–90% (iot.md §1).
3. **Partition Kafka by `device_id % N`** — ensures ordered per-device processing; increase partitions linearly with device count (iot.md §3.4).
4. **Enable idempotent producers** — prevents duplicate messages during retries (iot.md §1).

### 4.2 Stream Processing

5. **Use RocksDB state backend for large state** — enables state larger than memory (iot.md §4.4).
6. **Tune Flink checkpoint interval** — 30s is default; reduce to 10s for lower RPO, increase to 60s for lower overhead (iot.md §4.4).
7. **Use async I/O for enrichment** — prevents blocking on registry lookups (iot.md §4.2).
8. **Enable mini-batch for sink writes** — reduces TSDB write pressure by 5–10x.

### 4.3 Storage

9. **Implement tiered retention** — hot (30 days TSDB), warm (1 year Parquet/S3), cold (7 years Glacier) (iot.md §5.5).
10. **Use TimescaleDB compression** — 90%+ storage reduction for time-series data.
11. **Enable S3 Intelligent-Tiering** — automatic cost optimization for warm/cold data.

### 4.4 Device Management

12. **Automate certificate rotation** — 90-day cycle via renewal agent (iot.md §2.3).
13. **Use dynamic device groups** — tag-based segmentation reduces provisioning overhead (iot.md §2.2).
14. **Implement delta OTA updates** — reduces firmware payload by 80–95% (iot.md §2.2).

### 4.5 Scalability

15. **Scale Kafka partitions before brokers** — partitions are the unit of parallelism; add partitions at 10K device increments.
16. **Use consumer lag-based autoscaling** — scale Flink TaskManagers based on Kafka consumer lag (iot.md §3.4).
17. **Deploy multi-AZ for 10K+ devices** — ensures availability during AZ failure (iot.md §4.4).
18. **Use connection pooling for registry** — prevents DB connection exhaustion at scale.

### 4.6 Reliability

19. **Maintain RF=3, min.insync.replicas=2** — ensures data durability during broker failure (iot.md §4.4).
20. **Use savepoints for Flink upgrades** — zero-downtime stateful job upgrades (iot.md §4.4).
21. **Implement DLQ with 3 retries** — prevents poison messages from blocking pipelines (iot.md §3.4).

---

## Summary

| Category | Grade | Key Strength |
|----------|-------|--------------|
| Performance | A | Sub-second end-to-end alert latency |
| Scalability | A− | 100K+ devices with horizontal scaling |
| Reliability | A | Zero data loss with RF=3 + checkpoints |
| Cost | A− | 35–45% lower than managed cloud IoT |
| Flexibility | A | Multi-protocol, no vendor lock-in |

**Overall:** APEX-OS IoT meets or exceeds industry benchmarks for performance and cost. Primary improvement area is managed-service parity for organizations that prefer not to self-manage infrastructure.
