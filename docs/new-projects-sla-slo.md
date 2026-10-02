# New Projects — SLA, SLO, Monitoring, Incident Response & Escalation

## 1. Service Level Agreements (SLAs)

| Tier | Target | Measurement | Penalty |
|------|--------|-------------|---------|
| **Critical** | 99.95% uptime | Monthly | Service credit 25% |
| **Standard** | 99.9% uptime | Monthly | Service credit 10% |
| **Best-effort** | 99.5% uptime | Monthly | None |

- **Response time**: Critical < 15 min, Standard < 1 hr, Best-effort < 4 hrs
- **Resolution time**: Critical < 4 hrs, Standard < 24 hrs, Best-effort < 72 hrs
- **Maintenance windows**: Sundays 02:00–06:00 UTC, announced 48 hrs in advance
- **Exclusions**: Force majeure, customer-caused outages, scheduled maintenance

## 2. Service Level Objectives (SLOs)

| SLI | SLO | Window | Error Budget |
|-----|-----|--------|--------------|
| Availability | 99.95% | 30 days | 21.9 min/month |
| Latency (p95) | < 500 ms | 30 days | — |
| Latency (p99) | < 1 s | 30 days | — |
| Error rate | < 0.1% | 30 days | — |
| Throughput | ≥ 1000 req/s | 30 days | — |

- Error budget burn rate alerts at 2× (warning) and 4× (page)
- SLOs reviewed quarterly; adjusted based on capacity and demand

## 3. Monitoring Strategy

### Metrics
- **Infrastructure**: CPU, memory, disk, network per node
- **Application**: Request rate, error rate, latency (RED method)
- **Business**: Active users, transaction volume, revenue impact

### Logging
- Structured JSON logs to centralized store (retention: 90 days hot, 1 year cold)
- Correlation IDs propagated across all services
- Sensitive data redacted at the source

### Tracing
- OpenTelemetry traces for all inter-service calls
- Sampling: 100% errors, 10% success (adaptive under load)

### Alerting
| Severity | Condition | Notify | Response |
|----------|-----------|--------|----------|
| P1 | SLO breach or 5xx spike | On-call + manager | Immediate |
| P2 | Latency degradation | On-call | < 30 min |
| P3 | Resource saturation | Team channel | < 4 hrs |
| P4 | Minor anomalies | Ticket | Next business day |

### Dashboards
- Real-time: Grafana (per-service, per-endpoint)
- Weekly: SLO compliance, error budget remaining
- Monthly: Capacity planning, trend analysis

## 4. Incident Response

### Severity Levels
- **SEV1**: Complete outage or data loss — all hands
- **SEV2**: Major feature degraded — on-call + team lead
- **SEV3**: Minor issue or partial degradation — on-call
- **SEV4**: Cosmetic or low-impact — ticket queue

### Response Process
1. **Detect**: Alert fires or user report received
2. **Triage**: Assess severity, assign IC (Incident Commander)
3. **Mitigate**: Rollback, scale, or feature-flag disable
4. **Resolve**: Confirm fix, monitor for 30 min
5. **Review**: Post-incident review within 48 hrs (blameless)

### Communication
- Internal: #incidents Slack channel, status page updated every 30 min
- External: Status page + customer email for SEV1/SEV2
- Post-mortem: Published within 5 business days for SEV1/SEV2

### Runbooks
- Every alert has a linked runbook
- Runbooks tested monthly via game days
- Automated remediation for known failure modes

## 5. Escalation Procedures

### On-Call Rotation
- Primary on-call: 1-week rotation, 24/7 coverage
- Secondary on-call: Backup, 15 min response SLA
- Escalation manager: Director of Engineering

### Escalation Matrix
| Time Elapsed | Action |
|--------------|--------|
| 0 min | On-call acknowledges |
| 15 min | Secondary on-call engaged |
| 30 min | Engineering manager notified |
| 1 hr | Director + VP Engineering notified |
| 2 hr | CTO + customer communication |

### Escalation Triggers
- SLO error budget exhausted
- SEV1 unresolved after 1 hr
- Multiple related incidents
- Customer-impacting data loss
- Security incident

### Post-Escalation
- Incident commander debriefs within 24 hrs
- Action items tracked to completion
- Process improvements documented and prioritized

---

**Owner**: Platform Engineering  
**Review cycle**: Quarterly  
**Last updated**: 2026-10-02
