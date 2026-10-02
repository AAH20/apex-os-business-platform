# Contract Management

## 1. Architecture

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TB
    subgraph Sources["Contract Sources"]
        CRM[CRM / Sales]
        LEGAL[Legal Review]
        VENDOR[Vendor Portal]
        EMAIL[Email Intake]
    end

    subgraph Core["Contract Management Core"]
        INTAKE[Intake & Capture]
        PARSE[AI Extraction]
        REPO[Contract Repository]
        SEARCH[Search & Index]
        OBLIGATE[Obligation Engine]
        ALERT[Alert Service]
    end

    subgraph Lifecycle["Lifecycle Management"]
        DRAFT[Draft]
        REVIEW[Review]
        APPROVE[Approve]
        SIGN[Sign]
        EXECUTE[Execute]
        RENEW[Renew / Terminate]
    end

    subgraph Compliance["Compliance & Audit"]
        AUDIT[Audit Trail]
        POLICY[Policy Engine]
        REPORT[Reporting]
    end

    Sources --> INTAKE
    INTAKE --> PARSE
    PARSE --> REPO
    REPO --> SEARCH
    REPO --> OBLIGATE
    OBLIGATE --> ALERT
    REPO --> Lifecycle
    Lifecycle --> Compliance
    Compliance --> REPO
```

## 2. Contract Lifecycle

```mermaid
%%{init: {'theme': 'dark'}}%%
stateDiagram-v2
    [*] --> Draft
    Draft --> Review: Submit
    Review --> Draft: Reject
    Review --> Approve: Approved
    Approve --> Sign: Send for Signature
    Sign --> Execute: Fully Signed
    Execute --> Active: Effective Date
    Active --> Renewal: 90 days before expiry
    Renewal --> Active: Renewed
    Renewal --> Expired: Not renewed
    Active --> Terminated: Early termination
    Terminated --> [*]
    Expired --> [*]
```

### Stage Definitions

| Stage | Owner | Key Actions |
|-------|-------|-------------|
| Draft | Requestor | Create, attach, populate terms |
| Review | Legal / Manager | Redline, negotiate, approve |
| Approve | Authorized Signatory | Final approval |
| Sign | Both Parties | E-signature execution |
| Execute | System | Store, index, activate obligations |
| Active | Account Manager | Monitor compliance, obligations |
| Renewal | Account Manager | Initiate renewal or termination |

## 3. Contract Templates

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    subgraph Templates["Template Library"]
        MSA[MSA Template]
        NDA[NDA Template]
        SOW[SOW Template]
        DPA[DPA Template]
        SLA[SLA Template]
        AMEND[Amendment Template]
    end

    subgraph Variables["Template Variables"]
        PARTY[Party Name]
        DATE[Effective Date]
        TERM[Term / Duration]
        VALUE[Contract Value]
        JURIS[Jurisdiction]
    end

    Templates --> Variables
    Variables --> GEN[Generated Contract]
```

### Template Types

- **MSA** — Master Service Agreement (umbrella terms)
- **NDA** — Non-Disclosure Agreement (mutual / one-way)
- **SOW** — Statement of Work (project scope, deliverables)
- **DPA** — Data Processing Agreement (privacy compliance)
- **SLA** — Service Level Agreement (performance metrics)
- **Amendment** — Contract modification / extension

### Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{party_name}}` | Counterparty legal name | Acme Corp |
| `{{effective_date}}` | Contract start date | 2026-01-01 |
| `{{term_months}}` | Duration in months | 12 |
| `{{value}}` | Total contract value | $500,000 |
| `{{jurisdiction}}` | Governing law | Delaware, USA |
| `{{renewal_notice_days}}` | Notice period for renewal | 90 |

## 4. Contract Compliance

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TB
    subgraph Monitor["Compliance Monitoring"]
        OBLIG[Obligations]
        MILESTONE[Milestones]
        DELIVER[Deliverables]
        PAYMENT[Payment Terms]
    end

    subgraph Checks["Automated Checks"]
        DATE_CHECK[Date Validation]
        VALUE_CHECK[Value Threshold]
        POLICY_CHECK[Policy Conformance]
        RISK_CHECK[Risk Scoring]
    end

    subgraph Actions["Compliance Actions"]
        FLAG[Flag Violation]
        NOTIFY[Notify Owner]
        ESCALATE[Escalate]
        REMEDIATE[Remediation Plan]
    end

    Monitor --> Checks
    Checks --> Actions
    Actions --> OBLIG
```

### Compliance Rules

| Rule | Description | Severity |
|------|-------------|----------|
| Expiry Alert | Notify 90/60/30 days before expiry | High |
| Payment Due | Alert 7 days before payment due date | Medium |
| Deliverable Missed | Flag overdue deliverables | High |
| Value Threshold | Escalate contracts > $100K for review | Medium |
| Policy Violation | Auto-flag non-standard clauses | High |
| Auto-Renewal | Flag auto-renewal clauses without opt-out | Medium |

### Risk Scoring

- **Low (0-30)** — Standard terms, reputable counterparty
- **Medium (31-60)** — Non-standard clauses, moderate value
- **High (61-100)** — Unusual terms, high value, or compliance flags

## 5. Contract Renewal

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    subgraph Trigger["Renewal Trigger"]
        T90[90-Day Alert]
        T60[60-Day Alert]
        T30[30-Day Alert]
    end

    subgraph Process["Renewal Process"]
        EVAL[Evaluate Performance]
        NEGOTIATE[Negotiate Terms]
        DRAFT_RENEW[Draft Renewal]
        APPROVE_RENEW[Approve Renewal]
        SIGN_RENEW[Sign Renewal]
    end

    subgraph Outcome["Outcome"]
        RENEWED[Renewed]
        TERMINATED[Terminated]
        LAPSED[Lapsed]
    end

    Trigger --> EVAL
    EVAL --> NEGOTIATE
    NEGOTIATE --> DRAFT_RENEW
    DRAFT_RENEW --> APPROVE_RENEW
    APPROVE_RENEW --> SIGN_RENEW
    SIGN_RENEW --> RENEWED
    EVAL --> TERMINATED
    NEGOTIATE --> LAPSED
```

### Renewal Timeline

| Days Before Expiry | Action | Owner |
|-------------------|--------|-------|
| 90 | Initial alert, performance review | Account Manager |
| 60 | Renewal recommendation, negotiation start | Account Manager + Legal |
| 30 | Final renewal terms, approval | Legal + Management |
| 15 | Signature collection | Both Parties |
| 7 | Execution, archive old version | System |
| 0 | New contract effective | System |

### Renewal Decision Matrix

| Performance | Recommendation | Action |
|-------------|---------------|--------|
| Exceeds expectations | Renew + expand | Negotiate better terms |
| Meets expectations | Renew as-is | Standard renewal |
| Below expectations | Renegotiate | Adjust terms or scope |
| Unsatisfactory | Terminate | Initiate exit plan |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/contracts` | List all contracts |
| POST | `/api/contracts` | Create new contract |
| GET | `/api/contracts/{id}` | Get contract details |
| PUT | `/api/contracts/{id}` | Update contract |
| DELETE | `/api/contracts/{id}` | Delete draft contract |
| POST | `/api/contracts/{id}/submit` | Submit for review |
| POST | `/api/contracts/{id}/approve` | Approve contract |
| POST | `/api/contracts/{id}/sign` | Mark as signed |
| GET | `/api/contracts/{id}/obligations` | List obligations |
| GET | `/api/contracts/{id}/audit` | Get audit trail |
| POST | `/api/contracts/{id}/renew` | Initiate renewal |
| GET | `/api/templates` | List templates |
| POST | `/api/templates/generate` | Generate from template |
