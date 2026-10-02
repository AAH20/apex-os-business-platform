# APEX-OS Business Platform — Disaster Recovery Plan

**Version:** 1.0  
**Last Updated:** 2026-10-01  
**Owner:** Platform Engineering  
**Classification:** Internal  
**Review Cycle:** Quarterly

---

## Table of Contents

1. [Purpose & Scope](#1-purpose--scope)
2. [DR Strategy Overview](#2-dr-strategy-overview)
3. [Backup Strategy](#3-backup-strategy)
4. [Replication Strategy](#4-replication-strategy)
5. [Failover Strategy](#5-failover-strategy)
6. [RTO / RPO Targets](#6-rto--rpo-targets)
7. [DR Testing](#7-dr-testing)
8. [DR Automation](#8-dr-automation)
9. [DR Monitoring](#9-dr-monitoring)
10. [Roles & Responsibilities](#10-roles--responsibilities)
11. [Runbooks & Escalation](#11-runbooks--escalation)
12. [Appendices](#12-appendices)

---

## 1. Purpose & Scope

This document defines the Disaster Recovery (DR) plan for the APEX-OS Business Platform. It establishes the strategy, targets, testing cadence, automation, and monitoring required to ensure business continuity in the event of a disaster.

**In scope:**
- All production infrastructure (compute, storage, networking)
- Primary and secondary data stores (PostgreSQL, Redis, object storage)
- Message queues and event streams (Kafka)
- API gateway and microservices
- Authentication and identity services
- CI/CD pipelines and artifact repositories
- Observability stack (metrics, logs, traces)
- DNS and CDN configurations

**Out of scope:**
- Development and staging environments (covered by separate environment management policies)
- Third-party SaaS dependencies (covered by vendor SLAs)
- End-user devices and client-side state

---

## 2. DR Strategy Overview

APEX-OS employs a **multi-tier DR architecture** based on criticality:

| Tier | Description | Architecture | Typical RTO |
|------|-------------|-------------|-------------|
| **Tier 1 — Critical** | Core platform services (auth, API gateway, billing) | Active-Active multi-region | < 5 min |
| **Tier 2 — Essential** | Business logic services, data stores | Active-Passive with hot standby | < 30 min |
| **Tier 3 — Standard** | Supporting services, analytics, reporting | Active-Passive with warm standby | < 4 hours |
| **Tier 4 — Non-critical** | Batch jobs, internal tools, dev tooling | Cold standby / rebuild from IaC | < 24 hours |

**Recovery Site Topology:**

```
┌─────────────────────────────────────────────────────────┐
│                    Global Traffic Manager                │
│                  (Route 53 / Cloudflare)                 │
└────────────┬────────────────────────────┬───────────────┘
             │                            │
    ┌────────▼────────┐          ┌────────▼────────┐
    │  Primary Region  │          │  DR Region       │
    │  (us-east-1)     │          │  (us-west-2)     │
    │                  │          │                  │
    │  ┌────────────┐  │  Sync    │  ┌────────────┐  │
    │  │  Tier 1    │◄─┼──────────┼─►│  Tier 1    │  │
    │  │ (Active)   │  │ Replica  │  │ (Active)   │  │
    │  └────────────┘  │          │  └────────────┘  │
    │  ┌────────────┐  │  Async   │  ┌────────────┐  │
    │  │  Tier 2    │◄─┼──────────┼─►│  Tier 2    │  │
    │  │ (Primary)  │  │ Replica  │  │ (Standby)  │  │
    │  └────────────┘  │          │  └────────────┘  │
    │  ┌────────────┐  │  Async   │  ┌────────────┐  │
    │  │  Tier 3    │◄─┼──────────┼─►│  Tier 3    │  │
    │  │ (Primary)  │  │ Replica  │  │ (Standby)  │  │
    │  └────────────┘  │          │  └────────────┘  │
    └──────────────────┘          └──────────────────┘
```

---

## 3. Backup Strategy

### 3.1 Backup Schedule

| Data Source | Type | Frequency | Retention | Encryption |
|-------------|------|-----------|-----------|------------|
| PostgreSQL (OLTP) | Full | Daily (02:00 UTC) | 35 days | AES-256 |
| PostgreSQL (OLTP) | WAL archiving | Continuous | 7 days | AES-256 |
| PostgreSQL (OLTP) | Incremental | Every 6 hours | 14 days | AES-256 |
| Redis | RDB snapshot | Every 15 minutes | 7 days | AES-256 |
| Redis | AOF | Every 1 second (append) | 3 days | AES-256 |
| Object Storage (S3) | Versioned + Cross-region replication | Continuous | 90 days (versioned) | SSE-KMS |
| Kafka | Topic snapshot + log retention | Hourly snapshot | 7 days | AES-256 |
| etcd / K8s state | Full | Every 6 hours | 30 days | AES-256 |
| Secrets (Vault) | Raft snapshot | Every 1 hour | 90 days | AES-256-GCM |
| Configuration / IaC | Git commit | On every change | Indefinite | GPG-signed |

### 3.2 Backup Storage

- **Primary backup storage:** Same-region S3 bucket (or equivalent) with versioning enabled
- **Secondary backup storage:** Cross-region S3 bucket in DR region (replicated via S3 CRR)
- **Tertiary (air-gapped) backup:** Weekly snapshot to isolated account with Object Lock (WORM) for ransomware protection
- **Backup encryption:** All backups encrypted at rest with KMS-managed keys; keys stored in separate security account

### 3.3 Backup Validation

- **Automated restore tests:** Daily automated restore of a random backup subset to an isolated environment
- **Checksum verification:** SHA-256 checksums computed and verified on every backup
- **Backup catalog:** All backups indexed in a searchable catalog with metadata (timestamp, size, checksum, encryption key ID)
- **Restore drills:** Monthly full restore drill (see Section 7)

### 3.4 Backup Tooling

| Component | Tool | Configuration |
|-----------|------|---------------|
| PostgreSQL | pgBackRest / WAL-G | S3-compatible storage, parallel workers |
| Redis | redis-cli BGSAVE + S3 sync | Cron-based with locking |
| S3 | Native versioning + CRR | Lifecycle policies for cost optimization |
| Kafka | MirrorMaker 2 / custom | Topic-level replication |
| K8s / etcd | Velero | Namespace-scoped with hooks |
| Vault | Integrated Raft snapshot | Automated via cron |

---

## 4. Replication Strategy

### 4.1 Data Replication

| Data Store | Replication Mode | Lag Target | Mechanism |
|------------|-----------------|------------|-----------|
| PostgreSQL | Synchronous (same region) | 0 (zero data loss) | Streaming replication |
| PostgreSQL | Asynchronous (cross-region) | < 5 seconds | Logical replication / WAL shipping |
| Redis | Asynchronous (cross-region) | < 1 second | Redis Sentinel + replica |
| S3 / Object Storage | Cross-region | < 15 minutes | S3 Cross-Region Replication |
| Kafka | Active-Active (MM2) | < 2 seconds | MirrorMaker 2 bidirectional |
| etcd | Multi-region Raft | < 100ms | Built-in Raft consensus |

### 4.2 Replication Topology

```
Primary Region (us-east-1)                DR Region (us-west-2)
┌─────────────────────────┐              ┌─────────────────────────┐
│  PostgreSQL Primary     │───Sync──────►│  PostgreSQL Standby     │
│  (read-write)           │              │  (read-only, promotable)│
│                         │              │                         │
│  Redis Primary          │───Async─────►│  Redis Replica          │
│  (read-write)           │              │  (read-only)            │
│                         │              │                         │
│  Kafka Cluster A        │◄──MM2──────►│  Kafka Cluster B        │
│  (active)               │  (bidirect.) │  (active)               │
│                         │              │                         │
│  S3 Bucket (primary)    │───CRR──────►│  S3 Bucket (replica)    │
│  (versioned)            │              │  (versioned)            │
└─────────────────────────┘              └─────────────────────────┘
```

### 4.3 Replication Monitoring

- Replication lag monitored via Prometheus metrics (`pg_stat_replication`, `redis_replication_lag`, `kafka_consumer_lag`)
- Alerts fire when lag exceeds thresholds (see Section 9)
- Automatic replication health checks every 60 seconds

---

## 5. Failover Strategy

### 5.1 Failover Types

| Type | Description | Trigger | Automation Level |
|------|-------------|---------|-----------------|
| **Automatic** | System-initiated without human intervention | Health check failure, replication lag breach | Fully automated |
| **Semi-automated | System prepares failover, human confirms | Regional degradation, elevated error rates | One-click approval |
| **Manual** | Human-initiated full failover | Complete regional loss, security incident | Runbook-driven |

### 5.2 Failover Procedures

#### 5.2.1 Tier 1 — Automatic Failover (Active-Active)

1. Global Traffic Manager detects regional health check failure
2. DNS TTL (30 seconds) expires; traffic routed to DR region
3. DR region Tier 1 services already serving traffic (active-active)
4. **No data loss** — synchronous replication ensures consistency
5. **RTO: < 5 minutes** (DNS propagation + health check interval)

#### 5.2.2 Tier 2 — Semi-Automated Failover (Active-Passive)

1. Monitoring detects primary region degradation
2. Alert fires to on-call engineer via PagerDuty
3. On-call engineer assesses and approves failover via dashboard
4. Automation executes:
   a. Promote PostgreSQL standby to primary (`pg_promote()`)
   b. Promote Redis replica to primary
   c. Update Kafka consumer group offsets
   d. Switch DNS to DR region
   e. Verify service health in DR region
5. **RTO: < 30 minutes** (including human decision time)

#### 5.2.3 Tier 3 — Manual Failover (Active-Passive Warm)

1. On-call engineer initiates failover via runbook
2. Automation provisions warm standby resources
3. Data restored from latest cross-region replica
4. Services started in dependency order
5. Health checks verified
6. DNS updated
7. **RTO: < 4 hours**

#### 5.2.4 Tier 4 — Cold Standby Rebuild

1. Infrastructure provisioned from Terraform / Pulumi
2. Data restored from latest backup
3. Services deployed from container registry
4. Configuration applied from Git
5. **RTO: < 24 hours**

### 5.3 Failback Procedure

1. Verify primary region infrastructure is healthy
2. Re-establish replication from DR to primary (reverse direction)
3. Allow replication to catch up (verify lag = 0)
4. Switch DNS back to primary region
5. Verify service health in primary region
6. Demote DR region to standby
7. **Failback RTO: < 1 hour** (for Tier 1-2)

### 5.4 Split-Brain Prevention

- **Fencing:** STONITH (Shoot The Other Node In The Head) via cloud provider API
- **Quorum:** Distributed consensus via etcd / Consul for leader election
- **DNS TTL:** Low TTL (30s) to minimize stale routing
- **Health checks:** Multi-layer (L4 TCP, L7 HTTP, application-level)

---

## 6. RTO / RPO Targets

### 6.1 Service-Level Targets

| Service | Tier | RTO | RPO | Justification |
|---------|------|-----|-----|---------------|
| API Gateway | 1 | 5 min | 0 (zero) | Customer-facing; synchronous replication |
| Authentication / SSO | 1 | 5 min | 0 (zero) | Blocks all access if down |
| Billing / Payments | 1 | 5 min | 0 (zero) | Revenue-critical; transactional integrity |
| Core Business Logic | 2 | 30 min | < 5 sec | Async replication; near-zero loss |
| PostgreSQL (OLTP) | 2 | 30 min | < 5 sec | Async cross-region replication |
| Redis (Cache/Session) | 2 | 30 min | < 1 sec | Async replication; cache rebuildable |
| Kafka (Event Stream) | 2 | 30 min | < 2 sec | MM2 bidirectional replication |
| Analytics / Reporting | 3 | 4 hours | < 1 hour | Batch-rebuildable; non-real-time |
| Notification Service | 3 | 4 hours | < 1 hour | Retry-able; non-blocking |
| Search Index | 3 | 4 hours | < 1 hour | Rebuildable from source data |
| Batch Processing | 4 | 24 hours | < 24 hours | Re-runnable; non-time-sensitive |
| Internal Tools | 4 | 24 hours | < 24 hours | Non-customer-facing |

### 6.2 RTO/RPO Definitions

- **RTO (Recovery Time Objective):** Maximum acceptable time from disaster declaration to service restoration
- **RPO (Recovery Point Objective):** Maximum acceptable data loss measured in time (e.g., RPO of 5 seconds means at most 5 seconds of data may be lost)

### 6.3 Measurement & Reporting

- RTO measured from disaster declaration timestamp to first successful health check in DR region
- RPO measured from last committed transaction timestamp to disaster declaration timestamp
- Monthly DR metrics report generated and reviewed in SRE meeting
- Quarterly RTO/RPO compliance review against targets

---

## 7. DR Testing

### 7.1 Testing Schedule

| Test Type | Frequency | Duration | Scope | Participants |
|-----------|-----------|----------|-------|-------------|
| **Tabletop Exercise** | Monthly | 2 hours | Scenario walkthrough, decision-making | SRE, Product, Security |
| **Component Failover Test** | Bi-weekly | 1 hour | Single service failover | SRE team |
| **Full DR Drill** | Quarterly | 4-8 hours | Complete regional failover | All engineering |
| **Backup Restore Test** | Daily (automated) | 30 min | Random backup subset restore | Automated |
| **Chaos Engineering** | Weekly | 2 hours | Random failure injection | SRE + Engineering |
| **GameDay** | Semi-annually | Full day | Multi-failure scenario | All stakeholders |

### 7.2 Test Scenarios

| Scenario | Description | Expected Outcome |
|----------|-------------|-----------------|
| Single AZ loss | One availability zone becomes unavailable | Automatic failover to remaining AZs; no data loss |
| Regional loss | Entire primary region unreachable | Traffic routed to DR region; RTO < 5 min (Tier 1) |
| Database corruption | Data corruption detected in primary | Point-in-time recovery; RPO < 5 sec |
| Ransomware attack | Encryption of primary data stores | Restore from air-gapped backups; isolate affected systems |
| Network partition | Split-brain between regions | Quorum-based resolution; no dual-primary |
| DNS failure | DNS provider outage | Secondary DNS provider; manual IP update |
| Certificate expiry | TLS certificates expired | Automated cert renewal; fallback certs |
| Cascading failure | Multiple service dependencies fail | Circuit breakers engage; graceful degradation |

### 7.3 Test Execution Protocol

1. **Pre-test:**
   - Notify all stakeholders (minimum 48 hours for full DR drill)
   - Snapshot current state for comparison
   - Verify backup integrity
   - Confirm DR environment readiness

2. **Execution:**
   - Declare simulated disaster
   - Execute failover runbook
   - Monitor RTO/RPO metrics in real-time
   - Document all actions and timestamps

3. **Post-test:**
   - Verify data integrity (checksums, row counts)
   - Run smoke tests and integration tests
   - Measure actual RTO/RPO vs. targets
   - Document lessons learned
   - File improvement tickets for gaps
   - Update runbooks based on findings

### 7.4 Success Criteria

| Criterion | Target |
|-----------|--------|
| RTO met | 100% of services within target |
| RPO met | 100% of data stores within target |
| Data integrity | 100% checksum verification pass |
| Smoke tests | 100% pass rate |
| Rollback | Successful failback within target time |

---

## 8. DR Automation

### 8.1 Automation Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DR Automation Engine                      │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Health   │  │  Failover │  │  Backup  │  │  Restore │   │
│  │  Monitor  │  │  Engine  │  │  Manager │  │  Engine  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │              │              │              │         │
│       └──────────────┴──────────────┴──────────────┘         │
│                           │                                  │
│                    ┌──────▼──────┐                          │
│                    │  Event Bus   │                          │
│                    │  (Kafka)     │                          │
│                    └──────┬──────┘                          │
│                           │                                  │
│       ┌───────────────────┼───────────────────┐              │
│       │                   │                   │              │
│  ┌────▼────┐        ┌────▼────┐        ┌────▼────┐         │
│  │Terraform│        │  K8s    │        │  DNS    │         │
│  │  / IaC  │        │  Operator│        │  Manager│         │
│  └─────────┘        └─────────┘        └─────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Automated Failover Pipeline

```yaml
# failover-pipeline.yml
name: dr-failover
on:
  alert: regional_health_critical
  manual: workflow_dispatch

jobs:
  assess:
    steps:
      - check_primary_region_health
      - verify_dr_region_readiness
      - calculate_data_loss_estimate
      - notify_stakeholders

  decision:
    needs: assess
    steps:
      - if: tier1_service
        run: automatic_failover
      - if: tier2_service
        run: request_human_approval
        timeout: 10m
      - if: tier3_or_4
        run: create_incident_ticket

  execute:
    needs: decision
    steps:
      - promote_database_standby
      - promote_cache_replica
      - update_dns_records
      - restart_services_in_dr
      - run_health_checks
      - verify_data_integrity
      - notify_success

  rollback:
    if: execute.failed
    steps:
      - revert_dns_changes
      - demote_dr_services
      - investigate_failure
      - escalate_to_manual
```

### 8.3 Infrastructure as Code (IaC)

- All infrastructure defined in Terraform / Pulumi
- DR region infrastructure defined in parallel modules
- State stored in versioned, replicated backend
- `terraform plan` run on every PR to detect drift
- Automated `terraform apply` for DR environment updates

### 8.4 Automated Backup Verification

```python
# backup_verification.py (simplified)
def verify_backup(backup_id):
    # 1. Check backup exists and is accessible
    assert backup_exists(backup_id)
    
    # 2. Verify checksum
    assert verify_checksum(backup_id)
    
    # 3. Restore to isolated environment
    restore_job = restore_to_isolated(backup_id)
    
    # 4. Run data integrity checks
    assert run_row_count_checks(restore_job)
    assert run_checksum_validation(restore_job)
    assert run_application_smoke_tests(restore_job)
    
    # 5. Report results
    report_verification_result(backup_id, "PASS")
    
    # 6. Cleanup
    destroy_isolated_environment(restore_job)
```

### 8.5 Self-Healing Capabilities

| Component | Self-Healing Action | Trigger |
|-----------|-------------------|---------|
| PostgreSQL | Automatic failover to synchronous standby | Primary unreachable > 30s |
| Redis | Sentinel-based automatic failover | Master unreachable > 5s |
| Kafka | Automatic leader partition election | Broker failure |
| K8s Pods | Automatic rescheduling | Node failure / pod crash |
| K8s Nodes | Automatic replacement | Node NotReady > 5 min |
| DNS | Automatic failover to secondary | Primary DNS failure |
| Certificates | Automatic renewal | Expiry < 30 days |

---

## 9. DR Monitoring

### 9.1 Monitoring Stack

| Layer | Tool | Metrics |
|-------|------|---------|
| Infrastructure | Prometheus + Grafana | CPU, memory, disk, network |
| Application | Prometheus + Grafana | Request rate, error rate, latency |
| Data Stores | Custom exporters | Replication lag, connection count, query latency |
| Logs | ELK / Loki | Error patterns, audit events |
| Traces | Jaeger / Tempo | Request flow, dependency mapping |
| Synthetics | Pingdom / Uptime | External availability, response time |
| DR-Specific | Custom dashboard | RTO/RPO compliance, backup status, replication health |

### 9.2 DR-Specific Alerts

| Alert | Severity | Condition | Notification |
|-------|----------|-----------|-------------|
| `ReplicationLagHigh` | Critical | PostgreSQL lag > 10s | PagerDuty + Slack |
| `ReplicationLagHigh` | Critical | Redis lag > 5s | PagerDuty + Slack |
| `BackupFailed` | Critical | Any backup job failure | PagerDuty + Slack |
| `BackupStale` | Warning | No successful backup in 24h | Slack + Email |
| `DRRegionUnhealthy` | Critical | DR region health check failing | PagerDuty + Slack |
| `FailoverTestFailed` | Warning | Automated failover test failure | Slack |
| `RTOBreached` | Critical | RTO exceeds target | PagerDuty + Slack + Email |
| `RPOBreached` | Critical | RPO exceeds target | PagerDuty + Slack + Email |
| `DiskSpaceLow` | Warning | Backup storage > 80% | Slack |
| `CertificateExpiring` | Warning | TLS cert expiry < 30 days | Slack + Email |
| `DNSHealthCheckFailed` | Critical | DNS resolution failing | PagerDuty |
| `CrossRegionLatencyHigh` | Warning | Inter-region latency > 100ms | Slack |

### 9.3 DR Dashboard

A dedicated DR dashboard provides real-time visibility into:

- **Replication health:** Lag per data store, replication status
- **Backup status:** Last successful backup, next scheduled, storage utilization
- **DR environment readiness:** Resource availability, configuration drift
- **RTO/RPO compliance:** Current vs. target, trend over time
- **Failover readiness:** Last test result, next scheduled test
- **Regional health:** Primary and DR region status at a glance

### 9.4 Monitoring Runbooks

Each alert has an associated runbook with:
- Alert description and meaning
- Triage steps
- Escalation path
- Resolution procedures
- Historical context (similar past incidents)

---

## 10. Roles & Responsibilities

| Role | Responsibilities |
|------|-----------------|
| **DR Owner** (VP Engineering) | Overall DR strategy, budget, executive reporting |
| **DR Manager** (SRE Lead) | DR plan maintenance, test coordination, incident command |
| **SRE Team** | Runbook execution, failover operations, monitoring |
| **Database Team** | Backup/restore, replication management, data integrity |
| **Security Team** | Security incident response, forensics, air-gapped backup management |
| **Product Team** | Customer communication, feature prioritization during DR |
| **QA Team** | DR test validation, smoke test execution |

---

## 11. Runbooks & Escalation

### 11.1 Escalation Matrix

| Severity | Response Time | Escalation Path |
|----------|---------------|-----------------|
| **P1 — Critical** | 5 minutes | On-call SRE → DR Manager → VP Engineering → CTO |
| **P2 — High** | 15 minutes | On-call SRE → DR Manager → VP Engineering |
| **P3 — Medium** | 1 hour | On-call SRE → DR Manager |
| **P4 — Low** | 4 hours | SRE team |

### 11.2 Key Runbooks

| Runbook ID | Title | Trigger |
|------------|-------|---------|
| RB-DR-001 | Regional Failover — Tier 1 | Regional health failure |
| RB-DR-002 | Regional Failover — Tier 2 | Primary region degradation |
| RB-DR-003 | Database Point-in-Time Recovery | Data corruption |
| RB-DR-004 | Backup Restore Procedure | Data loss event |
| RB-DR-005 | Failback to Primary Region | Primary region restored |
| RB-DR-006 | Ransomware Recovery | Security incident |
| RB-DR-007 | DNS Failover | DNS provider outage |
| RB-DR-008 | Certificate Emergency Replacement | Cert expiry / compromise |

### 11.3 Communication Plan

| Stakeholder | Channel | Timing |
|-------------|---------|--------|
| Engineering team | Slack #incidents | Immediate |
| Leadership | PagerDuty + Email | Within 15 min (P1) |
| Customers | Status page | Within 30 min (P1) |
| All-hands | Email | Within 1 hour (P1) |
| Post-incident | Blameless postmortem | Within 48 hours |

---

## 12. Appendices

### Appendix A: DR Contact List

| Role | Primary | Secondary | Escalation |
|------|---------|-----------|------------|
| DR Manager | [On-call rotation] | [Backup] | VP Engineering |
| SRE On-Call | [PagerDuty schedule] | [Backup] | SRE Lead |
| DBA On-Call | [PagerDuty schedule] | [Backup] | DBA Lead |
| Security On-Call | [PagerDuty schedule] | [Backup] | CISO |

### Appendix B: DR Environment Specifications

| Resource | Primary Region | DR Region | Notes |
|----------|---------------|-----------|-------|
| Kubernetes clusters | 3 (prod) | 3 (prod) | Same node pools |
| PostgreSQL | 1 primary + 2 replicas | 1 standby + 2 replicas | Cross-region async |
| Redis | 3-node cluster | 3-node cluster | Sentinel-managed |
| Kafka | 6 brokers | 6 brokers | MM2 replication |
| S3 buckets | Versioned + CRR | Versioned + source | Cross-region |
| Load balancers | ALB + NLB | ALB + NLB | Pre-provisioned |

### Appendix C: Compliance & Audit

- DR plan reviewed quarterly by DR Manager and Security
- DR test results audited annually
- RTO/RPO compliance reported monthly
- Plan updated after every DR test and real incident
- Version controlled in Git with change history

### Appendix D: Glossary

| Term | Definition |
|------|-----------|
| RTO | Recovery Time Objective — maximum acceptable downtime |
| RPO | Recovery Point Objective — maximum acceptable data loss |
| RPO | Recovery Point Objective — maximum acceptable data loss |
| MTTR | Mean Time To Recovery |
| MTBF | Mean Time Between Failures |
| STONITH | Shoot The Other Node In The Head — fencing mechanism |
| MM2 | MirrorMaker 2 — Kafka cross-cluster replication |
| CRR | Cross-Region Replication |
| IaC | Infrastructure as Code |
| WORM | Write Once Read Many — immutable storage |

---

**Document Approval:**

| Role | Name | Date | Signature |
|------|------|------|-----------|
| DR Manager | | | |
| VP Engineering | | | |
| CTO | | | |

---

*This document is maintained by the Platform Engineering team. For questions or updates, contact the DR Manager or file a ticket in the #dr-planning Slack channel.*
