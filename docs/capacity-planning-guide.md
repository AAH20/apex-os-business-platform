# Capacity Planning Guide

## 1. Methodology

Capacity planning ensures APEX-OS resources match demand without over-provisioning. Follow a continuous cycle:

1. **Baseline** — Measure current utilization across CPU, memory, storage, network, and I/O.
2. **Forecast** — Project growth from historical trends, business roadmaps, and seasonal patterns.
3. **Model** — Simulate scenarios (normal, peak, failure) using load testing and queuing theory.
4. **Provision** — Allocate resources with headroom buffers (typically 20–30% above forecast).
5. **Review** — Reassess monthly or when usage deviates >15% from forecast.

**Principles:**
- Plan for peak, not average — average hides burst patterns.
- Separate steady-state from burst capacity.
- Account for failure domains: size for N+1 redundancy.
- Distinguish horizontal (scale-out) from vertical (scale-up) options early.

## 2. Resource Estimation

### Compute
- **CPU:** `(peak_rps × avg_cpu_per_request) / target_utilization`
  - Example: 500 RPS × 20ms CPU = 10 cores at 100%; at 60% target → ~17 cores.
- **Memory:** `(concurrent_sessions × memory_per_session) + system_overhead`
  - Include caches, buffers, and 25% headroom for GC spikes.

### Storage
- **Capacity:** `daily_growth × retention_period × replication_factor × 1.5 (safety)`
- **IOPS:** Estimate from workload profile (read/write ratio, random vs. sequential).

### Network
- **Bandwidth:** `peak_concurrent_users × avg_payload × requests_per_user × 1.3 (burst)`
- **Connection count:** Track concurrent connections; size connection pools at 70% of OS limits.

### Database
- **Connections:** `(app_servers × pool_size) < max_connections × 0.8`
- **Query throughput:** Benchmark p99 latency under 2× expected load.

### Sizing Workload Classes
| Class | CPU:Mem Ratio | Example |
|-------|--------------|---------|
| Web/API | 1:2 | Stateless services |
| Cache | 1:4 | Redis, in-memory |
| Database | 1:8 | PostgreSQL, persistent |
| Worker | 1:1 | CPU-bound batch jobs |

## 3. Scaling Triggers

Define thresholds that fire scaling actions before users are affected.

### Scale-Out Triggers (add instances)
| Metric | Threshold | Cooldown |
|--------|-----------|----------|
| CPU utilization | > 70% for 5 min | 5 min |
| Memory utilization | > 75% for 5 min | 5 min |
| Request queue depth | > 100 pending | 2 min |
| p99 latency | > 500 ms for 3 min | 5 min |
| Error rate | > 1% for 2 min | 3 min |

### Scale-In Triggers (remove instances)
| Metric | Threshold | Cooldown |
|--------|-----------|----------|
| CPU utilization | < 30% for 15 min | 15 min |
| Memory utilization | < 40% for 15 min | 15 min |
| Request rate | < 20% of peak for 20 min | 20 min |

### Scale-Up Triggers (resize instance)
| Metric | Threshold | Action |
|--------|-----------|--------|
| CPU throttling | > 5% of periods | Increase CPU allocation |
| Memory pressure | OOM events or > 85% | Increase memory |
| Disk I/O wait | > 20% | Move to faster storage tier |

### Emergency Triggers
- **Circuit breaker trips** → Scale out immediately, investigate root cause.
- **Health check failures** → Replace node, scale out if > 10% unhealthy.
- **Dependency degradation** → Shed non-critical load, scale critical path.

## 4. Cost Optimization

### Right-Sizing
- Review instance utilization weekly; downsize anything < 40% average CPU for 2+ weeks.
- Use burstable instances for dev/test; reserved for stable production baselines.

### Purchasing Strategies
| Commitment | Discount | Best For |
|------------|----------|----------|
| On-Demand | 0% | Spiky, unpredictable workloads |
| Reserved (1yr) | ~30–40% | Stable baseline capacity |
| Reserved (3yr) | ~50–60% | Confident long-term workloads |
| Spot/Preemptible | ~60–90% | Fault-tolerant, interruptible jobs |

### Architectural Savings
- **Caching:** Reduce database load 40–60% with Redis/Memcached for hot reads.
- **CDN:** Offload static assets; reduces origin bandwidth 70–90%.
- **Compression:** Enable gzip/brotli; cuts egress costs 30–50%.
- **Data tiering:** Move cold data to object storage (S3/GCS) after 30–90 days.
- **Serverless:** Use for spiky, event-driven workloads with < 20% average utilization.

### Waste Elimination
- Tag all resources by team/project; audit untagged resources monthly.
- Automate dev/test environment shutdown outside business hours.
- Delete orphaned volumes, snapshots, and load balancers.
- Set budget alerts at 50%, 80%, and 100% of monthly forecast.

## 5. Monitoring Metrics

### Golden Signals (per service)
| Signal | Metric | Warning | Critical |
|--------|--------|---------|----------|
| Latency | p50/p95/p99 response time | p99 > 200ms | p99 > 500ms |
| Traffic | Requests/sec, bytes/sec | > 2× baseline | > 3× baseline |
| Errors | Error rate, error budget burn | > 0.1% | > 1% |
| Saturation | CPU, memory, disk, connections | > 70% | > 85% |

### Resource Metrics
- **CPU:** utilization %, throttling count, load average.
- **Memory:** utilization %, swap usage, OOM kill count.
- **Disk:** utilization %, IOPS, throughput, I/O wait %.
- **Network:** bandwidth in/out, packet loss, connection count, retransmits.

### Application Metrics
- **Throughput:** requests/min, jobs/min, messages/min.
- **Queue depth:** pending jobs, consumer lag.
- **Dependency health:** downstream latency, error rates, timeout rates.
- **Business KPIs:** active users, transactions/min, revenue/min (correlate with infra).

### Capacity-Specific Metrics
- **Headroom:** `(current_capacity - current_load) / current_capacity` — alert if < 20%.
- **Forecast accuracy:** `|actual - forecast| / forecast` — track to improve models.
- **Cost per transaction:** `monthly_cost / total_transactions` — trend over time.
- **Resource waste:** idle instances, unattached volumes, over-provisioned storage.

### Alerting Best Practices
- Alert on symptoms (latency, errors), not causes (CPU) — CPU is a proxy.
- Use multi-window, multi-burn-rate alerts to reduce noise.
- Page only for user-impact issues; ticket for capacity risks.
- Run game days quarterly to validate scaling and failover behavior.

---

*Review this guide quarterly and after any major architecture change.*
