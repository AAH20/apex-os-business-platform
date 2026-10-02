# Release Management Guide

## 1. Release Process

### 1.1 Release Types

| Type | Cadence | Approval | Downtime |
|------|---------|----------|----------|
| **Patch** | As needed | Tech Lead | Zero |
| **Minor** | Bi-weekly | Product Owner | Zero |
| **Major** | Quarterly | CTO + PO | Scheduled window |
| **Hotfix** | Emergency | On-call + TL | Zero |

### 1.2 Standard Release Workflow

1. **T-7 days**: Feature freeze for minor/major releases
2. **T-5 days**: Code complete, begin integration testing
3. **T-3 days**: QA sign-off, staging deployment
4. **T-2 days**: UAT with stakeholders
5. **T-1 day**: Final pre-release checklist, deploy to production
6. **T-0**: Production deployment, smoke tests, monitoring
7. **T+1 day**: Post-release review, retrospective notes

### 1.3 Hotfix Workflow

1. On-call identifies critical issue
2. Create hotfix branch from `main`
3. Fix, test, and get expedited review (1 approver minimum)
4. Deploy to staging, verify fix
5. Deploy to production immediately
6. Document incident within 24 hours

### 1.4 Branch Strategy

- `main` — production-ready code
- `develop` — integration branch
- `release/x.y.z` — release preparation
- `hotfix/x.y.z` — emergency fixes
- `feature/*` — new features

---

## 2. Version Numbering

### 2.1 Semantic Versioning (SemVer)

Format: `MAJOR.MINOR.PATCH`

| Component | Increment When | Example |
|-----------|---------------|---------|
| **MAJOR** | Breaking API changes, schema migrations | `2.0.0` |
| **MINOR** | New features, backward-compatible | `1.3.0` |
| **PATCH** | Bug fixes, backward-compatible | `1.3.2` |

### 2.2 Pre-release Tags

- `1.3.0-alpha.1` — internal testing
- `1.3.0-beta.1` — stakeholder preview
- `1.3.0-rc.1` — release candidate

### 2.3 Version Sources

- `package.json` — Node.js services
- `pyproject.toml` — Python services
- `Cargo.toml` — Rust services
- `VERSION` file — fallback for monorepo root

### 2.4 Version Bump Rules

1. Never reuse a version number
2. Tag every release in Git: `git tag -a v1.3.0 -m "Release 1.3.0"`
3. Update `CHANGELOG.md` with every release
4. Keep version in sync across all services in a release train

---

## 3. Release Checklist

### 3.1 Pre-Release (T-1 day)

- [ ] All P0/P1 bugs resolved or deferred with approval
- [ ] Code review complete, all comments resolved
- [ ] CI/CD pipeline green (build, lint, test, security scan)
- [ ] Database migrations tested on staging
- [ ] Environment variables and secrets updated
- [ ] Feature flags configured correctly
- [ ] Load test results within acceptable thresholds
- [ ] Documentation updated (API docs, runbooks)
- [ ] Rollback plan documented and tested
- [ ] On-call engineer assigned for release window
- [ ] Communication sent to stakeholders

### 3.2 Deployment (T-0)

- [ ] Deploy to production during low-traffic window
- [ ] Run database migrations (if applicable)
- [ ] Verify service health checks pass
- [ ] Run smoke tests against production
- [ ] Monitor error rates and latency for 30 minutes
- [ ] Verify critical user journeys end-to-end
- [ ] Confirm monitoring dashboards are green
- [ ] Tag release in Git

### 3.3 Post-Release (T+1 day)

- [ ] Monitor for 48 hours (automated alerts active)
- [ ] Collect feedback from support team
- [ ] Schedule post-mortem if any incidents occurred
- [ ] Update release notes in user-facing changelog
- [ ] Archive release branch
- [ ] Update team on release outcome

---

## 4. Rollback Procedures

### 4.1 When to Rollback

Trigger rollback immediately if:
- Error rate exceeds 5% for >5 minutes
- Critical user journey is broken
- Data corruption is detected
- Security vulnerability is exposed
- P95 latency exceeds 2x baseline for >10 minutes

### 4.2 Rollback Steps

1. **Declare incident** — Notify team in #incidents channel
2. **Stop the bleeding** — Disable feature flags for the release
3. **Revert deployment** — Redeploy previous stable version
4. **Revert migrations** — Run down migrations if schema changed
5. **Verify** — Confirm error rates return to baseline
6. **Communicate** — Update stakeholders on status
7. **Document** — Record timeline and root cause

### 4.3 Rollback Commands

```bash
# Kubernetes rollback
kubectl rollout undo deployment/<service-name>

# Docker rollback
docker pull <registry>/<service>:<previous-tag>
docker stop <container> && docker rm <container>
docker run --name <container> <registry>/<service>:<previous-tag>

# Database migration rollback
npm run migrate:down
# or
alembic downgrade -1
```

### 4.4 Rollback Time Targets

| Service Tier | Target | Maximum |
|-------------|--------|---------|
| Critical (payments, auth) | 5 min | 15 min |
| Standard (APIs, dashboards) | 15 min | 30 min |
| Internal (admin tools) | 30 min | 60 min |

### 4.5 Post-Rollback

- Do not delete the failed release artifacts
- Preserve logs for investigation
- Create a follow-up ticket for the failed change
- Schedule root cause analysis within 48 hours

---

## 5. Communication Plan

### 5.1 Internal Communication

| Audience | Channel | Timing | Content |
|----------|---------|--------|---------|
| Engineering team | #eng-releases | T-7 days | Release scope, timeline |
| Engineering team | #eng-releases | T-1 day | Final checklist, go/no-go |
| All staff | #announcements | T-0 | Release starting |
| All staff | #announcements | T+0 | Release complete |
| Leadership | Email | T+1 day | Release summary, metrics |

### 5.2 External Communication

| Audience | Channel | Timing | Content |
|----------|---------|--------|---------|
| Customers (minor) | In-app banner | T-0 | New features available |
| Customers (major) | Email + blog | T-1 day | What's new, how to use |
| Customers (incident) | Status page | T-0 | Incident acknowledged |
| Customers (resolved) | Status page | T+0 | Issue resolved, details |
| API consumers | Developer portal | T-0 | API changelog, migration guide |

### 5.3 Status Page Updates

Use statuspage.io or equivalent:

1. **Investigating** — Issue identified, investigating
2. **Identified** — Root cause found, fix in progress
3. **Monitoring** — Fix deployed, watching metrics
4. **Resolved** — Issue confirmed fixed

### 5.4 Escalation Path

```
On-call Engineer → Tech Lead → Engineering Manager → CTO
     ↓                ↓              ↓                ↓
  T+0 min         T+15 min       T+30 min         T+60 min
```

### 5.5 Post-Release Communication Template

```
Subject: [RELEASE] v1.3.0 — Release Summary

Status: ✅ Complete / ⚠️ Partial / ❌ Rolled back

Changes:
- Feature A: description
- Feature B: description
- Bug fix: description

Impact:
- Users affected: N
- Downtime: 0 min
- Performance change: +2% latency (within SLO)

Next steps:
- Monitoring through DATE
- Follow-up tickets: LINK
```

---

## Appendix: Key Contacts

| Role | Name | Contact |
|------|------|---------|
| On-call Engineer | — | PagerDuty rotation |
| Tech Lead | — | Slack @tech-lead |
| Product Owner | — | Slack @product |
| DevOps | — | Slack @devops |
| Status Page Admin | — | Slack @status |

---

*Last updated: 2026-10-02*
*Owner: Engineering Team*
