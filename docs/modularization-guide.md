# APEX-OS Modularization Guide

## 1. Modularization Principles

### 1.1 Single Responsibility
Each module owns exactly one bounded context. A module should have one—and only one—reason to change. If a module serves two masters, split it.

### 1.2 High Cohesion, Low Coupling
- **Cohesion**: Elements within a module belong together by domain, not by coincidence.
- **Coupling**: Modules interact through stable interfaces, never through internal implementation details.

### 1.3 Information Hiding
Expose only what is necessary. Internal data structures, helper functions, and implementation choices are private to the module. Consumers depend on the contract, not the implementation.

### 1.4 Explicit Dependencies
All dependencies are declared in the module manifest. No hidden imports, no ambient globals, no side-effect-driven wiring.

### 1.5 Domain-Driven Boundaries
Modules align with business domains (e.g., `billing`, `inventory`, `auth`). Cross-domain communication flows through the event bus or explicit API calls—never through direct database access.

### 1.6 Reversibility
Every architectural decision should be cheap to reverse. Avoid frameworks or patterns that lock the module into a specific runtime, database, or transport.

---

## 2. Module Design Patterns

### 2.1 Standard Module Structure
```
modules/<module-name>/
├── manifest.json          # Module metadata, dependencies, exports
├── index.ts               # Public API surface (barrel file)
├── domain/                # Business logic, entities, value objects
│   ├── entities/
│   ├── value-objects/
│   └── domain-events/
├── application/           # Use cases, command/query handlers
│   ├── commands/
│   ├── queries/
│   └── services/
├── infrastructure/        # Adapters: DB, HTTP, MQ, cache
│   ├── persistence/
│   ├── messaging/
│   └── external-apis/
├── interfaces/            # Controllers, presenters, DTOs
│   ├── http/
│   ├── events/
│   └── cli/
├── tests/                 # Module-scoped tests
│   ├── unit/
│   ├── integration/
│   └── contracts/
└── README.md              # Module-specific documentation
```

### 2.2 Layered Architecture (Inside Each Module)
```
┌─────────────────────────┐
│  Interfaces (HTTP/CLI)  │  ← Transport layer
├─────────────────────────┤
│  Application Services   │  ← Use cases, orchestration
├─────────────────────────┤
│  Domain                 │  ← Business rules, invariants
├─────────────────────────┤
│  Infrastructure         │  ← I/O, persistence, external calls
└─────────────────────────┘
```
Dependencies point **inward**. Domain has zero outward dependencies.

### 2.3 Event-Driven Pattern
For cross-module communication:
- Modules publish **domain events** to the event bus.
- Modules subscribe to events they care about.
- Events are immutable, versioned, and carry a `traceId` for correlation.
- No synchronous cross-module calls for write operations.

### 2.4 Adapter Pattern
Infrastructure concerns are isolated behind adapters:
- `PersistenceAdapter` — database access
- `MessagingAdapter` — event bus / queue
- `ExternalApiAdapter` — third-party HTTP/gRPC calls
- `CacheAdapter` — caching layer

Swapping PostgreSQL for MySQL requires changing only the adapter, not the domain.

### 2.5 Facade Pattern
Complex subsystems expose a simplified facade to other modules. The facade is the only public entry point; internal services remain private.

### 2.6 Plugin Pattern
Optional capabilities (e.g., reporting, analytics) are loaded as plugins at runtime. Plugins register via the module registry and declare their dependencies.

---

## 3. Interface Contracts

### 3.1 Manifest Contract (`manifest.json`)
```json
{
  "name": "billing",
  "version": "1.4.2",
  "description": "Billing and invoicing module",
  "dependencies": {
    "shared-kernel": "^2.0.0",
    "auth": ">=1.0.0 <3.0.0"
  },
  "optionalDependencies": {
    "notifications": "^1.2.0"
  },
  "exports": {
    "commands": ["CreateInvoice", "ProcessRefund"],
    "queries": ["GetInvoice", "ListInvoices"],
    "events": ["InvoiceCreated", "InvoicePaid", "RefundProcessed"],
    "services": ["BillingService"]
  },
  "consumes": {
    "events": ["UserRegistered", "SubscriptionChanged"]
  },
  "provides": {
    "http": ["/api/v1/invoices"],
    "grpc": ["billing.v1.BillingService"]
  }
}
```

### 3.2 Command Contract
Commands are imperative, named in the tense of intent, and carry all required data:
```typescript
interface Command<T> {
  readonly type: string;           // Fully qualified: "billing.CreateInvoice"
  readonly payload: T;
  readonly metadata: {
    traceId: string;
    userId: string;
    timestamp: string;             // ISO 8601
    idempotencyKey: string;
  };
}
```

### 3.3 Query Contract
Queries are read-only, side-effect free, and return DTOs (never domain entities):
```typescript
interface Query<T> {
  readonly type: string;           // "billing.GetInvoice"
  readonly payload: T;
  readonly metadata: { traceId: string };
}

interface QueryResult<T> {
  data: T;
  meta?: { totalCount: number; page: number };
}
```

### 3.4 Event Contract
Events are named in past tense, immutable, and versioned:
```typescript
interface DomainEvent<T> {
  readonly type: string;           // "billing.InvoiceCreated"
  readonly version: number;        // Schema version
  readonly payload: T;
  readonly metadata: {
    traceId: string;
    aggregateId: string;
    occurredOn: string;
    correlationId: string;
    causationId: string;
  };
}
```

### 3.5 HTTP API Contract
- RESTful resources under `/api/v<major>/`
- OpenAPI 3.1 spec auto-generated from DTOs
- Standard error envelope: `{ error: { code, message, details } }`
- Idempotency-Key header required for all mutating endpoints

### 3.6 gRPC Contract
- Protobuf definitions live in `proto/<module>/<version>/`
- Services are versioned: `billing.v1.BillingService`
- Breaking changes require a new version; old versions deprecated, not removed

### 3.7 Versioning Policy
- **Major**: Breaking changes (removed fields, changed semantics)
- **Minor**: Backward-compatible additions (new optional fields, new endpoints)
- **Patch**: Bug fixes, documentation updates
- Semantic versioning enforced via CI checks

---

## 4. Dependency Management

### 4.1 Dependency Declaration
- All dependencies declared in `manifest.json`
- Version ranges use caret (`^`) for minor flexibility, exact for critical deps
- No circular dependencies allowed (enforced by CI)

### 4.2 Dependency Graph
```
shared-kernel (no deps)
    ↑
auth → shared-kernel
    ↑
billing → auth, shared-kernel
    ↑
notifications → billing, shared-kernel
```
The graph is a DAG. Cycles are a build-time error.

### 4.3 Shared Kernel
- `shared-kernel` contains cross-cutting primitives: `Entity`, `ValueObject`, `DomainEvent`, `Result`, `Id`
- Shared kernel changes require approval from all module owners
- Shared kernel is versioned independently

### 4.4 Dependency Injection
- Constructor injection only (no property injection, no service locator)
- DI container configured at composition root
- Module registrations are explicit, not auto-discovered

### 4.5 External Dependencies
- Third-party libraries pinned to exact versions in `package.lock`
- Vulnerability scanning in CI (Snyk / Dependabot)
- License compliance check (no GPL in proprietary modules)

### 4.6 Dependency Isolation
- Each module has its own `node_modules` (or equivalent)
- No hoisting of module-specific deps to root
- Module builds are independent and cacheable

---

## 5. Testing Strategy Per Module

### 5.1 Test Pyramid (Per Module)
```
         ┌──────────┐
         │   E2E    │  ← 5%  (critical paths only)
        ┌┴──────────┴┐
        │ Integration │  ← 15% (DB, MQ, external APIs)
       ┌┴─────────────┴┐
       │    Contract    │  ← 10% (consumer-driven)
      ┌┴───────────────┴┐
      │      Unit        │  ← 70% (domain logic)
      └──────────────────┘
```

### 5.2 Unit Tests
- Test domain entities, value objects, and application services
- No I/O, no network, no database
- Fast (< 100ms per test), deterministic, isolated
- Coverage target: ≥ 80% line, ≥ 70% branch on domain layer

### 5.3 Integration Tests
- Test infrastructure adapters against real (containerized) dependencies
- Use Testcontainers for PostgreSQL, Redis, Kafka
- Verify event publishing/consuming round-trips
- Run in CI on every PR

### 5.4 Contract Tests
- Consumer-driven contracts (Pact or similar)
- Provider verifies it satisfies all consumer contracts
- Breaking changes detected before merge
- Contracts stored in `tests/contracts/`

### 5.5 Event Tests
- Verify events are published with correct payload and metadata
- Verify event handlers process events idempotently
- Test event schema compatibility (forward and backward)

### 5.6 E2E Tests
- Critical user journeys only (e.g., "create order → payment → fulfillment")
- Run against staging environment
- Scheduled nightly, not on every PR

### 5.7 Test Data
- Factories for test data generation (no shared fixtures)
- Each test creates and tears down its own data
- No test depends on another test's state

### 5.8 CI Pipeline
```
Lint → Type Check → Unit Tests → Contract Tests → Integration Tests → Build
```
- Unit tests: every PR
- Contract tests: every PR
- Integration tests: every PR (parallelized)
- E2E: nightly + pre-release

---

## 6. Deployment Per Module

### 6.1 Build Artifacts
- Each module builds independently into a deployable artifact
- Artifacts are immutable and tagged with git SHA
- Multi-stage Docker builds; final image contains only runtime deps

### 6.2 Deployment Topology
```
┌─────────────────────────────────────────────┐
│                  API Gateway                │
├──────┬──────┬──────┬──────┬────────────────┤
│ auth │billing│inventory│notifications│ ... │
│ (3)  │ (2)  │  (2)   │   (2)      │     │
└──────┴──────┴──────┴──────┴────────────────┘
```
- Each module is a separate deployable unit
- Horizontal scaling per module based on load
- Modules communicate via service mesh or event bus

### 6.3 Database Per Module
- Each module owns its database/schema
- No cross-module joins; data consistency via events
- Schema migrations are module-scoped (Flyway / Alembic)
- Backward-compatible migrations required (expand-contract pattern)

### 6.4 Configuration
- Environment-specific config via environment variables
- Secrets via vault (HashiCorp Vault / AWS Secrets Manager)
- No config files baked into images
- Config changes trigger rolling restart, not redeployment

### 6.5 Deployment Strategy
- **Blue-Green**: Zero-downtime, instant rollback
- **Canary**: 5% → 25% → 50% → 100% traffic shift
- **Feature flags**: Decouple deployment from release
- Database migrations run before app deployment

### 6.6 Observability Per Module
- **Metrics**: Prometheus endpoints per module (`/metrics`)
- **Logs**: Structured JSON, correlated by `traceId`
- **Traces**: OpenTelemetry, sampled at 10% (100% for errors)
- **Health**: `/health` (liveness), `/ready` (readiness)
- **Alerts**: SLO-based (error rate, latency, saturation)

### 6.7 Rollback
- Rollback = redeploy previous artifact (no data migration rollback)
- Data migrations must be backward-compatible
- Feature flags allow instant feature disable without rollback

### 6.8 Multi-Environment
```
dev → staging → production
```
- Dev: ephemeral environments per PR
- Staging: mirrors production, runs E2E suite
- Production: canary deployments, manual approval gate

---

## Appendix: Module Checklist

Before a module is considered production-ready:

- [ ] `manifest.json` with all dependencies and exports
- [ ] Public API surface documented in `README.md`
- [ ] Unit test coverage ≥ 80% on domain layer
- [ ] Contract tests passing against all consumers
- [ ] Integration tests passing with real dependencies
- [ ] OpenAPI / Protobuf specs generated and committed
- [ ] Observability: metrics, logs, traces, health checks
- [ ] Deployment pipeline: build → test → deploy
- [ ] Runbook: common failures and remediation steps
- [ ] SLOs defined and alerts configured
