# APEX-OS Business Platform — SLA/SLO Framework

| Field | Value |
|---|---|
| **Document Version** | 1.0.0 |
| **Effective Date** | 2026-10-01 |
| **Owner** | APEX-OS Platform Engineering |
| **Review Cycle** | Quarterly |
| **Classification** | Internal — Engineering & Operations |

---

## Table of Contents

1. [Purpose & Scope](#1-purpose--scope)
2. [Definitions & Conventions](#2-definitions--conventions)
3. [Service Tiers](#3-service-tiers)
4. [Availability SLA](#4-availability-sla)
5. [Performance SLA](#5-performance-sla)
6. [Recovery SLA (RTO / RPO)](#6-recovery-sla-rto--rpo)
7. [Support SLA](#7-support-sla)
8. [Compliance SLA](#8-compliance-sla)
9. [Error Budgets & Burn Rate Alerts](#9-error-budgets--burn-rate-alerts)
10. [Measurement & Reporting](#10-measurement--reporting)
11. [Exclusions & Force Majeure](#11-exclusions--force-majeure)
12. [Escalation Matrix](#12-escalation-matrix)
13. [Document History](#13-document-history)

---

## 1. Purpose & Scope

This document defines the Service Level Agreements (SLAs) and Service Level Objectives (SLOs) for the **APEX-OS Business Platform** — a multi-cloud, Kubernetes-orchestrated enterprise platform spanning AWS, Azure, and GCP.

### 1.1 In Scope

| Layer | Components |
|---|---|
| **Compute** | EKS (AWS), AKS (Azure), GKE (GCP) clusters; worker nodes; control planes |
| **Data** | RDS PostgreSQL (Multi-AZ), S3, Azure Blob, GCP Cloud Storage, backups |
| **Networking** | VPC/VNet, subnets, load balancers, Istio service mesh, cert-manager, WAF |
| **Observability** | Prometheus, Grafana, Alertmanager, Loki, Tempo |
| **Security** | GuardDuty, Security Hub, VPC Flow Logs, encryption at rest/in transit |
| **API & Ingress** | Public-facing APIs, internal service-to-service endpoints, ingress controllers |

### 1.2 Out of Scope

- Third-party SaaS dependencies (e.g., Snowflake, Salesforce) — governed by their own SLAs
- Customer-managed client-side infrastructure (CDN edge, corporate firewalls)
- Development and staging environments (best-effort, no SLA)

---

## 2. Definitions & Conventions

| Term | Definition |
|---|---|
| **SLA** | Service Level Agreement — contractual commitment with financial penalty for breach |
| **SLO** | Service Level Objective — internal target, typically tighter than the SLA |
| **SLI** | Service Level Indicator — measured metric (e.g., success ratio, latency) |
| **Error Budget** | 1 − SLO; the allowable "downtime" before corrective action is mandated |
| **Burn Rate** | Rate at which the error budget is consumed over a sliding window |
| **RTO** | Recovery Time Objective — maximum acceptable time to restore service after failure |
| **RPO** | Recovery Point Objective — maximum acceptable data loss measured in time |
| **MTTR** | Mean Time To Restore — average time from detection to resolution |
| **MTTD** | Mean Time To Detect — average time from incident start to detection |
| **MTBF** | Mean Time Between Failures — average time between service failures |
| **Downtime** | Any period where the service is unavailable or materially degraded, measured as the percentage of failed requests or unreachable endpoints |

### 2.1 Measurement Windows

| Window | Duration | Use Case |
|---|---|---|
| **Rolling 7-day** | 7 × 24 h | Burn-rate alerting, trend detection |
| **Rolling 30-day** | 30 × 24 h | SLA compliance reporting, error budget tracking |
| **Calendar Month** | 1st – last day | Customer-facing SLA reports, billing adjustments |

---

## 3. Service Tiers

APEX-OS classifies workloads into three tiers. Each tier carries a distinct SLA/SLO profile.

| Tier | Description | Example Workloads | Availability SLA | Availability SLO |
|---|---|---|---|---|
| **Tier 1 — Mission Critical** | Revenue-impacting, customer-facing, or safety-critical | Public APIs, auth service, payment processing, data plane | 99.99% | 99.995% |
| **Tier 2 — Business Critical** | Internal tools, dashboards, reporting, non-customer-facing | Admin console, analytics pipeline, internal microservices | 99.95% | 99.97% |
| **Tier 3 — Standard** | Dev tools, batch jobs, non-utility services | CI/CD runners, log processors, staging mirrors | 99.9% | 99.95% |

---

## 4. Availability SLA

### 4.1 Uptime Targets by Tier

| Tier | SLA Target | SLO Target | Max Downtime / Month (SLA) | Max Downtime / Month (SLO) |
|---|---|---|---|---|
| **Tier 1** | 99.99% | 99.995% | 4.38 min | 2.19 min |
| **Tier 2** | 99.95% | 99.97% | 21.9 min | 13.1 min |
| **Tier 3** | 99.9% | 99.95% | 43.8 min | 21.9 min |

> **Calculation basis:** 30-day month = 43,200 minutes. Downtime = (1 − availability) × 43,200.

### 4.2 Availability SLI Definition

```
Availability SLI = (Total Requests − Failed Requests) / Total Requests
```

- **Failed requests** = HTTP 5xx responses, connection timeouts (> 30 s), TLS handshake failures
- **Excluded** = HTTP 4xx (client errors), planned maintenance windows (with ≥ 72 h notice), force majeure

### 4.3 Multi-Cloud Availability Architecture

| Component | Redundancy Model | Failure Domain |
|---|---|---|
| **Kubernetes (EKS/AKS/GKE)** | Multi-AZ node pools, cluster autoscaler (min 2, max 6 nodes) | AZ-level |
| **RDS PostgreSQL** | Multi-AZ with synchronous standby | AZ-level |
| **Object Storage (S3/Blob/GCS)** | Cross-region replication, versioning | Region-level |
| **Istio Service Mesh** | Multi-replica control plane, locality-aware routing | Pod-level |
| **Load Balancers** | Cloud-provider native ALB/NLB with health checks | AZ-level |
| **DNS / Ingress** | Route 53 / Azure DNS / Cloud DNS with health-checked failover | Region-level |

### 4.4 Planned Maintenance

| Parameter | Value |
|---|---|
| **Notice period** | ≥ 72 hours for Tier 1; ≥ 24 hours for Tier 2/3 |
| **Maintenance window** | Saturday 02:00–06:00 UTC (low-traffic window) |
| **Max duration** | 4 hours per window |
| **Frequency** | ≤ 2 windows per month for Tier 1 |
| **Impact** | Zero-downtime deployments via rolling updates; maintenance does not count against SLA |

---

## 5. Performance SLA

### 5.1 Latency Targets by Tier

All latency measurements are **server-side** (ingress to response), measured at the edge load balancer.

| Tier | p50 | p95 | p99 | p99.9 |
|---|---|---|---|---|
| **Tier 1** | ≤ 50 ms | ≤ 200 ms | ≤ 500 ms | ≤ 1,000 ms |
| **Tier 2** | ≤ 100 ms | ≤ 400 ms | ≤ 1,000 ms | ≤ 2,000 ms |
| **Tier 3** | ≤ 200 ms | ≤ 800 ms | ≤ 2,000 ms | ≤ 4,000 ms |

### 5.2 Throughput Targets

| Tier | Min Throughput | Burst Capacity |
|---|---|---|
| **Tier 1** | 10,000 RPS sustained | 50,000 RPS (auto-scaled) |
| **Tier 2** | 2,000 RPS sustained | 10,000 RPS |
| **Tier 3** | 500 RPS sustained | 2,000 RPS |

### 5.3 Performance SLI Definitions

| SLI | Definition | Measurement |
|---|---|---|
| **Latency** | Time from request receipt to final byte of response | Prometheus histogram at ingress |
| **Throughput** | Successful requests per second | Prometheus counter at ingress |
| **Error Ratio** | Failed requests / total requests | Prometheus counter at ingress |
| **Saturation** | CPU, memory, disk I/O utilization | Node exporter + cAdvisor |
| **DNS Resolution** | Time to resolve platform domains | External probe (global) |
| **TLS Handshake** | Time to complete TLS negotiation | External probe (global) |

### 5.4 Performance Degradation Thresholds

| Severity | Trigger | Action |
|---|---|---|
| **Warning** | p95 exceeds SLO for 5 consecutive minutes | Page on-call engineer; investigate |
| **Critical** | p99 exceeds SLO for 3 consecutive minutes | Auto-scale + page; consider circuit-breaking |
| **Emergency** | p99 exceeds 2× SLO for 1 minute | Failover to secondary region; executive notification |

---

## 6. Recovery SLA (RTO / RPO)

### 6.1 Recovery Objectives by Tier

| Tier | RTO (SLA) | RTO (SLO) | RPO (SLA) | RPO (SLO) |
|---|---|---|---|---|
| **Tier 1** | ≤ 15 min | ≤ 5 min | ≤ 1 min | ≤ 15 sec |
| **Tier 2** | ≤ 1 hour | ≤ 15 min | ≤ 15 min | ≤ 5 min |
| **Tier 3** | ≤ 4 hours | ≤ 1 hour | ≤ 1 hour | ≤ 15 min |

### 6.2 Recovery Scenarios & Procedures

| Scenario | Detection | Automated Response | Manual Escalation |
|---|---|---|---|
| **Single pod failure** | Liveness probe (3 strikes) | Kubernetes reschedules pod | None — fully automated |
| **Node failure** | Node NotReady (2 min) | Cluster autoscaler provisions replacement; pods rescheduled | If > 50% nodes lost → page |
| **AZ failure** | Health check failures across AZ | Traffic shifted to healthy AZs via Route 53 / Azure Traffic Manager | If multi-AZ fails → region failover |
| **Region failure** | External probe failure (3 regions) | DNS failover to secondary region; RDS cross-region read replica promoted | Executive + customer notification |
| **Data corruption** | Anomaly detection on write patterns | Point-in-time recovery from RDS snapshots; S3 versioning restore | Data engineering team engaged |
| **Complete platform loss** | All probes failing | Disaster recovery runbook executed; infrastructure-as-code redeploy | Full incident command activated |

### 6.3 Backup & Restore

| Data Store | Backup Frequency | Retention | Encryption | Cross-Region |
|---|---|---|---|---|
| **RDS PostgreSQL** | Continuous (WAL archiving) + daily snapshots | 35 days (snapshots), 7 days (WAL) | AES-256 | Yes — secondary region |
| **S3 / Blob / GCS** | Versioned (continuous) + daily cross-region sync | 90 days (versions), 35 days (snapshots) | AES-256 / CMEK | Yes — paired region |
| **Kubernetes etcd** | Every 6 hours | 30 days | AES-256 | Yes — S3/GCS |
| **Istio / cert-manager config** | GitOps (ArgoCD) — every change | Indefinite (Git history) | Sealed Secrets | Yes — multi-region Git |
| **Monitoring data (Prometheus)** | 15s scrape interval | 30 days (local), 1 year (object storage) | At-rest via S3/Blob | Yes — Thanos/Cortex |

### 6.4 Disaster Recovery Runbook

The full DR runbook is maintained at `docs/runbooks/disaster-recovery.md` and tested quarterly via game-day exercises.

| DR Exercise | Frequency | Scope | Success Criteria |
|---|---|---|---|
| **Tabletop** | Quarterly | Scenario walkthrough | All stakeholders understand roles |
| **Functional** | Semi-annually | Single-component failover | RTO/RPO met in test |
| **Full-scale** | Annually | Complete region failover | RTO ≤ 15 min, RPO ≤ 1 min for Tier 1 |

---

## 7. Support SLA

### 7.1 Severity Levels

| Severity | Description | Examples |
|---|---|---|
| **SEV-1 — Critical** | Complete service outage or data loss; no workaround | Platform down, all APIs returning 500, data corruption |
| **SEV-2 — High** | Major feature degraded; limited workaround exists | Single AZ failure, elevated error rates, latency > 2× SLO |
| **SEV-3 — Medium** | Partial degradation; workaround available | Non-critical feature broken, single node failure |
| **SEV-4 — Low** | Minor issue, cosmetic, or general inquiry | Documentation request, feature request, UI glitch |

### 7.2 Response & Resolution Time Commitments

| Severity | Response Time (SLA) | Resolution Time (SLA) | Response Time (SLO) | Resolution Time (SLO) |
|---|---|---|---|---|
| **SEV-1** | ≤ 15 min | ≤ 4 hours | ≤ 5 min | ≤ 1 hour |
| **SEV-2** | ≤ 30 min | ≤ 8 hours | ≤ 15 min | ≤ 4 hours |
| **SEV-3** | ≤ 4 hours | ≤ 3 business days | ≤ 1 hour | ≤ 1 business day |
| **SEV-4** | ≤ 1 business day | ≤ 10 business days | ≤ 4 hours | ≤ 5 business days |

### 7.3 Support Channels

| Channel | Availability | Use For |
|---|---|---|
| **PagerDuty (on-call)** | 24 × 7 × 365 | SEV-1, SEV-2 |
| **Slack #apex-os-support** | Business hours (follow-the-sun) | SEV-3, SEV-4 |
| **Email support@apex-os.io** | Business hours | SEV-3, SEV-4 |
| **Status page (status.apex-os.io)** | 24 × 7 (public) | Incident communication, scheduled maintenance |
| **Emergency hotline** | 24 × 7 × 365 | SEV-1 executive escalation |

### 7.4 On-Call Rotation

| Role | Coverage | Escalation Path |
|---|---|---|
| **L1 — Tier 1 Support** | 24 × 7 (follow-the-sun: US → EU → APAC) | L1 → L2 after 15 min if unresolved |
| **L2 — Platform Engineer** | 24 × 7 (PagerDuty) | L2 → L3 after 30 min if unresolved |
| **L3 — Senior / Staff Engineer** | Business hours + on-call escalation | L3 → Engineering Manager after 1 hour |
| **Incident Commander** | Activated for SEV-1 | IC → VP Engineering → CTO |

### 7.5 Customer Communication

| Incident Severity | Initial Update | Update Frequency | Post-Incident Review |
|---|---|---|---|
| **SEV-1** | Within 15 min of detection | Every 30 min during active incident | Within 48 hours — blameless postmortem |
| **SEV-2** | Within 1 hour of detection | Every 2 hours during active incident | Within 5 business days |
| **SEV-3** | Within 4 hours | Daily until resolved | Within 10 business days |
| **SEV-4** | Within 1 business day | Weekly until resolved | Optional |

---

## 8. Compliance SLA

### 8.1 Audit & Assessment Schedule

| Audit Type | Frequency | Scope | Owner |
|---|---|---|---|
| **Internal security audit** | Quarterly | IAM policies, network policies, secrets management, RBAC | Security Engineering |
| **External penetration test** | Semi-annually | External-facing APIs, ingress endpoints, WAF rules | Third-party firm |
| **SOC 2 Type II** | Annually | Security, availability, confidentiality, privacy | External auditor |
| **ISO 27001 surveillance** | Annually | ISMS controls, risk register, statement of applicability | External auditor |
| **PCI DSS (if applicable)** | Quarterly ASV scan + annual QSA | Cardholder data environment, network segmentation | QSA / ASV vendor |
| **Vulnerability scan (DAST)** | Weekly | All public-facing endpoints | Security Engineering |
| **Vulnerability scan (SAST)** | Every commit (CI) | All application code | DevSecOps pipeline |
| **Container image scan** | Every build + weekly rescan | All container images (Trivy/Grype) | DevSecOps pipeline |
| **Infrastructure-as-code scan** | Every PR | Terraform, Helm, Kubernetes manifests (Checkov/tfsec) | DevSecOps pipeline |
| **Compliance posture (CSPM)** | Continuous | AWS Security Hub, Azure Defender, GCP Security Command Center | Security Engineering |
| **Access review** | Quarterly | All IAM roles, Kubernetes RBAC, database grants | Security + Engineering |
| **Log review** | Continuous (automated) + monthly manual | Audit logs, VPC Flow Logs, K8s audit logs | Security Engineering |

### 8.2 Reporting & Deliverables

| Report | Frequency | Audience | Delivery |
|---|---|---|---|
| **SLA compliance report** | Monthly | Customers, leadership | Email + customer portal |
| **Error budget status** | Weekly | Engineering leadership | Internal dashboard |
| **Security posture report** | Monthly | CISO, security team | Internal dashboard + email |
| **Vulnerability remediation report** | Bi-weekly | Engineering, security | Jira dashboard |
| **Compliance certification** | Annually | Customers, auditors | Customer portal |
| **Incident postmortem** | Per SEV-1/SEV-2 | Engineering, leadership | Confluence + email |
| **DR test report** | Per exercise | Engineering, leadership | Confluence |
| **Change advisory board (CAB) minutes** | Weekly | Engineering, operations | Confluence |

### 8.3 Data Retention & Privacy

| Data Type | Retention Period | Standard |
|---|---|---|
| **Application logs** | 90 days hot, 1 year cold (object storage) | GDPR Art. 5(1)(e) |
| **Audit logs** | 7 years | SOC 2 CC7.2, ISO 27001 A.12.4 |
| **Monitoring metrics** | 30 days high-res, 1 year downsampled | Internal policy |
| **Tracing data** | 30 days | Internal policy |
| **Backup data** | 35 days (RDS), 90 days (object storage) | Internal policy |
| **Customer data** | Per contract + 30 days post-termination | GDPR, CCPA |
| **Support tickets** | 3 years | Internal policy |

### 8.4 Compliance Controls Mapping

| Control Domain | Key Controls | Verification |
|---|---|---|
| **Access Control** | RBAC, least privilege, MFA enforced, quarterly access reviews | AWS IAM Access Analyzer, Azure PIM, GCP IAM |
| **Encryption** | TLS 1.3 in transit, AES-256 at rest, KMS/CMEK key rotation (90 days) | AWS KMS, Azure Key Vault, GCP Cloud KMS |
| **Network Security** | Security groups, NACLs, private subnets, WAF, DDoS protection | AWS WAF, Shield, GuardDuty, VPC Flow Logs |
| **Secrets Management** | HashiCorp Vault / AWS Secrets Manager, automatic rotation (30 days) | Vault audit logs |
| **Change Management** | GitOps (ArgoCD), PR approval, automated CI/CD, rollback capability | ArgoCD audit logs |
| **Incident Response** | Runbooks, PagerDuty, blameless postmortem, game-day exercises | Postmortem docs, game-day reports |
| **Data Protection** | Encryption, backup, DR, data classification, DLP | Backup verification tests, DR exercises |

---

## 9. Error Budgets & Burn Rate Alerts

### 9.1 Error Budget Calculation

```
Error Budget = 1 − SLO Target

Example (Tier 1, 30-day window):
  SLO = 99.995%
  Error Budget = 0.005% = 0.00005
  Total requests (30 days) = 100,000,000
  Budget = 100,000,000 × 0.00005 = 5,000 failed requests
```

### 9.2 Burn Rate Alerting

| Burn Rate | Window | Alert Threshold | Action |
|---|---|---|---|
| **Fast burn** | 1 hour | Budget consumed ≥ 2% in 1 hour | Page on-call; freeze deployments |
| **Fast burn** | 6 hours | Budget consumed ≥ 5% in 6 hours | Page on-call; incident review |
| **Slow burn** | 3 days | Budget consumed ≥ 10% in 3 days | Engineering leadership notified; reliability review |
| **Exhausted** | 30 days | Budget = 0 | Deployment freeze; all hands on reliability |

### 9.3 Error Budget Policy

| Budget Status | Policy |
|---|---|
| **> 50% remaining** | Normal operations; standard deployment cadence |
| **20–50% remaining** | Caution; require additional review for risky deployments |
| **< 20% remaining** | Deployment freeze for non-critical changes; reliability sprint planned |
| **0% (exhausted)** | Full deployment freeze; all engineering effort on reliability until budget recovers |

---

## 10. Measurement & Reporting

### 10.1 Observability Stack

| Layer | Tool | Metrics |
|---|---|---|
| **Metrics** | Prometheus + Thanos (long-term) | SLI/SLO metrics, burn rate, saturation |
| **Dashboards** | Grafana | Real-time SLO dashboards per tier |
| **Logging** | Loki + ELK | Application logs, audit logs, error logs |
| **Tracing** | Tempo / Jaeger | Distributed traces, latency breakdown |
| **Alerting** | Alertmanager + PagerDuty | SLO burn rate alerts, SLA breach alerts |
| **Synthetic** | External probes (global) | Availability, latency, DNS, TLS from outside |
| **Status** | Statuspage.io | Customer-facing status page |

### 10.2 SLO Dashboard Panels

Each tier has a dedicated Grafana dashboard showing:

1. **Availability** — rolling 30-day success ratio vs. SLO
2. **Latency** — p50, p95, p99, p99.9 vs. SLO thresholds
3. **Error budget** — remaining budget, burn rate (1h, 6h, 3d windows)
4. **Throughput** — RPS vs. capacity
5. **Saturation** — CPU, memory, disk, network per component
6. **Incident timeline** — active and recent incidents

### 10.3 SLA Breach & Penalty

| SLA Metric | Breach Threshold | Penalty |
|---|---|---|
| **Availability** | Below SLA target for 3 consecutive months | Service credit: 10% of monthly fee per 0.01% below SLA |
| **Availability** | Below SLA target for 6 consecutive months | Service credit: 25% + right to terminate |
| **Performance (p99)** | Exceeds SLA for 5 consecutive days | Service credit: 5% of monthly fee |
| **Recovery (RTO)** | Exceeds RTO in any SEV-1 incident | Service credit: 15% of monthly fee |
| **Recovery (RPO)** | Exceeds RPO in any incident | Service credit: 25% of monthly fee + mandatory RCA |
| **Support (response)** | Exceeds response SLA for SEV-1 | Escalation to VP Engineering; service credit: 5% |

> **Penalty cap:** Total service credits shall not exceed 50% of the monthly service fee.

---

## 11. Exclusions & Force Majeure

### 11.1 SLA Exclusions

The following are **not** counted against SLA calculations:

1. **Planned maintenance** — with ≥ 72 h notice for Tier 1, ≥ 24 h for Tier 2/3
2. **Client-side failures** — DNS misconfiguration, expired client certificates, client network issues
3. **Third-party dependencies** — cloud provider outages outside APEX-OS control (e.g., AWS region-wide failure), SaaS provider outages
4. **Force majeure** — natural disasters, war, terrorism, government action, pandemics
5. **Abuse or misuse** — DDoS attacks (where Shield/WAF is enabled), API abuse, exceeding documented rate limits
6. **Beta / preview features** — explicitly labeled as such; best-effort only
7. **Customer-requested changes** — configuration changes that degrade performance or availability

### 11.2 Cloud Provider SLA Reference

| Provider | Service | SLA |
|---|---|---|
| **AWS** | EKS | 99.95% |
| **AWS** | RDS Multi-AZ | 99.95% |
| **AWS** | S3 Standard | 99.9% |
| **Azure** | AKS | 99.95% (with Uptime SLA) |
| **Azure** | Blob Storage | 99.9% |
| **GCP** | GKE | 99.95% (Regional) |
| **GCP** | Cloud Storage | 99.9% |

> APEX-OS SLA commitments are **independent** of cloud provider SLAs. In the event of a cloud provider SLA breach, APEX-OS will pass through any service credits received from the provider.

---

## 12. Escalation Matrix

| Level | Trigger | Escalate To | Timeframe |
|---|---|---|---|
| **L1** | Initial alert | On-call engineer (PagerDuty) | Immediate |
| **L2** | Unresolved after 15 min (SEV-1) or 30 min (SEV-2) | Senior platform engineer | Automatic |
| **L3** | Unresolved after 30 min (SEV-1) or 1 hour (SEV-2) | Engineering manager | Automatic |
| **L4** | Unresolved after 1 hour (SEV-1) or 4 hours (SEV-2) | VP Engineering | Automatic |
| **L5** | Unresolved after 4 hours (SEV-1) | CTO | Automatic |
| **Customer** | SEV-1 declared | Customer success + status page | Within 15 min |
| **Executive** | SEV-1 unresolved > 2 hours | CEO + board notification | Automatic |

---

## 13. Document History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0.0 | 2026-10-01 | APEX-OS Platform Engineering | Initial release |

---

## Appendix A: Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│              APEX-OS SLA/SLO QUICK REFERENCE            │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│  Metric  │  Tier 1  │  Tier 2  │  Tier 3  │   Unit      │
├──────────┼──────────┼──────────┼──────────┼─────────────┤
│ Avail.   │ 99.99%   │ 99.95%   │ 99.9%    │ per month   │
│ p50      │ ≤ 50ms   │ ≤ 100ms  │ ≤ 200ms  │ latency     │
│ p95      │ ≤ 200ms  │ ≤ 400ms  │ ≤ 800ms  │ latency     │
│ p99      │ ≤ 500ms  │ ≤ 1000ms │ ≤ 2000ms │ latency     │
│ RTO      │ ≤ 15min  │ ≤ 1hr    │ ≤ 4hrs   │ recovery    │
│ RPO      │ ≤ 1min   │ ≤ 15min  │ ≤ 1hr    │ data loss   │
│ SEV-1    │ ≤ 15min  │ ≤ 30min  │ ≤ 4hrs   │ response    │
│ SEV-1    │ ≤ 4hrs   │ ≤ 8hrs   │ ≤ 3days  │ resolution  │
└──────────┴──────────┴──────────┴──────────┴─────────────┘
```

---

## Appendix B: SLI Query Examples (PromQL)

```promql
# Availability SLI (rolling 30 days)
1 - (
  sum(increase(http_requests_total{status=~"5.."}[30d]))
  /
  sum(increase(http_requests_total[30d]))
)

# p99 latency (rolling 30 days)
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket[30d])) by (le)
)

# Error budget remaining (Tier 1)
1 - (
  (
    sum(increase(http_requests_total{status=~"5.."}[30d]))
    /
    sum(increase(http_requests_total[30d]))
  )
  / 0.00005
)

# Burn rate (1-hour window)
(
  sum(increase(http_requests_total{status=~"5.."}[1h]))
  /
  sum(increase(http_requests_total[1h]))
)
/
0.00005
```

---

*End of document.*
