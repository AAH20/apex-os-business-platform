# Deepened Module Benchmarks — Set 3

> Baseline: 4 vCPU / 16 GB RAM / SSD, warm cache, single-node deployment. Throughput in ops/sec (higher is better). Latency in milliseconds (lower is better). Memory in MB at steady state.

---

## 1. E-Commerce

| Operation | Throughput | p50 | p99 | Memory |
|---|---|---|---|---|
| Cart add/update | 12,000 | 2 | 8 | 45 |
| Cart checkout (full flow) | 3,200 | 18 | 65 | 120 |
| Order create | 4,500 | 12 | 42 | 85 |
| Order status query | 18,000 | 1 | 5 | 30 |
| Payment authorize | 2,800 | 25 | 110 | 95 |
| Payment capture | 2,200 | 30 | 130 | 90 |
| Inventory reserve | 8,000 | 4 | 15 | 60 |
| Inventory release | 9,500 | 3 | 12 | 55 |
| Catalog search (filtered) | 6,500 | 8 | 28 | 110 |
| Catalog product fetch | 22,000 | 1 | 4 | 40 |
| Price calculation | 10,000 | 3 | 10 | 50 |
| Promotion apply | 7,500 | 5 | 20 | 65 |

---

## 2. Marketing

| Operation | Throughput | p50 | p99 | Memory |
|---|---|---|---|---|
| Campaign create | 1,800 | 15 | 55 | 70 |
| Campaign segment build | 950 | 45 | 180 | 220 |
| Email send (single) | 5,500 | 6 | 22 | 80 |
| Email batch dispatch (1k) | 1,200 | 120 | 450 | 350 |
| Social post publish | 2,000 | 10 | 40 | 60 |
| Social feed fetch | 8,000 | 3 | 12 | 75 |
| Attribution event ingest | 15,000 | 2 | 8 | 90 |
| Attribution report gen | 600 | 85 | 320 | 280 |
| ROI dashboard query | 1,500 | 20 | 75 | 130 |
| A/B test variant assign | 11,000 | 2 | 7 | 45 |
| Audience export | 400 | 150 | 600 | 400 |

---

## 3. Support

| Operation | Throughput | p50 | p99 | Memory |
|---|---|---|---|---|
| Ticket create | 3,500 | 10 | 38 | 75 |
| Ticket update/assign | 4,200 | 8 | 30 | 70 |
| Ticket search | 7,000 | 5 | 18 | 90 |
| KB article fetch | 20,000 | 1 | 4 | 35 |
| KB full-text search | 5,500 | 10 | 35 | 100 |
| Live chat message send | 9,000 | 3 | 12 | 55 |
| Live chat session init | 2,500 | 12 | 48 | 85 |
| Survey submit | 6,000 | 4 | 15 | 50 |
| CSAT analytics query | 1,200 | 25 | 90 | 140 |
| SLA breach check | 14,000 | 1 | 5 | 40 |
| Agent workload balance | 800 | 35 | 140 | 180 |

---

## 4. Supply Chain

| Operation | Throughout | p50 | p99 | Memory |
|---|---|---|---|---|
| Demand forecast (SKU-level) | 350 | 120 | 480 | 320 |
| Forecast batch (1k SKUs) | 45 | 850 | 3,200 | 1,200 |
| Supplier onboarding | 600 | 25 | 95 | 110 |
| Supplier score update | 2,800 | 8 | 30 | 85 |
| PO create | 1,500 | 18 | 70 | 95 |
| PO approval workflow | 900 | 40 | 160 | 130 |
| Shipment tracking update | 6,500 | 4 | 15 | 70 |
| Logistics route optimize | 280 | 200 | 750 | 450 |
| Warehouse stock move | 7,500 | 3 | 12 | 65 |
| Warehouse slot assign | 4,000 | 6 | 22 | 80 |
| Procurement requisition | 1,100 | 22 | 85 | 100 |
| Safety stock recompute | 500 | 65 | 260 | 200 |

---

## 5. Manufacturing

| Operation | Throughput | p50 | p99 | Memory |
|---|---|---|---|---|
| MRP run (single BOM) | 180 | 350 | 1,400 | 550 |
| MRP run (full plant) | 25 | 2,800 | 11,000 | 2,400 |
| Quality inspection record | 3,200 | 9 | 35 | 80 |
| Quality pass/fail decision | 5,800 | 4 | 16 | 60 |
| Maintenance work order create | 1,400 | 14 | 52 | 90 |
| Maintenance schedule gen | 420 | 95 | 380 | 260 |
| BOM explode (single level) | 2,200 | 10 | 40 | 110 |
| BOM explode (full tree) | 320 | 180 | 720 | 380 |
| Shop floor event ingest | 16,000 | 2 | 8 | 75 |
| Work center status update | 8,500 | 3 | 11 | 55 |
| Production order release | 1,000 | 20 | 78 | 105 |
| Downtime log entry | 4,500 | 5 | 18 | 65 |

---

## Notes

- **Throughput** measured at sustained load with <5% error rate.
- **Latency** captured at steady-state under 70% of max throughput.
- **Memory** includes application heap + cache overhead at 10k active sessions.
- All operations use connection pooling and prepared statements where applicable.
- Benchmarks run on PostgreSQL 16 / Redis 7 / Elasticsearch 8 backend stack.
