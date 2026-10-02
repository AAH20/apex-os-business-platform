# HR Architecture

## 1. HR Data Model

```mermaid
%%{init: {'theme': 'dark'}}%%
erDiagram
    EMPLOYEE ||--o{ EMPLOYMENT_HISTORY : has
    EMPLOYEE ||--o{ PAYROLL_RECORD : receives
    EMPLOYEE ||--o{ PERFORMANCE_REVIEW : undergoes
    EMPLOYEE ||--o{ RECRUITMENT_CANDIDATE : sourced_from
    EMPLOYEE ||--o{ LEAVE_REQUEST : submits
    EMPLOYEE ||--o{ BENEFIT_ENROLLMENT : enrolls
    EMPLOYEE {
        uuid id PK
        string employee_number UK
        string first_name
        string last_name
        string email UK
        string phone
        date date_of_birth
        string gender
        string nationality
        string national_id
        uuid department_id FK
        uuid job_title_id FK
        uuid manager_id FK
        string employment_type
        string employment_status
        date hire_date
        date termination_date
        decimal salary
        string currency
        string pay_frequency
        string bank_account
        timestamp created_at
        timestamp updated_at
    }
    DEPARTMENT ||--o{ EMPLOYEE : employs
    DEPARTMENT {
        uuid id PK
        string name
        string code UK
        uuid parent_department_id FK
        uuid head_employee_id FK
        string cost_center
        boolean active
    }
    JOB_TITLE ||--o{ EMPLOYEE : defines
    JOB_TITLE {
        uuid id PK
        string title
        string job_family
        string job_level
        decimal min_salary
        decimal max_salary
        text description
        text requirements
    }
    EMPLOYMENT_HISTORY {
        uuid id PK
        uuid employee_id FK
        string event_type
        date effective_date
        uuid department_id FK
        uuid job_title_id FK
        decimal salary_change
        string reason
        uuid approved_by FK
    }
    PAYROLL_RECORD {
        uuid id PK
        uuid employee_id FK
        date pay_period_start
        date pay_period_end
        decimal gross_pay
        decimal tax_deduction
        decimal social_security
        decimal other_deductions
        decimal net_pay
        string payment_status
        date payment_date
    }
    PERFORMANCE_REVIEW {
        uuid id PK
        uuid employee_id FK
        uuid reviewer_id FK
        string review_cycle
        date review_date
        int overall_rating
        text goals
        text achievements
        text development_plan
        string status
    }
    RECRUITMENT_CANDIDATE {
        uuid id PK
        string first_name
        string last_name
        string email UK
        string phone
        string source
        uuid requisition_id FK
        string stage
        date applied_date
        uuid employee_id FK
    }
    LEAVE_REQUEST {
        uuid id PK
        uuid employee_id FK
        string leave_type
        date start_date
        date end_date
        decimal days_requested
        string status
        uuid approved_by FK
        text reason
    }
    BENEFIT_ENROLLMENT {
        uuid id PK
        uuid employee_id FK
        string benefit_type
        string plan_name
        date enrollment_date
        date coverage_start
        date coverage_end
        decimal employee_contribution
        decimal employer_contribution
    }
    DEPARTMENT ||--o{ JOB_TITLE : categorizes
```

## 2. Employee Lifecycle

```mermaid
%%{init: {'theme': 'dark'}}%%
stateDiagram-v2
    [*] --> Onboarding: Hire
    Onboarding --> Active: Complete onboarding
    Active --> Active: Role change / Promotion
    Active --> On_Leave: Approved leave
    On_Leave --> Active: Return from leave
    Active --> Suspended: Disciplinary action
    Suspended --> Active: Reinstatement
    Suspended --> Terminated: Termination upheld
    Active --> Terminated: Resignation / Termination
    Terminated --> [*]: Exit complete

    state Onboarding {
        [*] --> DocumentCollection
        DocumentCollection --> BackgroundCheck
        BackgroundCheck --> AccountSetup
        AccountSetup --> BenefitsEnrollment
        BenefitsEnrollment --> Orientation
        Orientation --> [*]
    }

    state Active {
        [*] --> RegularDuties
        RegularDuties --> Training: Assigned
        Training --> RegularDuties: Completed
        RegularDuties --> PerformanceReview: Cycle start
        PerformanceReview --> RegularDuties: Completed
    }

    state Terminated {
        [*] --> OffboardingInitiated
        OffboardingInitiated --> AssetReturn
        AssetReturn --> AccessRevocation
        AccessRevocation --> FinalPayroll
        FinalPayroll --> ExitInterview
        ExitInterview --> [*]
    }
```

## 3. Payroll Processing

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    A[Pay Period Start] --> B[Collect Time & Attendance]
    B --> C[Calculate Gross Pay]
    C --> D[Apply Overtime & Bonuses]
    D --> E[Calculate Deductions]
    E --> F[Tax Withholding]
    F --> G[Social Security & Medicare]
    G --> H[Benefit Deductions]
    H --> I[Other Deductions]
    I --> J[Calculate Net Pay]
    J --> K[Generate Pay Stubs]
    K --> L[Manager Approval]
    L --> M{Approved?}
    M -->|No| N[Return for Correction]
    N --> C
    M -->|Yes| O[Submit to Bank]
    O --> P[Direct Deposit / Check]
    P --> Q[Update General Ledger]
    Q --> R[Archive Payroll Records]
    R --> S[Pay Period End]

    subgraph PrePayroll
        B
        C
        D
    end

    subgraph Deductions
        F
        G
        H
        I
    end

    subgraph PostPayroll
        Q
        R
    end
```

## 4. Performance Management

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    A[Goal Setting] --> B[Mid-Year Review]
    B --> C[Continuous Feedback]
    C --> D[Year-End Review]
    D --> E[Calibration]
    E --> F[Rating Assignment]
    F --> G[Compensation Adjustment]
    G --> H[Development Plan]
    H --> I[Promotion Decision]
    I --> J[Succession Planning]
    J --> A

    subgraph GoalSetting {
        A1[SMART Goals] --> A2[Manager Alignment]
        A2 --> A3[Employee Acknowledgment]
    }

    subgraph ReviewProcess {
        D1[Self Assessment] --> D2[Peer Feedback]
        D2 --> D3[Manager Assessment]
        D3 --> D4[360° Review]
    }

    subgraph Outcomes {
        F1[Exceeds Expectations] --> F2[Merit Increase + Bonus]
        F3[Meets Expectations] --> F4[Standard Merit Increase]
        F5[Needs Improvement] --> F6[Performance Improvement Plan]
    }

    subgraph Development {
        H1[Training Needs] --> H2[Skill Gap Analysis]
        H2 --> H3[Career Pathing]
        H3 --> H4[Mentorship Assignment]
    }
```

## 5. Recruitment Pipeline

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart TD
    A[Requisition Created] --> B[Requisition Approved]
    B --> C[Job Posting]
    C --> D[Application Received]
    D --> E[Resume Screening]
    E --> F{Qualified?}
    F -->|No| G[Reject / Talent Pool]
    F -->|Yes| H[Phone Screen]
    H --> I{Pass?}
    I -->|No| G
    I -->|Yes| J[Technical Assessment]
    J --> K{Pass?}
    K -->|No| G
    K -->|Yes| L[Panel Interview]
    L --> M{Pass?}
    M -->|No| G
    M -->|Yes| N[Cultural Fit Interview]
    N --> O{Pass?}
    O -->|No| G
    O -->|Yes| P[Background Check]
    P --> Q{Clear?}
    Q -->|No| G
    Q -->|Yes| R[Offer Extended]
    R --> S{Accepted?}
    S -->|No| G
    S -->|Yes| T[Pre-Boarding]
    T --> U[Onboarding Scheduled]
    U --> V[Hired]

    subgraph Sourcing {
        C1[Job Boards] --> C2[Social Media]
        C2 --> C3[Employee Referrals]
        C3 --> C4[Recruitment Agencies]
        C4 --> C5[Career Site]
    }

    subgraph Assessment {
        J1[Coding Test] --> J2[Case Study]
        J2 --> J3[Role Play]
        J3 --> J4[Personality Test]
    }
```
