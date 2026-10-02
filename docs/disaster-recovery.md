# Disaster Recovery — APEX-OS Business Platform

**Version:** 2.0 · **Last Updated:** 2026-10-02 · **Owner:** Platform Engineering · **Review Cycle:** Quarterly

---

## 1. DR Strategy

**Objective:** Restore platform services within defined RTO/RPO after any disruptive event.

| Tier | Services | RTO | RPO |
|------|----------|-----|-----|
| 1 — Critical | Auth, API Gateway, Billing | 5 min | 0 (zero) |
| 2 — Essential | Core DB, Redis, Kafka | 30 min | < 5 sec |
| 3 — Standard | Reporting, Search, Notifications | 4 hr | < 1 hr |
| 4 — Non-critical | Batch jobs, Internal tools | 24 hr | < 24 hr |

**Topology:** Active-Active multi-region (us-east-1 / us-west-2) behind a Global Traffic Manager. Tier 1 runs active-active; Tiers 2–4 use active-passive with cross-region replication.

**Scope:** All production infrastructure, data stores, message queues, API gateway, auth, CI/CD, observability, DNS/CDN. Out of scope: dev/staging environments, third-party SaaS, end-user devices.

**Principles:**
- Automated failover for Tier 1; semi-automated for Tier 2; manual for Tiers 3–4.
- All DR decisions logged for post-incident review.
- Runbooks versioned in Git and tested quarterly.

---

## 2. Backup Strategy

### 2.1 Schedule

| Data Source | Type | Frequency | Retention | Encryption |
|-------------|------|-----------|-----------|------------|
| PostgreSQL | Full | Daily 02:00 UTC | 35 days | AES-256 |
| PostgreSQL | WAL archiving | Continuous | 7 days | AES-256 |
| PostgreSQL | Incremental | Every 6 hr | 14 days | AES-256 |
| Redis | RDB snapshot | Every 15 min | 7 days | AES-256 |
| Redis | AOF | Every 1 sec | 3 days | AES-256 |
| S3 / Object Storage | Versioned + CRR | Continuous | 90 days | SSE-KMS |
| Kafka | Topic snapshot | Hourly | 7 days | AES-256 |
| etcd / K8s state | Full | Every 6 hr | 30 days | AES-256 |
| Vault secrets | Raft snapshot | Every 1 hr | 90 days | AES-256-GCM |
| Config / IaC | Git commit | On every change | Indefinite | GPG-signed |

### 2.2 Storage

- **Primary:** Same-region S3 bucket with versioning.
- **Secondary:** Cross-region S3 bucket in DR region (S3 CRR).
- **Tertiary (air-gapped):** Weekly snapshot to isolated account with Object Lock (WORM) for ransomware protection.
- All backups encrypted at rest with KMS-managed keys in a separate security account.

### 2.3 Validation

- Daily automated restore of a random backup subset to an isolated environment.
- SHA-256 checksum verification on every backup artifact.
- All backups indexed in a searchable catalog (timestamp, size, checksum, key ID).
- Monthly full restore drill (see Section 5).

### 2.4 Tooling

| Component | Tool |
|-----------|------|
| PostgreSQL | pgBackRest / WAL-G |
| Redis | redis-cli BGSAVE + S3 sync |
| S3 | Native versioning + CRR |
| Kafka | MirrorMaker 2 |
| K8s / etcd | Velero |
| Vault | Integrated Raft snapshot |

---

## 3. Failover Strategy

### 3.1 Failover Types

| Type | Trigger | Automation |
|------|---------|------------|
| Automatic | Health check failure, replication lag breach | Fully automated |
| Semi-automated | Regional degradation, elevated error rates | One-click approval |
| Manual | Complete regional loss, security incident | Runbook-driven |

### 3.2 Procedures

**Tier 1 — Automatic (Active-Active):**
1. Global Traffic Manager detects regional health check failure.
2. DNS TTL (30s) expires; traffic routed to DR region.
3. DR Tier 1 services already serving traffic — no data loss.
4. RTO: < 5 minutes.

**Tier 2 — Semi-Automated (Active-Passive):**
1. Monitoring detects primary region degradation; alert fires to on-call.
2. On-call approves failover via dashboard.
3. Automation: promote PostgreSQL standby → promote Redis replica → update Kafka consumer offsets → switch DNS → verify health.
4. RTO: < 30 minutes.

**Tier 3 — Manual (Warm Standby):**
1. On-call initiates via runbook.
2. Provision warm standby resources; restore from latest cross-region replica.
3. Start services in dependency order; verify health checks; update DNS.
4. RTO: < 4 hours.

**Tier 4 — Cold Standby Rebuild:**
1. Provision infrastructure from Terraform/Pulumi.
2. Restore data from latest backup; deploy from container registry; apply config from Git.
3. RTO: < 24 hours.

### 3.3 Failback

1. Verify primary region healthy.
2. Re-establish replication DR → primary; wait for lag = 0.
3. Switch DNS back; verify health; demote DR to standby.
4. Failback RTO: < 1 hour (Tier 1–2).

### 3.4 Split-Brain Prevention

- STONITH fencing via cloud provider API before replica promotion.
- Quorum via etcd/Consul for leader election.
- Low DNS TTL (30s) to minimize stale routing.
- Multi-layer health checks (L4 TCP, L7 HTTP, application-level).

---

## 4. Recovery Procedures

### 4.1 Database Corruption
1. Identify last known-good snapshot via WAL replay testing.
2. Restore snapshot to staging; validate data integrity.
3. Replay WAL to target RPO (max 5 min data loss).
4. Promote restored instance; update connection strings.
5. Verify smoke tests; announce recovery.

### 4.2 Regional Outage
1. Confirm region-level failure (not application-level).
2. Initiate cross-region failover: promote DR replicas.
3. Update Global Traffic Manager weights to 100% DR region.
4. Scale DR region to full capacity (pre-warmed node pools).
5. Monitor error rates until stable; declare recovery.

### 4.3 Ransomware / Data Destruction
1. Isolate affected workloads (network policy enforcement).
2. Identify attack scope via audit logs and file integrity monitoring.
3. Restore from immutable air-gapped backups (WORM storage).
4. Rotate all credentials, certificates, and secrets.
5. Preserve forensic snapshot before any recovery action.
6. Gradual service restoration with enhanced monitoring.

### 4.4 Accidental Data Deletion
1. Identify deletion scope and timestamp.
2. Halt related write operations if ongoing.
3. Restore affected tables/objects from point-in-time recovery.
4. Validate with application-level checks before re-enabling writes.

### 4.5 DNS Failure
1. Confirm DNS provider outage via synthetic checks.
2. Fail over to secondary DNS provider.
3. If needed, update IPs manually via runbook.
4. Monitor propagation until fully resolved.

---

## 5. DR Testing

### 5.1 Schedule

| Test Type | Frequency | Duration | Scope |
|-----------|-----------|----------|-------|
| Backup restore validation | Daily (automated) | 30 min | Random backup subset |
| Tabletop exercise | Monthly | 2 hr | Scenario walkthrough |
| Component failover test | Bi-weekly | 1 hr | Single service |
| Full DR drill | Quarterly | 4–8 hr | Complete regional failover |
| Chaos engineering | Weekly | 2 hr | Random failure injection |
| GameDay | Semi-annually | Full day | Multi-failure scenario |

### 5.2 Test Scenarios

| Scenario | Expected Outcome |
|----------|-----------------|
| Single AZ loss | Automatic failover to remaining AZs; no data loss |
| Regional loss | Traffic routed to DR; RTO < 5 min (Tier 1) |
| Database corruption | Point-in-time recovery; RPO < 5 sec |
| Ransomware attack | Restore from air-gapped backups; isolate affected systems |
| Network partition | Quorum-based resolution; no dual-primary |
| DNS failure | Secondary DNS provider; manual IP update |
| Certificate expiry | Automated cert renewal; fallback certs |
| Cascading failure | Circuit breakers engage; graceful degradation |

### 5.3 Execution Protocol

1. **Pre-test:** Notify stakeholders (48 hr for full drill); snapshot current state; verify backup integrity; confirm DR readiness.
2. **Execution:** Declare simulated disaster; execute runbook; monitor RTO/RPO in real-time; document all actions and timestamps.
3. **Post-test:** Verify data integrity (checksums, row counts); run smoke tests; measure actual RTO/RPO vs targets; document lessons learned; file improvement tickets; update runbooks.

### 5.4 Success Criteria

| Criterion | Target |
|-----------|--------|
| RTO met | 100% of services within target |
| RPO met | 100% of data stores within target |
| Data integrity | 100% checksum verification pass |
| Smoke tests | 100% pass rate |
| Rollback | Successful failback within target time |

### 5.5 Post-Test Actions

- Document gaps and update runbooks within 48 hours.
- Track remediation items as high-priority tickets.
- Report metrics to engineering leadership monthly.

---

## Roles & Escalation

| Role | Responsibility | Escalation |
|------|---------------|------------|
| On-call SRE | First responder, runbook execution | DR Manager |
| DR Manager (SRE Lead) | Failover decisions, incident command | VP Engineering |
| VP Engineering | Resource approval, executive reporting | CTO |
| DBA Team | Backup/restore, replication, data integrity | — |
| Security Team | Incident response, forensics, air-gapped backups | CISO |
| Comms Lead | Status page updates | — |

**Escalation matrix:** P1 (5 min) → On-call → DR Manager → VP Eng → CTO · P2 (15 min) → On-call → DR Manager → VP Eng · P3 (1 hr) → On-call → DR Manager · P4 (4 hr) → SRE team.

---

*This document is maintained by the Platform Engineering team. For questions or updates, contact the DR Manager or file a ticket in #dr-planning.*
