# Deepened Module Benchmarks

> Performance targets for APEX-OS Business Platform deepened modules.  
> Baseline: 4 vCPU / 8 GB RAM / SSD, warm JVM, connection pool = 20.

## Methodology

- **Throughput**: sustained ops/sec over 60 s steady-state.
- **Latency**: p50 / p99 in milliseconds (ms) after warm-up.
- **Memory**: heap delta in MB during peak load.
- All benchmarks run with production-like data volumes unless noted.

---

## 1. Accounting

| Operation | Throughput (ops/s) | Latency p50 (ms) | Latency p99 (ms) | Memory (MB) |
|---|---|---|---|---|
| Multi-currency conversion (10k txns, 15 FX pairs) | 1,200 | 8 | 45 | 12 |
| Recurring entry generation (500 schedules → 5k entries) | 850 | 12 | 60 | 18 |
| Financial statement generation (BS/IS/CF, 12 periods) | 45 | 180 | 420 | 85 |
| Budget comparison (10k line items, variance) | 600 | 22 | 95 | 28 |
| Tax calculation (multi-jurisdiction, 5k invoices) | 900 | 15 | 70 | 22 |

---

## 2. CRM

| Operation | Throughput (ops/s) | Latency p50 (ms) | Latency p99 (ms) | Memory (MB) |
|---|---|---|---|---|
| Lead scoring (10k leads, 25 signals each) | 1,500 | 6 | 35 | 15 |
| Pipeline automation (stage transitions, 2k deals) | 700 | 18 | 85 | 20 |
| Email tracking (open/click webhook, 50k events) | 3,000 | 3 | 20 | 35 |
| Segmentation (dynamic segment, 100k contacts) | 120 | 250 | 600 | 95 |
| Churn prediction (score 20k accounts, ML model) | 350 | 45 | 180 | 110 |

---

## 3. Analytics

| Operation | Throughput (ops/s) | Latency p50 (ms) | Latency p99 (ms) | Memory (MB) |
|---|---|---|---|---|
| Cohort analysis (12-month retention, 50k users) | 80 | 320 | 750 | 140 |
| Funnel analysis (10-step funnel, 100k sessions) | 200 | 95 | 280 | 65 |
| Forecasting (ARIMA, 30-day horizon, 500 series) | 25 | 450 | 1,200 | 220 |
| Anomaly detection (z-score + IQR, 1M data points) | 500 | 30 | 120 | 75 |
| Correlation matrix (100 variables × 50k rows) | 40 | 380 | 900 | 160 |

---

## 4. Security

| Operation | Throughput (ops/s) | Latency p50 (ms) | Latency p99 (ms) | Memory (MB) |
|---|---|---|---|---|
| JWT refresh (token rotation, RS256) | 2,500 | 4 | 25 | 8 |
| OAuth2 token exchange (authorization code flow) | 1,800 | 10 | 55 | 14 |
| SAML assertion validation (XML signature check) | 600 | 25 | 110 | 30 |
| ABAC policy evaluation (1k rules, 10k subjects) | 1,200 | 7 | 40 | 18 |
| Security headers injection (CSP/HSTS/X-Frame) | 5,000 | 1 | 5 | 3 |

---

## 5. Workflow

| Operation | Throughput (ops/s) | Latency p50 (ms) | Latency p99 (ms) | Memory (MB) |
|---|---|---|---|---|
| Parallel execution (50 concurrent branches) | 400 | 55 | 220 | 55 |
| Conditional branching (10k evaluations, 5 conditions) | 2,000 | 5 | 30 | 12 |
| Sub-workflow invocation (nested 3 levels deep) | 350 | 70 | 260 | 48 |
| Workflow versioning (diff + migrate 500 instances) | 90 | 200 | 550 | 90 |
| Workflow analytics (execution trace, 10k runs) | 150 | 130 | 380 | 70 |

---

## Summary

| Module | Avg Throughput (ops/s) | Avg p99 Latency (ms) | Peak Memory (MB) |
|---|---|---|---|
| Accounting | 780 | 158 | 85 |
| CRM | 1,414 | 197 | 110 |
| Analytics | 235 | 710 | 220 |
| Security | 2,280 | 47 | 30 |
| Workflow | 518 | 292 | 90 |

**Notes:**
- Throughput measured at 70% CPU saturation.
- p99 latency includes GC pauses (G1GC, max 50 ms target).
- Memory figures are steady-state heap delta, not total footprint.
- ML-dependent operations (churn, forecasting) use pre-loaded models.
