# APEX-OS Business Platform — Platform Overview

## Architecture

APEX-OS is a modular, event-driven business operations platform built on a layered architecture:

```
┌─────────────────────────────────────────────────────┐
│  Frontend (React + Vite + Tailwind)                 │
├─────────────────────────────────────────────────────┤
│  API Gateway (FastAPI, JWT, Rate Limiting)          │
├─────────────────────────────────────────────────────┤
│  Domain Modules (66 packages, 30+ core domains)     │
├─────────────────────────────────────────────────────┤
│  Infrastructure (Event Bus, CQRS, Saga, Cache)      │
├─────────────────────────────────────────────────────┤
│  Data Layer (SQLAlchemy, PostgreSQL, Redis)         │
└─────────────────────────────────────────────────────┘
```

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy 2.0, Pydantic, Alembic
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Recharts, React Router
- **Infrastructure**: Event bus, CQRS, Saga orchestration, distributed locks, message queue
- **Deployment**: Docker multi-stage builds, Kubernetes (Helm), Terraform, Nginx reverse proxy

## Core Modules (30)

| # | Module | Domain |
|---|--------|--------|
| 1 | Accounting | Invoices, journal entries, ledger |
| 2 | CRM | Contacts, leads, deals, opportunities |
| 3 | Analytics | Metrics, dashboards, KPI tracking |
| 4 | HR | Employees, roles, permissions |
| 5 | Inventory | Stock, products, suppliers |
| 6 | Supply Chain | Orders, logistics, fulfillment |
| 7 | Manufacturing | Production, BOM, work orders |
| 8 | IoT | Device telemetry, sensors |
| 9 | Reporting | Reports, exports, scheduled jobs |
| 10 | Compliance | Policies, audits, controls |
| 11 | Assets | Asset tracking, depreciation |
| 12 | Budgeting | Budgets, forecasts, variance |
| 13 | Project Mgmt | Projects, tasks, milestones |
| 14 | Billing | Payments, subscriptions, invoicing |
| 15 | Ecommerce | Storefront, cart, checkout |
| 16 | Marketing | Campaigns, leads, automation |
| 17 | Support | Tickets, SLA, knowledge base |
| 18 | Documents | File storage, versioning |
| 19 | Notifications | Email, SMS, push, in-app |
| 20 | Security | Auth, RBAC, audit logs, vault |
| 21 | Integration | API gateway, webhooks, connectors |
| 22 | Workflow | Process automation, approvals |
| 23 | Data Warehouse | ETL, OLAP, data modeling |
| 24 | Big Data | Batch/stream processing |
| 25 | Data Science | ML models, experiments |
| 26 | Continuous BI | Real-time dashboards |
| 27 | AI/ML | NLP, predictions, recommendations |
| 28 | Blockchain | Smart contracts, provenance |
| 29 | Disaster Recovery | Backup, restore, replication |
| 30 | Monitoring | Metrics, tracing, alerting |

Additional infrastructure modules: `cache`, `search`, `gamification`, `feature_flags`, `event_sourcing`, `cqrs`, `saga`, `message_queue`, `distributed_lock`, `multitenancy`, `ab_testing`, `agent_reach`, `vision`, `speech`, `nlp`, `ml`, `bi`, `cost_management`, `capacity_planning`, `data_exchange`, `file_storage`, `logging`, `tracing`, `audit`, `backup`, `knowledge`, `personalization`, `recommendations`, `tasks`, `contracts`, `alerting`, `integration_hub`, `database`, `core`, `api`.

## API Summary

- **Framework**: FastAPI with automatic OpenAPI docs (`/docs`, `/redoc`)
- **Auth**: JWT-based with RBAC, middleware for rate limiting
- **Route files**: 47 route modules in `web/backend/routes/`
- **Key endpoints**:
  - `GET /health` — health check
  - `/api/v1/accounting/invoices` — invoice CRUD
  - `/api/v1/crm/contacts` — contact management
  - `/api/v1/crm/deals` — deal pipeline
  - `/api/v1/analytics/metrics` — KPI metrics
  - `/api/v1/hr/employees` — employee records
  - `/api/v1/inventory/products` — product catalog
  - `/api/v1/supply-chain/orders` — order management
  - `/api/v1/manufacturing/work-orders` — production orders
  - `/api/v1/iot/devices` — device management
  - `/api/v1/reporting/reports` — report generation
  - `/api/v1/workflow/processes` — workflow automation
- **Patterns**: CQRS, event sourcing, saga orchestration, distributed locking

## Frontend Summary

- **Framework**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS with custom design system
- **Charts**: Recharts for data visualization
- **Routing**: React Router v6 with 87 page components
- **State**: React hooks + context API
- **Key pages**: Dashboard, Accounting, CRM, HR, Inventory, Supply Chain, Manufacturing, IoT, Analytics, Reporting, Projects, Billing, Marketing, Support, Settings
- **API client**: Centralized in `web/frontend/src/api/`
- **Build**: `npm run build` → static assets served by Nginx

## Deployment Guide

### Docker Compose (Quick Start)

```bash
cp .env.example .env
# Edit .env with your secrets
docker-compose up -d
```

Services: frontend (port 3000), backend (port 8000), PostgreSQL (5432), Redis (6379), Nginx (80/443).

### Kubernetes (Production)

```bash
# Using Helm
helm install apex-os ./helm/apex-os \
  --set secrets.dbPassword=... \
  --set secrets.jwtSecret=...

# Or using kubectl with manifests in k8s/
kubectl apply -f k8s/
```

### Terraform (Infrastructure)

```bash
cd terraform/
terraform init
terraform plan
terraform apply
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `SECRET_KEY` | JWT signing secret |
| `ADMIN_PASSWORD` | Initial admin password |
| `ENVIRONMENT` | `development` or `production` |

### Health Checks

- Backend: `GET /health` → `{"status": "healthy", "version": "0.1.0"}`
- Docker: `curl -f http://localhost:8000/health`
- K8s: liveness and readiness probes configured in Helm charts

### Migrations

```bash
alembic upgrade head
```

See `docs/DEPLOYMENT_GUIDE.md` for detailed instructions.
