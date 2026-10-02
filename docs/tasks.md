# Task Management

## 1. Architecture

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart TD
    subgraph Sources
        UI[Web UI]
        API[REST API]
        CLI[CLI]
        EXT[External Systems]
    end

    subgraph Core
        TM[Task Manager]
        TS[Task Store]
        TQ[Task Queue]
        TW[Task Workers]
        TE[Task Events]
    end

    subgraph Support
        N[Notifications]
        S[Scheduler]
        L[Logger]
    end

    UI --> TM
    API --> TM
    CLI --> TM
    EXT --> TM

    TM --> TS
    TM --> TQ
    TQ --> TW
    TW --> TE
    TE --> N
    TE --> L
    S --> TQ
```

## 2. Task Types

| Type | Description | Priority | SLA |
|------|-------------|----------|-----|
| `bug` | Defect or regression | P1–P4 | 24h–14d |
| `feature` | New capability | P2–P3 | Sprint |
| `improvement` | Enhancement to existing | P3–P4 | Sprint |
| `tech_debt` | Refactoring / cleanup | P3–P4 | Backlog |
| `research` | Investigation / spike | P3 | 3d |
| `ops` | Operational / infra work | P1–P2 | 4h–2d |

## 3. Task Workflow

```mermaid
%%{init: {'theme':'dark'}}%%
stateDiagram-v2
    [*] --> backlog
    backlog --> triaged : Assign + Prioritize
    triaged --> in_progress : Pick up
    in_progress --> in_review : Submit
    in_review --> done : Approve
    in_review --> in_progress : Reject
    in_progress --> blocked : Dependency
    blocked --> in_progress : Unblocked
    in_progress --> cancelled : Won't fix
    in_review --> cancelled : Won't fix
    done --> [*]
    cancelled --> [*]
```

## 4. Task Assignment

- **Auto-assign**: Round-robin within team based on capacity
- **Manual**: Lead or PM assigns directly
- **Self-assign**: Team member picks from triaged pool
- **Escalation**: Unassigned P1 tasks auto-escalate to on-call after 1h

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    T[New Task] --> Q{Queue Type}
    Q -->|bug| B[Bug Queue]
    Q -->|feature| F[Feature Queue]
    Q -->|ops| O[Ops Queue]
    B --> A1[Auto Round-Robin]
    F --> A2[Lead Assigns]
    O --> A3[On-Call]
    A1 --> W[Worker]
    A2 --> W
    A3 --> W
```

## 5. Task Tracking

```mermaid
%%{init: {'theme':'dark'}}%%
gantt
    title Task Lifecycle Tracking
    dateFormat YYYY-MM-DD
    section States
    Triage       :t1, 2026-10-01, 1d
    In Progress  :t2, after t1, 3d
    Review       :t3, after t2, 1d
    Done         :t4, after t3, 1d
```

### Metrics

- **Cycle time**: Created → Done
- **Lead time**: Created → In Progress
- **WIP limit**: Max 3 active tasks per worker
- **SLA breach**: Alert when task exceeds SLA threshold
- **Throughput**: Tasks completed per sprint
