# APEX-OS Support

## 1. Support Architecture

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TB
    subgraph Channels
        Email[Email]
        Chat[Live Chat]
        Phone[Phone]
        Portal[Self-Service Portal]
        API[API / Webhook]
    end

    subgraph Intake
        Router[Smart Router]
        Tagger[Auto-Tagger]
        Dedup[De-Duplication]
    end

    subgraph Core
        TicketDB[(Ticket Store)]
        KB[(Knowledge Base)]
        UserDB[(User Directory)]
        Workflow[Workflow Engine]
    end

    subgraph Resolution
        L1[L1 Support]
        L2[L2 Engineering]
        L3[L3 Specialist]
        Bot[AI Copilot]
    end

    subgraph Observability
        SLA[SLA Monitor]
        CSAT[CSAT / NPS]
        Reports[Analytics]
    end

    Email & Chat & Phone & Portal & API --> Router
    Router --> Tagger --> Dedup
    Dedup --> TicketDB
    TicketDB --> Workflow
    Workflow --> L1
    L1 -->|Escalate| L2
    L2 -->|Escalate| L3
    Bot -.Assists.-> L1 & L2
    KB -.Suggests.-> Bot & L1
    UserDB -.Enriches.-> Router
    TicketDB --> SLA
    SLA --> Reports
    L1 & L2 & L3 --> CSAT
```

## 2. Ticket Management

### Priority Matrix

| Priority | Description | Response Target | Resolution Target |
|----------|-------------|-----------------|-------------------|
| P1 – Critical | Service down / data loss | 15 min | 4 hours |
| P2 – High | Major feature broken | 1 hour | 8 hours |
| P3 – Medium | Partial degradation | 4 hours | 24 hours |
| P4 – Low | General question / cosmetic | 1 business day | 72 hours |

### Lifecycle

```mermaid
%%{init: {'theme': 'dark'}}%%
stateDiagram-v2
    [*] --> New
    New --> Triaged: Auto-tag + assign
    Triaged --> InProgress: Agent picks up
    InProgress --> Waiting: Needs user input
    Waiting --> InProgress: User responds
    InProgress --> Resolved: Fix confirmed
    Resolved --> Closed: CSAT collected
    Resolved --> InProgress: Reopened by user
    Closed --> [*]
    New --> Cancelled: Duplicate / spam
    Cancelled --> [*]
```

### Rules

- Auto-close after 7 days of user inactivity (with warning at day 5).
- Reopen window: 14 days post-closure.
- Merge duplicates; link related tickets.
- All internal notes flagged `[internal]` — never visible to customers.

## 3. Knowledge Base

### Structure

```
kb/
├── getting-started/       # Onboarding, quickstart
├── how-to/                # Task-oriented guides
├── troubleshooting/       # Symptom → cause → fix
├── api-reference/         # Endpoint docs, schemas
├── faq/                   # Top 50 questions
├── release-notes/         # Changelog per version
└── internal/              # Runbooks, escalation paths
```

### Article Standards

- Every article: **title**, **last-reviewed date**, **owner**, **tags**.
- Screenshots for UI steps; copy-paste snippets for CLI/API.
- Link related articles bidirectionally.
- Deprecate (don't delete) outdated content with redirect notice.

### Maintenance

- Monthly review cycle: flag articles with > 90 days since review.
- Auto-flag articles linked from resolved tickets with low CSAT.
- Community contributions via PR; L2 approves before publish.

## 4. Live Chat

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant U as User
    participant W as Widget
    participant B as Bot
    participant A as Agent
    participant KB as Knowledge Base

    U->>W: Opens chat
    W->>B: Context (page, user ID, plan)
    B->>KB: Suggest articles
    B-->>U: Show suggestions
    U->>B: Types question
    B->>B: Intent + sentiment
    alt Confident match
        B-->>U: Answer + article link
    else Needs human
        B->>A: Transfer with transcript + summary
        A-->>U: Greets, continues
    end
    U->>A: Follow-up
    A->>KB: Search for solution
    A-->>U: Resolution
    U->>W: Rate chat (CSAT)
```

### Guidelines

- Bot handles ~60 % of chats; seamless human handoff with full context.
- Max queue wait: 2 minutes (P1) / 5 minutes (P2+).
- Proactive trigger: user visits pricing page 3× in one session.
- Offline hours: chat captures email, creates P3 ticket.

## 5. SLA Management

### SLA Tiers by Plan

| Plan | Coverage | P1 Response | P2 Response | P3/P4 Response |
|------|----------|-------------|-------------|----------------|
| Community | Forum only | — | — | — |
| Starter | Business hours | 4 h | 8 h | 24 h |
| Business | 24 × 7 | 1 h | 4 h | 12 h |
| Enterprise | 24 × 7 + dedicated CSM | 15 min | 1 h | 4 h |

### SLA Clock Rules

- Pauses when status = **Waiting on Customer**.
- Pauses outside business hours (except Enterprise 24 × 7).
- Resumes on customer reply or internal status change.
- Breach warning at 80 % of target; escalate to manager at 90 %.

### Monitoring & Reporting

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    T[Ticket Events] --> C[SLA Clock]
    C --> M{SLA Met?}
    M -->|Yes| G[Green ✅]
    M -->|No| R[Red 🚨]
    R --> N[Notify Agent + Manager]
    N --> E[Escalation Path]
    G --> D[(SLA Metrics)]
    E --> D
    D --> Dash[Dashboard]
    D --> WBR[Weekly Business Review]
```

### Escalation Path

1. **Agent** — owns ticket, first responder.
2. **Team Lead** — breach risk or P1 unresolved > 2 h.
3. **Support Manager** — P1 breach or pattern of breaches.
4. **VP Engineering** — systemic outage, enterprise escalation.

### Metrics Tracked

- **FRT** — First Response Time
- **MTTR** — Mean Time to Resolution
- **SLA Achievement %** — target ≥ 95 %
- **CSAT** — target ≥ 4.5 / 5
- **Reopen Rate** — target < 8 %
