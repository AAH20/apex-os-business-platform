# Projects

## Architecture

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart TB
    subgraph PM["Project Management Core"]
        P[Project] --> T[Task]
        T --> S[Subtask]
        T --> D[Dependency]
        P --> M[Milestone]
        M --> T
    end

    subgraph RES["Resource Layer"]
        R[Resource] --> A[Allocation]
        A --> T
        TE[Team] --> R
    end

    subgraph TRK["Tracking Layer"]
        L[Time Log] --> T
        L --> R
        B[Budget] --> P
        B --> L
    end

    subgraph RPT["Reporting Layer"]
        RP[Report] --> P
        RP --> T
        RP --> L
        RP --> B
        DASH[Dashboard] --> RP
    end

    PM --> RES
    RES --> TRK
    TRK --> RPT
```

## Task Management

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier |
| title | string | Short task name |
| status | enum | `todo` / `in_progress` / `review` / `done` |
| priority | enum | `low` / `medium` / `high` / `critical` |
| assignee | FK → Resource | Owner of the task |
| project | FK → Project | Parent project |
| estimate | hours | Planned effort |
| due_date | date | Deadline |
| tags | string[] | Labels for filtering |

**Workflow:** `todo → in_progress → review → done`

- Tasks support subtrees (parent/child) for breakdown
- Dependencies block downstream tasks until resolved
- Milestones group tasks by deliverable deadlines

## Resource Allocation

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    subgraph TEAM["Team"]
        E1[Engineer]
        E2[Designer]
        E3[PM]
    end

    subgraph POOL["Resource Pool"]
        CAP[Capacity<br/>40h/week]
        SKILL[Skill Matrix]
    end

    subgraph ASSIGN["Assignment"]
        T1[Task A<br/>20h]
        T2[Task B<br/>15h]
        T3[Task C<br/>10h]
    end

    TEAM --> POOL
    POOL --> ASSIGN
```

- Each resource has a **capacity** (hours/week) and **skill tags**
- Allocation = sum of assigned task estimates per resource
- Over-allocation flagged when assigned > capacity
- Rebalancing moves tasks from overloaded to underloaded resources

## Time Tracking

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Log entry ID |
| task | FK → Task | Related task |
| resource | FK → Resource | Who logged time |
| date | date | Day of work |
| hours | decimal | Hours spent |
| billable | boolean | Billable or internal |
| description | text | What was done |

- Time logged rolls up to task → project → budget
- Budget burn = sum(logged hours × resource rate)
- Timesheets are weekly views filtered by resource

## Reporting

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    subgraph DATA["Data Sources"]
        TS[Time Sheets]
        TK[Tasks]
        BUD[Budgets]
    end

    subgraph MET["Metrics"]
        VEL[Velocity]
        BRN[Burn Rate]
        CPI[Cost Perf. Index]
        UTIL[Utilization %]
    end

    subgraph OUT["Outputs"]
        Gantt[Gantt Chart]
        Burndown[Burndown]
        Heatmap[Utilization Heatmap]
        CSV[CSV Export]
    end

    DATA --> MET
    MET --> OUT
```

**Standard reports:**

- **Burndown** — remaining work vs. ideal trajectory
- **Velocity** — completed story points per sprint
- **Utilization** — logged hours / capacity per resource
- **Budget vs. Actual** — planned spend vs. logged cost
- **Gantt** — timeline view of tasks and milestones
