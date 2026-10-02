# Change Management

## 1. Change Management Process

### 1.1 Change Categories

| Category | Description | Approval | Lead Time |
|----------|-------------|----------|-----------|
| **Standard** | Pre-approved, low-risk (docs, config tweaks) | Team lead | 1 day |
| **Normal** | Feature work, minor refactors | Tech lead + PM | 3 days |
| **Major** | Architecture changes, DB migrations | Architecture board | 1 week |
| **Emergency** | Security patches, prod incidents | On-call + CTO | Immediate |

### 1.2 Change Request Workflow

1. **Submit** — Create a Change Request (CR) ticket with: description, scope, risk assessment, affected components, test plan, rollback plan.
2. **Review** — Assigned reviewer evaluates within 24h (Standard/Normal) or 4h (Emergency).
3. **Approve/Reject** — Approved CRs are scheduled; rejected CRs include feedback and can be resubmitted.
4. **Implement** — Work proceeds per the approved plan. Any scope change requires re-approval.
5. **Verify** — QA validates against acceptance criteria; automated tests must pass.
6. **Close** — CR marked complete with deployment notes and lessons learned.

### 1.3 Risk Assessment Matrix

| Likelihood \ Impact | Low | Medium | High |
|---------------------|-----|--------|------|
| **High** | Medium | High | Critical |
| **Medium** | Low | Medium | High |
| **Low** | Low | Low | Medium |

- **Critical** — Requires CTO sign-off and mandatory rollback rehearsal.
- **High** — Requires architecture review and staged rollout.
- **Medium** — Standard review process.
- **Low** — Expedited review.

---

## 2. Version Control Strategy

### 2.1 Branching Model (Git Flow)

```
main ─────────────────────────────────────────────►
  \                                               /
   release/1.4 ─────►                            /
    \                                          /
     develop ──────────────────────────────►    /
      \                                      /
       feature/ABC-123 ─────►               /
        \                                /
         hotfix/1.4.1 ──────────────────►
```

| Branch | Purpose | Protection |
|--------|---------|------------|
| `main` | Production releases | Require 2 approvals, CI pass |
| `develop` | Integration branch | Require 1 approval, CI pass |
| `release/*` | Release preparation | Require 2 approvals, freeze window |
| `feature/*` | Feature development | Require 1 approval |
| `hotfix/*` | Emergency fixes | Require 1 approval, fast-track CI |

### 2.2 Commit Convention

```
<type>(<scope>): <description>

[optional body]
[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`

Example: `feat(auth): add OAuth2 SSO integration for enterprise tier`

### 2.3 Tagging & Versioning

- **Semantic Versioning**: `MAJOR.MINOR.PATCH`
  - MAJOR — Breaking changes
  - MINOR — New features (backward compatible)
  - PATCH — Bug fixes
- Tags: `v1.4.0`, `v1.4.1`, etc.
- Pre-release: `v1.5.0-rc.1`, `v1.5.0-beta.2`

### 2.4 Repository Hygiene

- Squash merge for feature branches.
- Rebase `develop` onto `main` after each release.
- Delete merged branches after 7 days.
- Protected branches enforce linear history.

---

## 3. Release Management

### 3.1 Release Cadence

| Release Type | Frequency | Cut-off | Deploy Window |
|-------------|-----------|---------|---------------|
| **Patch** | As needed | Anytime | Tue–Thu, 10:00–14:00 UTC |
| **Minor** | Bi-weekly | Monday | Wednesday, 10:00–14:00 UTC |
| **Major** | Quarterly | 2 weeks prior | Scheduled maintenance window |

### 3.2 Release Checklist

- [ ] All CRs merged and verified
- [ ] CHANGELOG.md updated
- [ ] Migration scripts tested on staging
- [ ] Runbook updated
- [ ] Monitoring dashboards verified
- [ ] Rollback artifacts prepared
- [ ] Stakeholders notified (see §5)
- [ ] Smoke test plan ready

### 3.3 Deployment Pipeline

```
Build → Unit Tests → Integration Tests → Staging Deploy →
  Smoke Tests → Security Scan → Approval Gate → Production Deploy
```

- **Staging** — Full replica of production; mandatory for all changes.
- **Canary** — 5% traffic for 30 minutes before full rollout (Major releases only).
- **Blue/Green** — Zero-downtime deployments for API and web tiers.

### 3.4 Release Artifacts

Each release produces:
- Docker images tagged with version + git SHA
- Database migration scripts (forward + rollback)
- Configuration manifests
- Signed release notes

---

## 4. Rollback Procedures

### 4.1 Rollback Triggers

- Error rate exceeds 5% for 5 minutes
- P95 latency exceeds 2× baseline for 10 minutes
- Critical feature regression detected
- Data corruption or integrity issues
- Security vulnerability discovered post-deploy

### 4.2 Rollback Decision Matrix

| Severity | Decision Maker | Max Time to Decide | Action |
|----------|---------------|-------------------|--------|
| **Sev-1** | On-call engineer | 5 minutes | Immediate rollback |
| **Sev-2** | Tech lead | 15 minutes | Rollback or hotfix |
| **Sev-3** | PM + Tech lead | 1 hour | Forward fix preferred |

### 4.3 Rollback Steps

1. **Declare incident** — Open incident ticket, notify #incidents channel.
2. **Stop the bleed** — Rollback deployment:
   ```bash
   kubectl rollout undo deployment/<service> --namespace=prod
   ```
3. **Verify rollback** — Confirm metrics return to baseline.
4. **Data rollback** — If migrations ran, execute rollback scripts:
   ```bash
   migrate -database $DB_URL -path ./migrations down 1
   ```
5. **Communicate** — Post status update (see §5).
6. **Post-mortem** — Schedule within 24h for Sev-1/Sev-2.

### 4.4 Rollback Testing

- Rollback drills performed monthly on staging.
- Database rollback scripts tested in CI pipeline.
- Infrastructure-as-code enables environment recreation in <30 minutes.

---

## 5. Communication Plan

### 5.1 Stakeholder Matrix

| Audience | Channel | Frequency | Owner |
|----------|---------|-----------|-------|
| **Engineering** | #eng-releases (Slack) | Per release | Release manager |
| **Product/PM** | #product-updates | Per release | PM |
| **Leadership** | Weekly digest | Weekly | CTO |
| **Customers** | Status page + email | As needed | Support |
| **All-hands** | Monthly meeting | Monthly | CEO |

### 5.2 Release Communication Templates

**Pre-release (T-24h):**
> 🚀 Release v1.4.0 scheduled for [DATE] at [TIME] UTC.
> Scope: [brief summary]
> Expected impact: [none/minor/moderate]
> Status page will be updated during deployment.

**During release:**
> 🔄 v1.4.0 deployment in progress. ETA: [time].
> Monitoring: [dashboard link]

**Post-release:**
> ✅ v1.4.0 deployed successfully.
> Highlights: [key changes]
> Issues: [none / known issues with workarounds]

**Rollback:**
> ⚠️ v1.4.0 rolled back due to [reason].
> Previous version v1.3.2 is live.
> Investigation underway. Next update: [time].

### 5.3 Incident Communication

| Timeframe | Action |
|-----------|--------|
| T+0 | Acknowledge incident in #incidents |
| T+15min | Initial assessment and ETA |
| T+30min | Progress update |
| T+60min | Resolution or escalation update |
| Post-resolution | Post-mortem summary within 24h |

### 5.4 Change Advisory Board (CAB)

- **Members**: CTO, VP Eng, PM, QA lead, Security lead, SRE lead.
- **Meeting**: Weekly (30 min) for Normal/Major changes; ad-hoc for Emergency.
- **Purpose**: Review upcoming changes, assess risk, resolve conflicts, approve schedule.

---

## Appendix: Tools & References

- **Issue Tracker**: Jira (project: APEX)
- **CI/CD**: GitHub Actions
- **Monitoring**: Grafana + Prometheus
- **Status Page**: status.apex-os.com
- **Runbook**: docs/runbooks/
- **Incident Response**: docs/incident-response.md
