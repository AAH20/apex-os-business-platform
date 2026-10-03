# CRUD Contribution Guide

Welcome to the APEX-OS Business Platform CRUD contribution guide. This document defines the standards, workflows, and expectations for all CRUD (Create, Read, Update, Delete) contributions.

---

## 1. CRUD Code of Conduct

All contributors must adhere to the following principles:

- **Respect existing patterns**: Follow the established CRUD conventions already present in the codebase. Do not invent parallel patterns.
- **No destructive operations without safeguards**: Every Delete operation must include soft-delete support or explicit confirmation guards.
- **Data integrity first**: Never bypass validation layers. All CRUD operations must respect model-level and schema-level constraints.
- **Idempotency**: Create and Update operations should be idempotent where possible to prevent duplicate records.
- **Auditability**: All mutations must include appropriate logging or audit trail entries.
- **Scope discipline**: A single PR should address one CRUD resource or a tightly related group. Do not bundle unrelated entities.
- **Backward compatibility**: Changes to existing CRUD contracts must not break consumers without a documented migration path.

---

## 2. CRUD Development Setup

### Prerequisites

- Node.js 20+ and pnpm 9+
- Docker (for local database and cache services)
- Git 2.40+

### Initial Setup

```bash
git clone git@github.com:apex-os/business-platform.git
cd business-platform
pnpm install
docker compose up -d postgres redis
pnpm db:migrate
pnpm db:seed
pnpm dev
```

### Verifying Your Environment

```bash
# Run the full test suite
pnpm test

# Run CRUD-specific integration tests
pnpm test:crud

# Lint and type-check
pnpm lint
pnpm typecheck
```

All three commands must pass before you begin work on a CRUD feature.

### Project Structure

```
src/
  modules/
    <resource>/
      <resource>.controller.ts    # HTTP handlers
      <resource>.service.ts       # Business logic
      <resource>.repository.ts    # Data access layer
      <resource>.schema.ts        # Validation schemas
      <resource>.types.ts         # TypeScript interfaces
  shared/
    middleware/                    # Auth, validation, error handling
    utils/                         # Pagination, filtering helpers
```

---

## 3. CRUD Coding Standards

### Naming Conventions

| Layer | Convention | Example |
|-------|-----------|---------|
| Controller methods | `create<Resource>`, `get<Resource>`, `list<Resources>`, `update<Resource>`, `delete<Resource>` | `createInvoice`, `listInvoices` |
| Service methods | Same as controller, delegate to repository | `service.createInvoice(dto)` |
| Repository methods | `insert`, `findById`, `findAll`, `update`, `softDelete` | `repo.insert(data)` |
| Database tables | plural snake_case | `invoices`, `line_items` |
| DTOs | `<Action><Resource>Dto` | `CreateInvoiceDto`, `UpdateInvoiceDto` |

### Controller Standards

- Controllers must be thin: parse input, call service, return response.
- Use the shared validation middleware with Zod schemas from `<resource>.schema.ts`.
- Return consistent response envelopes:
  - Create: `201 Created` with the created resource
  - Read (single): `200 OK` with the resource
  - Read (list): `200 OK` with `{ data: [], meta: { page, limit, total } }`
  - Update: `200 OK` with the updated resource
  - Delete: `204 No Content`

### Service Standards

- Services contain business logic and orchestration only.
- Never import repository types into controllers.
- Use transactions for multi-step operations.
- Throw domain-specific errors; let the global error handler map them to HTTP status codes.

### Repository Standards

- Use the base repository class for common operations.
- Override only when custom queries are needed.
- Always use parameterized queries — never string interpolation.
- Soft-delete by default: set `deleted_at` instead of removing rows.

### Validation Standards

- Define Zod schemas in `<resource>.schema.ts`.
- Create and Update schemas should be separate (Update = partial of Create).
- Validate at the controller boundary, not inside services.
- Return `422 Unprocessable Entity` with field-level error details on validation failure.

### Error Handling

```typescript
// Use domain errors, not raw throws
throw new ResourceNotFoundError('Invoice', id);
throw new DuplicateResourceError('Invoice', 'number', value);
throw new ResourceConflictError('Cannot delete: resource has dependencies');
```

### Pagination and Filtering

- All list endpoints must support `page`, `limit`, `sort`, and `filter` query params.
- Default limit: 20. Max limit: 100.
- Use the shared `parsePagination()` and `parseFilter()` utilities.

---

## 4. CRUD Pull Request Process

### Before You Start

1. Check existing issues and PRs to avoid duplicate work.
2. Open or comment on an issue describing the CRUD resource you plan to implement.
3. Wait for maintainer acknowledgment before writing code.

### Branch Naming

```
feat/crud-<resource>          # New CRUD resource
fix/crud-<resource>-<issue>   # Bug fix in existing CRUD
refactor/crud-<resource>      # Refactoring existing CRUD
```

### Commit Convention

Follow Conventional Commits:

```
feat(crud): add Invoice CRUD endpoints
fix(crud): resolve soft-delete filter in list query
test(crud): add integration tests for Invoice update
```

### PR Requirements

- [ ] PR title follows `type(scope): description` format
- [ ] Description includes: what changed, why, and migration notes (if any)
- [ ] Screenshots or API response examples for new endpoints
- [ ] All existing tests pass
- [ ] New tests cover the added CRUD operations
- [ ] No lint or type errors
- [ ] Database migrations included (if schema changed)
- [ ] API documentation updated (OpenAPI spec or docs/ endpoint)

### Review Process

1. **Automated checks** must pass (CI: lint, typecheck, test, build).
2. **One maintainer approval** required for merge.
3. **Address review comments** by pushing additional commits to the same branch.
4. **Squash merge** is the default merge strategy — keep commits clean.

### Post-Merge

- The maintainer will tag a release.
- Breaking changes require a minor version bump and a changelog entry.

---

## 5. CRUD Testing Requirements

### Minimum Coverage

Every CRUD resource must have tests covering:

| Operation | Required Test Cases |
|-----------|-------------------|
| **Create** | Success, validation failure, duplicate detection, unauthorized access |
| **Read (single)** | Success, not found, unauthorized access |
| **Read (list)** | Success with pagination, empty result, filter/sort correctness |
| **Update** | Success, validation failure, not found, partial update, concurrent modification |
| **Delete** | Success, not found, dependency conflict, soft-delete verification |

### Test Structure

```typescript
describe('Invoice CRUD', () => {
  describe('createInvoice', () => {
    it('creates an invoice with valid data');
    it('rejects invalid data with 422');
    it('prevents duplicate invoice numbers');
  });

  describe('getInvoice', () => {
    it('returns an existing invoice');
    it('throws NotFound for missing invoice');
  });

  // ... list, update, delete
});
```

### Test Commands

```bash
# Run all CRUD tests
pnpm test:crud

# Run tests for a specific resource
pnpm test:crud -- --grep "Invoice"

# Run with coverage report
pnpm test:crud -- --coverage
```

### Coverage Thresholds

- **Lines**: 80% minimum for CRUD modules
- **Branches**: 75% minimum for CRUD modules
- **Functions**: 85% minimum for CRUD modules

### Integration Tests

- Use a real test database (via Docker), not mocks.
- Seed test data in `beforeAll`, clean up in `afterAll`.
- Test the full HTTP stack: route → middleware → controller → service → repository → DB.

### Test Data

- Use factory functions from `test/factories/<resource>.factory.ts`.
- Never hardcode IDs — always create resources and use their generated IDs.
- Use faker.js for realistic but randomized field values.

---

## Quick Reference

| Task | Command |
|------|---------|
| Install dependencies | `pnpm install` |
| Start dev server | `pnpm dev` |
| Run all tests | `pnpm test` |
| Run CRUD tests | `pnpm test:crud` |
| Lint | `pnpm lint` |
| Type check | `pnpm typecheck` |
| Run migrations | `pnpm db:migrate` |
| Seed database | `pnpm db:seed` |

---

Thank you for contributing to APEX-OS Business Platform. Quality CRUD operations are the backbone of our platform — your diligence makes the difference.
