# New Projects — Cost Optimization Guide

> Applies to all new projects in the APEX-OS Business Platform. Target: minimize total cost of ownership (TCO) without sacrificing delivery speed or reliability.

---

## 1. Infrastructure Cost Optimization

### 1.1 Compute

- **Right-size from day one.** Start with burstable/tunable instance types (e.g., T-series, B-series) and scale vertically only when metrics justify it.
- **Use spot/preemptible instances** for stateless workloads, batch jobs, and CI/CD runners. Reserve on-demand capacity only for critical path services.
- **Containerize everything.** Kubernetes (EKS/GKE/AKS) with horizontal pod autoscaling (HPA) and cluster autoscaler reduces idle capacity by 30–50 %.
- **Serverless for spiky workloads.** Use Lambda, Cloud Functions, or Cloud Run for APIs with variable traffic; pay-per-request beats idle VMs.
- **Multi-AZ only where required.** Non-critical services can run single-AZ with automated failover scripts.

### 1.2 Storage

- **Tier data automatically.** Move cold objects to infrequent-access or archive storage after 30/60/90 days via lifecycle policies.
- **Compress and deduplicate** before persisting logs, backups, and media assets.
- **Use object storage (S3/GCS)** over block storage for anything that doesn't need a filesystem.
- **Delete aggressively.** Set TTLs on temporary files, orphaned snapshots, and unused volumes.

### 1.3 Networking

- **Keep traffic intra-region.** Cross-region data transfer is the most common hidden cost.
- **Use a CDN** (CloudFront, Cloudflare, Fastly) for all static assets and public APIs.
- **VPC endpoints / PrivateLink** instead of NAT Gateway for AWS service access — saves $30–50/month per AZ.
- **Monitor egress.** Alert on any service exceeding 100 GB/month outbound.

### 1.4 Cloud Provider Strategy

- **Avoid multi-cloud for new projects** unless there is a hard compliance or latency requirement. Multi-cloud adds 20–40 % overhead in tooling, expertise, and data transfer.
- **Commit to reserved instances / savings plans** only after 2–3 weeks of stable usage data.
- **Use managed services** (RDS, Cloud SQL, ElastiCache) when the team lacks dedicated ops — the premium is cheaper than a part-time DBA.

### 1.5 Cost Monitoring

- Tag every resource with `project`, `environment`, `owner`, `cost-center`.
- Enable billing alerts at 50 %, 80 %, and 100 % of budget.
- Run weekly cost reviews using cloud-native tools (AWS Cost Explorer, GCP Cost Table) or third-party (Vantage, Kubecost).

---

## 2. Development Cost Optimization

### 2.1 Team Structure

- **Small, senior teams outperform large, junior teams.** A team of 3 senior engineers typically delivers the same output as 5–6 junior engineers at lower total cost and higher quality.
- **Use staff/platform engineers** to build internal tooling that accelerates all product teams.
- **Avoid over-hiring early.** Contract or fractional specialists for niche needs (security, ML, mobile) instead of full-time hires.

### 2.2 Tooling & Automation

- **Invest in CI/CD from day one.** Automated testing and deployment reduces rework cost by 40–60 %.
- **Use monorepo tooling** (Nx, Turborepo, Bazel) to share code, configs, and CI pipelines across services.
- **Adopt infrastructure-as-code** (Terraform, Pulumi) to eliminate manual environment setup and drift.
- **Standardize on a single framework** per language to reduce context-switching and onboarding time.

### 2.3 Code Quality & Technical Debt

- **Enforce code review** — a single review catches 60–90 % of defects before they reach production.
- **Write tests for critical paths.** Unit tests for business logic, integration tests for API contracts, E2E tests for user journeys only.
- **Refactor continuously.** Allocate 10–15 % of each sprint to paying down technical debt.
- **Use static analysis** (SonarQube, ESLint, Semgrep) to catch issues before they become bugs.

### 2.4 Build & Test Speed

- **Parallelize CI pipelines.** Use build caching (remote cache, layer caching) to keep builds under 5 minutes.
- **Run only affected tests** in PR pipelines; full suite runs on merge to main.
- **Use ephemeral preview environments** instead of shared staging — reduces coordination cost and environment contention.

### 2.5 Documentation

- **Docs as code.** Keep architecture decision records (ADRs), API docs, and runbooks in the same repo as the code.
- **Automate API documentation** from OpenAPI specs to eliminate drift.
- **Write runbooks for every operational procedure** — reduces on-call burden and incident MTTR.

---

## 3. Operational Cost Optimization

### 3.1 Observability

- **Use open standards** (OpenTelemetry) to avoid vendor lock-in and reduce licensing costs.
- **Sample traces** in production (10–20 % for normal traffic, 100 % for errors) to control observability data volume costs.
- **Centralize logs** with a retention policy: 7 days hot, 30 days warm, 1 year cold (compliance-dependent).
- **Alert on symptoms, not causes.** Reduce alert fatigue and on-call burnout.

### 3.2 Incident Management

- **Define SLOs/SLIs for every service.** Error budgets guide release velocity and reliability investment.
- **Automate rollback.** Automated canary analysis (Argo Rollouts, Flagger) reduces incident duration by 50–70 %.
- **Conduct blameless postmortems** for every SEV-1/SEV-2 incident. Track action items to completion.
- **Maintain a runbook for every alert** — unactionable alerts waste on-call time.

### 3.3 On-Call & Support

- **Follow-the-sun on-call** if the team is distributed; otherwise, limit on-call rotations to one week per engineer.
- **Compensate on-call** fairly — burnout is a hidden cost that compounds.
- **Use chatOps** (Slack + PagerDuty/Opsgenie) to reduce context-switching during incidents.

### 3.4 Backup & Disaster Recovery

- **3-2-1 backup rule:** 3 copies, 2 media types, 1 offsite.
- **Test restores quarterly.** Untested backups are not backups.
- **Define RTO/RPO per service** and implement only to the required level — over-engineering DR is expensive.

### 3.5 Capacity Planning

- **Forecast growth** using historical metrics and business projections.
- **Scale proactively** — don't wait for paging to add capacity.
- **Use load testing** (k6, Locust) before major launches to validate capacity assumptions.

---

## 4. Licensing Optimization

### 4.1 Open Source First

- **Default to MIT/Apache-2.0/BSD-licensed dependencies.** Avoid GPL/AGPL in proprietary products unless the team understands the implications.
- **Use an SBOM** (Software Bill of Materials) to track all dependencies and their licenses.
- **Automate license scanning** (FOSSA, Snyk, GitHub Dependency Graph) in CI.

### 4.2 Commercial Software

- **Audit all licenses quarterly.** Remove unused seats, downgrade plans, and eliminate shelfware.
- **Negotiate enterprise agreements** once spend exceeds $10K/year with any vendor.
- **Prefer usage-based pricing** over per-seat for tools with variable adoption.
- **Evaluate open-source alternatives** before purchasing: e.g., Grafana vs. Datadog, Metabase vs. Looker, Keycloak vs. Auth0.

### 4.3 Cloud Service Licensing

- **Bring Your Own License (BYOL)** when you already own perpetual licenses for databases or middleware.
- **Use cloud provider marketplace offerings** only when the managed service premium is justified.
- **Avoid per-core licensing** in cloud environments — it scales linearly with instance size and can become the dominant cost.

### 4.4 Developer Tools

- **Consolidate tools.** Each additional tool adds license cost, integration cost, and cognitive load.
- **Use free tiers** for small teams: GitHub Team, Linear, Vercel, etc.
- **Review seat counts monthly.** Remove licenses from departed employees and inactive accounts.

---

## 5. ROI Analysis

### 5.1 Cost Categories

| Category | Typical % of TCO | Optimization Lever |
|---|---|---|
| Infrastructure (cloud) | 30–50 % | Right-sizing, spot, serverless, reserved |
| Personnel (dev + ops) | 40–60 % | Senior teams, automation, reduced rework |
| Licensing (tools + SaaS) | 5–15 % | Open source, seat audits, consolidation |
| Training & onboarding | 2–5 % | Documentation, standardized tooling |
| Incident & downtime | 5–10 % | Observability, automation, SLOs |

### 5.2 Key Metrics to Track

- **Cost per transaction/request** — the ultimate unit economics metric.
- **Cost per developer per month** — total spend / headcount.
- **Infrastructure cost as % of revenue** — should decrease as revenue grows.
- **Mean time to recovery (MTTR)** — directly correlates with downtime cost.
- **Deployment frequency** — higher frequency with stable failure rate indicates healthy automation investment.

### 5.3 Investment Priorities (by ROI)

1. **CI/CD and automation** — highest ROI. Reduces rework, accelerates delivery, and cuts on-call burden.
2. **Observability** — high ROI. Reduces MTTR and prevents revenue loss from downtime.
3. **Right-sizing infrastructure** — immediate cost savings with no delivery impact.
4. **Developer experience (DX) tooling** — medium ROI. Reduces onboarding time and context-switching.
5. **Training** — medium ROI. Reduces errors and accelerates feature delivery.

### 5.4 Break-Even Analysis

For any optimization initiative, calculate:

```
Break-even (months) = Implementation cost / Monthly savings
```

Prioritize initiatives with break-even < 6 months. Reject initiatives with break-even > 18 months unless they address a critical risk or compliance requirement.

### 5.5 Quarterly Cost Review Template

1. **Total spend** by category and by service.
2. **Cost per transaction** trend (should be flat or decreasing).
3. **Top 10 most expensive resources** — justify or eliminate.
4. **License utilization** — identify unused or underused seats.
5. **Optimization initiatives** — status, savings realized, next steps.
6. **Forecast** — projected spend for next quarter based on growth plans.

---

## Summary

Cost optimization is not a one-time exercise — it is a continuous discipline. The highest-leverage investments are automation, observability, and right-sizing. Track unit economics, review costs quarterly, and always calculate break-even before committing to an optimization initiative.
