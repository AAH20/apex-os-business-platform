# Incident Response Playbook

## 1. Severity Levels

| Level | Name | Description | Examples |
|-------|------|-------------|----------|
| SEV1 | Critical | Complete service outage or data loss; no workaround | Production DB down, auth failure, data breach |
| SEV2 | High | Major feature degraded; limited workaround exists | Payment processing slow, API errors >5%, partial outage |
| SEV3 | Medium | Minor feature issue; workaround available | Non-critical UI bug, single-node failure, degraded performance |
| SEV4 | Low | Cosmetic or informational; no user impact | Typos, logging gaps, minor config drift |

---

## 2. Response Procedures by Severity

### SEV1 — Critical

1. **Acknowledge** within 5 minutes; declare incident in `#incidents` channel.
2. **Assemble** the Incident Commander (IC) and on-call engineers.
3. **Triage** — confirm scope, impact, and affected users/systems.
4. **Mitigate** — apply rollback, failover, or feature flag disable.
5. **Communicate** — post initial status within 15 minutes; update every 30 minutes.
6. **Resolve** — confirm fix in production; monitor for 1 hour.
7. **Hand off** — IC documents timeline and hands to post-incident review lead.

### SEV2 — High

1. **Acknowledge** within 15 minutes.
2. **Triage** — identify root cause or apply known workaround.
3. **Mitigate** — deploy fix or enable fallback.
4. **Communicate** — post status within 30 minutes; update hourly.
5. **Resolve** — confirm fix; monitor for 30 minutes.
6. **Document** — file incident ticket with timeline.

### SEV3 — Medium

1. **Acknowledge** within 1 business day.
2. **Triage** — reproduce and diagnose.
3. **Fix** — schedule patch in next release cycle.
4. **Communicate** — update ticket; notify affected teams.
5. **Resolve** — verify fix in staging before deploy.

### SEV4 — Low

1. **Log** in backlog.
2. **Fix** in regular sprint planning.
3. **Close** after verification.

---

## 3. Communication Templates

### Initial Status Update

```
[SEV-X] <Short description>
Status: Investigating
Impact: <What is affected and for whom>
Next update: <Time + 30 min>
IC: <Name>
```

### Progress Update

```
[SEV-X] <Short description>
Status: Identified / Mitigating / Monitoring
Update: <What changed since last update>
ETA: <Expected resolution time or "Unknown">
Next update: <Time>
```

### Resolution Notice

```
[SEV-X] <Short description> — RESOLVED
Duration: <Start> – <End> (<Total time>)
Root cause: <One-line summary>
Action taken: <What was done>
Follow-up: <Link to post-incident review or ticket>
```

### Customer-Facing Notice

```
We are currently experiencing <issue summary>.
Our team is actively working on a resolution.
We expect to provide an update within <timeframe>.
We apologize for the inconvenience.
Status page: <URL>
```

---

## 4. Escalation Contacts

| Role | Primary | Backup | Escalation Path |
|------|---------|--------|-----------------|
| Incident Commander | On-call IC (PagerDuty) | Secondary IC | IC → Engineering Manager → VP Eng |
| Engineering | On-call Engineer (PagerDuty) | Team Lead | Engineer → EM → VP Eng |
| SRE / Infra | On-call SRE | Infra Lead | SRE → Infra Manager → CTO |
| Product | Product Manager | Product Lead | PM → Director of Product → CPO |
| Security | Security On-call | CISO | Security → CISO → CEO |
| Communications | Comms Lead | Marketing Manager | Comms → VP Marketing → CEO |
| Customer Support | Support Lead | Support Manager | Support → Head of Support → COO |

**Escalation triggers:**
- SEV1 not mitigated within 30 minutes → escalate to VP Eng.
- SEV1 not resolved within 2 hours → escalate to CTO.
- Data breach or security incident → escalate to CISO immediately.
- Media or regulatory attention → escalate to Comms Lead and CEO.

---

## 5. Post-Incident Actions

### Immediate (within 24 hours)

- [ ] Confirm incident is fully resolved and stable.
- [ ] File or update incident ticket with complete timeline.
- [ ] Notify stakeholders of resolution.

### Post-Incident Review (within 5 business days)

- [ ] Schedule blameless post-mortem with all involved parties.
- [ ] Document timeline: detection → response → mitigation → resolution.
- [ ] Identify root cause (5 Whys or similar methodology).
- [ ] List contributing factors and systemic issues.
- [ ] Define action items with owners and deadlines.
- [ ] Share post-mortem summary with engineering org.

### Follow-Up

- [ ] Track action items to completion.
- [ ] Update runbooks and monitoring based on findings.
- [ ] Add alerts or dashboards to prevent recurrence.
- [ ] Conduct retrospective on response process itself.
- [ ] Archive incident artifacts (logs, chat transcripts, tickets).

### Metrics to Track

- Mean Time to Detect (MTTD)
- Mean Time to Acknowledge (MTTA)
- Mean Time to Mitigate (MTTM)
- Mean Time to Resolve (MTTR)
- Incident count by severity (weekly/monthly)
- Recurring incident rate
