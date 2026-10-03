# CRUD Architecture

## 1. CRUD System Overview

The APEX-OS Business Platform implements a layered CRUD (Create, Read, Update, Delete) architecture that governs all persistent data operations across the system. This architecture ensures consistent data handling, validation, and access control for every entity in the platform.

### Core Principles

- **Separation of Concerns**: Each CRUD operation is isolated into distinct layers (Controller → Service → Repository → Database)
- **Validation at Boundaries**: All input is validated at the API boundary before reaching business logic
- **Audit Trail**: Every mutation operation is logged with timestamp, user, and change details
- **Soft Deletes**: Entities are soft-deleted by default; hard deletes require explicit admin action
- **Pagination & Filtering**: All list endpoints support cursor-based pagination and field-level filtering

### Entity Categories

| Category | Examples | Storage |
|----------|----------|---------|
| Core Business | Orders, Customers, Products | PostgreSQL |
| User Management | Users, Roles, Permissions | PostgreSQL |
| Content | Articles, Media, Documents | PostgreSQL + S3 |
| Audit | Logs, Events, History | PostgreSQL (partitioned) |
| Cache | Sessions, Rate Limits | Redis |

---

## 2. CRUD Component Diagram

```mermaid
graph TB
    subgraph Client Layer
        Web[Web App]
        Mobile[Mobile App]
        API[API Consumers]
    end

    subgraph API Gateway
        Auth[Auth Middleware]
        RateLimit[Rate Limiter]
        Router[Route Dispatcher]
    end

    subgraph Controller Layer
        C_Create[Create Controller]
        C_Read[Read Controller]
        C_Update[Update Controller]
        C_Delete[Delete Controller]
    end

    subgraph Service Layer
        S_Create[Create Service]
        S_Read[Read Service]
        S_Update[Update Service]
        S_Delete[Delete Service]
        Validation[Validation Engine]
        EventBus[Event Bus]
    end

    subgraph Repository Layer
        R_Create[Create Repo]
        R_Read[Read Repo]
        R_Update[Update Repo]
        R_Delete[Delete Repo]
        UnitOfWork[Unit of Work]
    end

    subgraph Data Layer
        PG[(PostgreSQL)]
        Redis[(Redis Cache)]
        S3[(S3 Storage)]
    end

    Web --> Auth
    Mobile --> Auth
    API --> Auth
    Auth --> RateLimit --> Router
    Router --> C_Create & C_Read & C_Update & C_Delete
    C_Create --> S_Create
    C_Read --> S_Read
    C_Update --> S_Update
    C_Delete --> S_Delete
    S_Create & S_Read & S_Update & S_Delete --> Validation
    S_Create --> R_Create
    S_Read --> R_Read
    S_Update --> R_Update
    S_Delete --> R_Delete
    R_Create & R_Read & R_Update & R_Delete --> UnitOfWork
    UnitOfWork --> PG
    S_Read --> Redis
    S_Create --> EventBus
    S_Update --> EventBus
    S_Delete --> EventBus
    EventBus --> S3
```

---

## 3. CRUD Data Flow Diagram

```mermaid
sequenceDiagram
    participant Client
    participant Gateway
    participant Controller
    participant Service
    participant Repository
    participant Database
    participant EventBus

    Note over Client,EventBus: CREATE Flow
    Client->>Gateway: POST /api/v1/entities
    Gateway->>Controller: Validate & Forward
    Controller->>Service: create(dto)
    Service->>Service: Validate Business Rules
    Service->>Repository: insert(entity)
    Repository->>Database: INSERT
    Database-->>Repository: entity + id
    Repository-->>Service: persisted entity
    Service->>EventBus: publish(EntityCreated)
    Service-->>Controller: Response DTO
    Controller-->>Gateway: 201 Created
    Gateway-->>Client: JSON Response

    Note over Client,EventBus: READ Flow
    Client->>Gateway: GET /api/v1/entities/:id
    Gateway->>Controller: Validate & Forward
    Controller->>Service: findById(id)
    Service->>Repository: findById(id)
    Repository->>Database: SELECT
    Database-->>Repository: row data
    Repository-->>Service: entity
    Service-->>Controller: Response DTO
    Controller-->>Gateway: 200 OK
    Gateway-->>Client: JSON Response

    Note over Client,EventBus: UPDATE Flow
    Client->>Gateway: PUT /api/v1/entities/:id
    Gateway->>Controller: Validate & Forward
    Controller->>Service: update(id, dto)
    Service->>Repository: findById(id)
    Repository->>Database: SELECT
    Database-->>Repository: current entity
    Service->>Service: Validate & Merge Changes
    Service->>Repository: update(entity)
    Repository->>Database: UPDATE
    Database-->>Repository: updated entity
    Service->>EventBus: publish(EntityUpdated)
    Service-->>Controller: Response DTO
    Controller-->>Gateway: 200 OK
    Gateway-->>Client: JSON Response

    Note over Client,EventBus: DELETE Flow
    Client->>Gateway: DELETE /api/v1/entities/:id
    Gateway->>Controller: Validate & Forward
    Controller->>Service: delete(id)
    Service->>Repository: softDelete(id)
    Repository->>Database: UPDATE deleted_at
    Database-->>Repository: confirmation
    Service->>EventBus: publish(EntityDeleted)
    Service-->>Controller: 204 No Content
    Controller-->>Gateway: 204
    Gateway-->>Client: No Content
```

---

## 4. CRUD Deployment Diagram

```mermaid
graph LR
    subgraph Edge
        CDN[CDN / WAF]
        LB[Load Balancer]
    end

    subgraph App Cluster
        API1[API Server 1]
        API2[API Server 2]
        API3[API Server N]
        Worker1[Worker 1]
        Worker2[Worker 2]
    end

    subgraph Data Cluster
        PG_Primary[(PostgreSQL Primary)]
        PG_Replica1[(PostgreSQL Replica 1)]
        PG_Replica2[(PostgreSQL Replica 2)]
        RedisCluster[Redis Cluster]
        S3Bucket[S3 Bucket]
    end

    subgraph Monitoring
        Prometheus[Prometheus]
        Grafana[Grafana]
        Jaeger[Jaeger Tracing]
    end

    CDN --> LB
    LB --> API1 & API2 & API3
    API1 & API2 & API3 --> PG_Primary
    API1 & API2 & API3 --> RedisCluster
    API1 & API2 & API3 --> S3Bucket
    PG_Primary --> PG_Replica1 & PG_Replica2
    Worker1 & Worker2 --> PG_Primary
    Worker1 & Worker2 --> RedisCluster
    API1 & API2 & API3 --> Prometheus
    Worker1 & Worker2 --> Prometheus
    Prometheus --> Grafana
    API1 & API2 & API3 --> Jaeger
```

---

## 5. CRUD Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Language | TypeScript | 5.x | Type-safe application code |
| Runtime | Node.js | 20 LTS | JavaScript runtime |
| Web Framework | Express.js | 4.x | HTTP routing & middleware |
| ORM | Prisma | 5.x | Database abstraction & migrations |
| Validation | Zod | 3.x | Schema validation at boundaries |
| Authentication | Passport.js | 0.7 | Multi-strategy auth |
| Authorization | CASL | 6.x | Permission-based access control |
| Caching | ioredis | 5.x | Redis client for cache layer |
| Queue | BullMQ | 5.x | Background job processing |
| Object Storage | AWS S3 SDK | 3.x | File & media storage |
| Logging | Pino | 8.x | Structured logging |
| Tracing | OpenTelemetry | 1.x | Distributed tracing |
| Testing | Vitest | 1.x | Unit & integration tests |
| Container | Docker | 24.x | Application containerization |
| Orchestration | Kubernetes | 1.28 | Container orchestration |
| CI/CD | GitHub Actions | - | Build, test, deploy pipeline |
| IaC | Terraform | 1.6 | Infrastructure provisioning |
| Monitoring | Prometheus + Grafana | - | Metrics & dashboards |
| Alerting | PagerDuty | - | Incident response |

### Database Schema Conventions

- All tables use UUID primary keys
- Timestamps: `created_at`, `updated_at`, `deleted_at` (soft delete)
- Audit fields: `created_by`, `updated_by`
- Indexes on all foreign keys and frequently queried columns
- Partitioning on audit/log tables by date range

### API Conventions

- RESTful endpoints under `/api/v1/`
- JSON request/response bodies
- Standard HTTP status codes
- Cursor-based pagination (`?cursor=&limit=`)
- Field filtering (`?fields=id,name,status`)
- Sorting (`?sort=-created_at`)
- Rate limiting per API key/user tier
