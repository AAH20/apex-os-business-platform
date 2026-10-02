# APEX-OS Business Platform — Developer Onboarding Guide

Welcome to the APEX-OS Business Platform team. This guide gets you from zero to your first merged contribution.

---

## 1. New Developer Onboarding

### First Day

1. **Access** — Request GitHub repo access from your team lead; accept the invite.
2. **Communication** — Join the team Slack/Discord channel and the daily standup.
3. **Accounts** — Get access to: GitHub org, CI dashboard, staging environment, and the observability stack (Grafana/Langfuse).
4. **Buddy** — You will be paired with an onboarding buddy for your first two weeks.

### First Week

- Read this guide end-to-end.
- Complete environment setup (Section 2).
- Review the architecture walkthrough (Section 4).
- Pick a `good-first-issue` label ticket from the board.
- Ship your first PR (Section 3).

### First Month

- Own a small feature or bug fix end-to-end.
- Participate in code review (giving and receiving).
- Shadow an on-call rotation if applicable.

---

## 2. Environment Setup

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Core runtime |
| Node.js | 20 LTS | Frontend tooling |
| Docker | 24+ | Local services |
| uv | latest | Python package manager |
| pnpm | latest | JS package manager |
| just | latest | Task runner (Make alternative) |
| gh | latest | GitHub CLI |

### Clone & Install

```bash
git clone git@github.com:your-org/apex-os-business-platform.git
cd apex-os-business-platform

# Python environment
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# JS dependencies
pnpm install

# Task runner
just --list          # see available commands
```

### Local Services

```bash
docker compose up -d   # Postgres, Redis, MinIO, etc.
just migrate           # run DB migrations
just seed              # optional: seed dev data
```

### Verify Setup

```bash
just test             # run full test suite
just lint             # ruff + mypy + eslint
just dev              # start dev servers
```

All three should pass before you start coding.

### Environment Variables

Copy `.env.example` to `.env` and fill in local values:

```bash
cp .env.example .env
```

Key variables: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `CORS_ORIGINS`.

---

## 3. First Contribution Guide

### Branch Naming

```
feat/<ticket-id>-short-description
fix/<ticket-id>-short-description
docs/<ticket-id>-short-description
```

### Workflow

1. **Pull latest main** — `git pull origin main`
2. **Create branch** — from `main`, not from another feature branch
3. **Write code** — follow the style guide (ruff for Python, biome for TS)
4. **Write tests** — every PR needs test coverage for new logic
5. **Run checks locally** — `just lint && just test`
6. **Commit** — conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`
7. **Push & open PR** — `gh pr create --fill`
8. **Address review** — respond to all comments before re-requesting review
9. **Merge** — squash merge once CI is green and you have 1 approval

### PR Checklist

- [ ] Tests pass locally and in CI
- [ ] Lint passes (ruff, mypy, eslint, prettier)
- [ ] New env vars documented in `.env.example`
- [ ] Migration included if schema changed
- [ ] CHANGELOG.md updated
- [ ] No secrets committed

### Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`.

---

## 4. Architecture Walkthrough

### High-Level Overview

APEX-OS is a modular business platform with a Python backend and React frontend.

```
┌─────────────────────────────────────────────────┐
│                   Client (React)                 │
├─────────────────────────────────────────────────┤
│              API Gateway (FastAPI)               │
├──────────┬──────────┬──────────┬────────────────┤
│  Auth    │  Billing │  CRM     │  Inventory     │
│ Service  │ Service  │ Service  │  Service       │
├──────────┴──────────┴──────────┴────────────────┤
│              Event Bus (Redis Streams)           │
├─────────────────────────────────────────────────┤
│  PostgreSQL  │  Redis  │  MinIO (S3) │  Worker   │
└─────────────────────────────────────────────────┘
```

### Backend (Python / FastAPI)

- **`src/apex/`** — core application code
  - `api/` — route handlers, request/response schemas
  - `services/` — business logic layer
  - `models/` — SQLAlchemy ORM models
  - `repositories/` — data access layer
  - `events/` — event producers/consumers
  - `workers/` — background task processors
- **`tests/`** — pytest suite, mirrors `src/` structure
- **`alembic/`** — database migrations

### Frontend (React / TypeScript)

- **`web/src/`** — React app
  - `pages/` — route-level components
  - `components/` — reusable UI components
  - `hooks/` — custom React hooks
  - `api/` — typed API client (generated from OpenAPI)
  - `stores/` — Zustand state stores

### Key Patterns

- **Repository Pattern** — all DB access goes through repository classes
- **Service Layer** — business logic lives in services, not routes
- **Event-Driven** — services emit events; workers consume asynchronously
- **Schema-First** — Pydantic models define API contracts; OpenAPI generated from them

### Data Flow

1. Request hits FastAPI route → validated by Pydantic schema
2. Route calls service method → business logic executed
3. Service uses repository → DB operations
4. Service emits event → published to Redis Stream
5. Worker picks up event → async processing (emails, reports, etc.)

---

## 5. Common Tasks Guide

### Add a New API Endpoint

1. Define Pydantic schema in `src/apex/api/schemas/`
2. Add route handler in `src/apex/api/routes/`
3. Implement service method in `src/apex/services/`
4. Add repository method in `src/apex/repositories/`
5. Write tests in `tests/api/routes/`
6. Regenerate OpenAPI client: `just generate-client`

### Add a Database Migration

```bash
just migrate-create "add column to table"
# edit the generated file in alembic/versions/
just migrate              # apply locally
```

Never edit existing migrations — always create new ones.

### Add a Background Worker

1. Define event schema in `src/apex/events/schemas/`
2. Create worker in `src/apex/workers/`
3. Register worker in `src/apex/workers/__init__.py`
4. Write tests in `tests/workers/`

### Debug a Failing Test

```bash
just test -- -k "test_name" -vv     # run single test with verbose output
just test -- --pdb                  # drop into debugger on failure
```

### Run Performance Benchmarks

```bash
just benchmark              # runs locust suite against local dev server
```

### Update Dependencies

```bash
# Python
uv lock --upgrade
uv pip install -e ".[dev]"

# JS
pnpm update
```

### Useful Commands Reference

| Command | Description |
|---------|-------------|
| `just dev` | Start all dev servers |
| `just test` | Run full test suite |
| `just test-watch` | Run tests in watch mode |
| `just lint` | Run all linters |
| `just format` | Auto-format all code |
| `just typecheck` | Run mypy + tsc |
| `just migrate` | Apply DB migrations |
| `just migrate-create "msg"` | Create new migration |
| `just seed` | Seed dev database |
| `just generate-client` | Regenerate TS API client |
| `just benchmark` | Run performance benchmarks |
| `just docker-up` | Start local services |
| `just docker-down` | Stop local services |

### Getting Help

- **Slack**: `#apex-dev` for general questions
- **Docs**: `/docs` directory in the repo
- **Architecture Decision Records**: `/docs/adr/`
- **Runbook**: `/docs/runbook/` for operational tasks
- **Escalation**: tag `@tech-lead` in PR or Slack for blockers

---

*Last updated: 2026-10-02. For corrections, open a PR against this file.*
