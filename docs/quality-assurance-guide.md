# Quality Assurance Guide

## 1. QA Strategy

### Principles
- **Shift left**: Catch defects as early as possible — cheaper to fix at design than in production.
- **Automate relentlessly**: Any manual test run more than twice should be scripted.
- **Risk-based prioritisation**: Focus effort on high-impact, high-probability failure areas.
- **Fast feedback**: Tests must run in minutes, not hours. Slow suites get skipped.
- **Ownership**: Every engineer is responsible for quality. QA enables; it does not gate-keep alone.

### Approach
| Phase | Activities |
|-------|-----------|
| Design | Threat modelling, API contract review, acceptance criteria definition |
| Development | TDD, static analysis, pre-commit hooks |
| Integration | CI pipeline, contract tests, integration suites |
| Pre-release | Staging validation, performance benchmarks, security scan |
| Post-release | Monitoring, alerting, error tracking, incident review |

### Test Data & Environments
- Use anonymised production-like data in staging.
- Never run destructive tests against production.
- Seed databases deterministically for reproducible test runs.

---

## 2. Test Pyramid

```
         /\
        /  \     E2E Tests (few, critical paths)
       /----\
      /      \   Integration Tests (APIs, DB, external services)
     /--------\
    /          \ Unit Tests (many, fast, isolated)
   /------------|
```

### Unit Tests (~70% of suite)
- Scope: Individual functions, classes, components.
- Speed: < 100 ms each; full suite < 2 min.
- Tools: pytest (backend), Vitest/Jest (frontend).
- Rules:
  - No network, no filesystem, no clock dependencies.
  - Mock all external boundaries.
  - One assertion per behaviour (multiple asserts on same outcome acceptable).
  - Cover happy path, edge cases, and error paths.

### Integration Tests (~20% of suite)
- Scope: API endpoints, database queries, message consumers, auth flows.
- Speed: < 10 min total.
- Tools: pytest with testcontainers, Supertest.
- Rules:
  - Use real database (containerised), mocked third-party APIs.
  - Verify request/response contracts.
  - Test authentication and authorisation boundaries.

### End-to-End Tests (~10% of suite)
- Scope: Critical user journeys only (signup → onboarding → core action → logout).
- Speed: < 15 min total.
- Tools: Playwright.
- Rules:
  - Run against staging, never production.
  - Idempotent — clean up created state.
  - Retry once on known-flaky selectors; fix root cause after.

### Non-Functional Tests
| Type | Tool | Frequency |
|------|------|-----------|
| Performance (load) | k6 / Locust | Per release |
| Security (SAST) | Semgrep / Bandit | Every PR |
| Security (deps) | pip-audit / npm audit | Daily |
| Accessibility | axe-core | Per PR (frontend) |
| Visual regression | Chromatic / Percy | Per PR (UI) |

---

## 3. Quality Gates

All gates must pass before code merges. No exceptions without written tech-lead approval.

### Pre-Commit (local)
- [ ] Linter passes (ruff / ESLint).
- [ ] Formatter passes (prettier / black).
- [ ] Type checker passes (mypy / tsc --noEmit).
- [ ] No secrets detected (gitleaks).

### Pull Request (CI)
- [ ] All unit tests pass.
- [ ] Integration tests pass.
- [ ] Code coverage ≥ 80% (new code ≥ 90%).
- [ ] No new security warnings (SAST clean).
- [ ] No dependency vulnerabilities introduced.
- [ ] At least one approving review.
- [ ] PR description includes: what, why, how to verify.

### Pre-Deploy (staging)
- [ ] E2E suite green.
- [ ] Performance regression < 10% vs. baseline.
- [ ] Database migrations tested forward and backward.
- [ ] Feature flags configured correctly.
- [ ] Smoke tests pass post-deploy.

### Post-Deploy (production)
- [ ] Canary health checks pass (error rate, latency).
- [ ] Monitoring dashboards reviewed for anomalies.
- [ ] Rollback plan documented and tested.

---

## 4. Code Review Checklist

### Correctness
- [ ] Logic matches requirements and acceptance criteria.
- [ ] Edge cases handled (null, empty, overflow, concurrency).
- [ ] Error paths return meaningful messages; no silent failures.
- [ ] No race conditions in async/concurrent code.

### Security
- [ ] Inputs validated and sanitised (SQL injection, XSS, SSRF).
- [ ] Secrets not hardcoded; use vault/env vars.
- [ ] Authentication and authorisation enforced.
- [ ] Dependencies are trusted and pinned.

### Maintainability
- [ ] Functions are small and single-purpose.
- [ ] Naming is clear; no abbreviations without context.
- [ ] No dead code or commented-out blocks.
- [ ] Complex logic has explanatory comments (why, not what).
- [ ] Follows project style guide.

### Testing
- [ ] New code has corresponding unit tests.
- [ ] Tests are deterministic and independent.
- [ ] Mocks are minimal — prefer real implementations where feasible.
- [ ] Test names describe the behaviour being verified.

### Performance
- [ ] No N+1 queries.
- [ ] Large datasets paginated or streamed.
- [ ] No unnecessary re-renders (frontend).
- [ ] Expensive operations cached where appropriate.

### Observability
- [ ] Key operations emit structured logs.
- [ ] Metrics emitted for business-critical paths.
- [ ] Traces propagate across service boundaries.
- [ ] Alerts configured for new failure modes.

---

## 5. Release Criteria

A release is ready when **all** of the following are true:

### Functional
- [ ] All acceptance criteria for the release scope are met.
- [ ] Zero open P0/P1 bugs.
- [ ] Known P2 bugs documented with workarounds or scheduled fixes.

### Quality
- [ ] All quality gates (Section 3) pass.
- [ ] Code coverage meets threshold.
- [ ] No critical or high-severity security findings.
- [ ] Performance benchmarks within acceptable range.

### Operational
- [ ] Runbook updated for new features or infrastructure changes.
- [ ] Monitoring and alerting configured.
- [ ] Rollback procedure tested within the last release cycle.
- [ ] On-call engineer briefed.

### Documentation
- [ ] API docs updated (OpenAPI/Swagger).
- [ ] User-facing changes have help text or changelog entries.
- [ ] Architecture Decision Records (ADRs) written for significant changes.

### Sign-Off
- [ ] Product owner approves feature completeness.
- [ ] Tech lead approves technical quality.
- [ ] Security review complete (if applicable).

---

## Incident Response & Postmortems

- **Severity 1** (data loss, security breach, full outage): Page immediately; fix forward or rollback within 1 hour.
- **Severity 2** (major feature broken): Fix within 4 hours or rollback.
- **Postmortem** required for all Sev-1 and Sev-2 incidents within 48 hours.
- Postmortems are blameless; focus on systemic fixes, not individual fault.

---

## Continuous Improvement

- Review test effectiveness quarterly: are we catching real bugs?
- Track escaped defects (bugs found in production) and feed them back as test cases.
- Retire flaky tests that cannot be fixed — they erode trust in the suite.
- Update this guide when processes change; keep it living, not shelfware.
