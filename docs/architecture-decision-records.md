# Architecture Decision Records

## ADR-001: Monorepo vs Multi-repo

**Status:** Accepted  
**Date:** 2026-10-02

### Context

APEX-OS Business Platform consists of multiple services (API gateway, auth, billing, notifications, analytics) that share common libraries (ORM models, event schemas, middleware). We need to decide whether to keep all code in a single repository or split into multiple repositories.

### Decision

Use a **monorepo** with a clear service boundary structure. All services, shared libraries, and infrastructure-as-code live in a single repository under `/services`, `/libs`, and `/infra` directories.

### Consequences

- **Positive:** Atomic cross-service changes in a single PR; shared library updates propagate immediately; unified CI/CD pipeline; simpler local development setup.
- **Negative:** Repository grows over time; requires disciplined access controls; build times can increase without proper caching; risk of tight coupling between services if boundaries are not enforced.
- **Mitigations:** Use path-based CODEOWNERS; implement Bazel or Nx for incremental builds; enforce service boundaries via linting rules.

---

## ADR-002: Python vs Go for Hot Path

**Status:** Accepted  
**Date:** 2026-10-02

### Context

The billing and analytics services handle high-throughput request paths (payment webhook processing, real-time metrics aggregation). We must choose the primary language for these performance-critical paths.

### Decision

Use **Go** for the hot-path services (billing, analytics ingestion). Use **Python** for the remaining services (auth, notifications, admin API) where developer velocity and ecosystem maturity matter more than raw throughput.

### Consequences

- **Positive:** Go delivers predictable low-latency performance and efficient memory usage for high-throughput paths; Python retains its strength in rapid iteration and rich library ecosystem for business logic.
- **Negative:** Two-language stack increases operational complexity (different build tooling, debugging, hiring); context switching for developers.
- **Mitigations:** Define clear gRPC contracts between services; maintain shared protobuf definitions; document service ownership.

---

## ADR-003: SQLAlchemy vs Raw SQL

**Status:** Accepted  
**Date:** 2026-10-02

### Context

The platform uses PostgreSQL as its primary datastore. We need to decide on the data access layer approach — ORM-based or raw SQL.

### Decision

Use **SQLAlchemy 2.0** (with its typed Core and ORM layers) as the primary data access layer. Use raw SQL only for complex analytical queries that cannot be expressed efficiently through the ORM.

### Consequences

- **Positive:** Type-safe query construction; migration integration via Alembic; reduced boilerplate for CRUD operations; easier to refactor schema.
- **Negative:** ORM overhead for complex queries; learning curve for SQLAlchemy 2.0's new patterns; potential for N+1 queries if not careful.
- **Mitigations:** Use `selectinload`/`joinedload` eagerly; enforce query review in code review; use `explain analyze` in CI for critical paths.

---

## ADR-004: FastAPI vs Django

**Status:** Accepted  
**Date:** 2026-10-02

### Context

The platform exposes REST and WebSocket APIs. We need a Python web framework that supports async I/O, automatic OpenAPI documentation, and integrates with our Go services.

### Decision

Use **FastAPI** for all Python-based API services. Do not use Django.

### Consequences

- **Positive:** Native async support; automatic OpenAPI/Swagger generation; Pydantic validation reduces bugs; lightweight and modular; easy to containerize.
- **Negative:** Smaller ecosystem than Django (no built-in admin panel, ORM, or auth); requires more manual wiring for common patterns.
- **Mitigations:** Build internal shared libraries for auth middleware, admin CRUD scaffolding, and common patterns; leverage Starlette ecosystem.

---

## ADR-005: AGPL-3.0 vs MIT

**Status:** Accepted  
**Date:** 2026-10-02

### Context

APEX-OS Business Platform is an open-source project. We must choose a license that balances community adoption with protection against cloud providers offering the platform as a service without contributing back.

### Decision

License the platform under **AGPL-3.0** (Affero General Public License v3.0).

### Consequences

- **Positive:** Network copyleft ensures that modifications and extensions offered as a service must be open-sourced; protects the community fork; compatible with GPL-3.0.
- **Negative:** Some enterprises avoid AGPL due to its strong copyleft terms; may limit adoption in proprietary environments; requires legal review for contributors.
- **Mitigations:** Provide a commercial licensing option for enterprises that cannot comply with AGPL; document contribution guidelines clearly.
