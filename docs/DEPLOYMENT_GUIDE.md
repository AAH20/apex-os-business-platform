# APEX-OS Business Platform — Deployment Guide

## Docker Compose

```bash
cp .env.example .env          # fill in real values
docker compose up -d --build
```

Services: `frontend` (nginx, :3000→80), `backend` (uvicorn, :8000), `postgres` (:5432), `redis` (:6379), `nginx` (:80/:443). Named volumes persist `postgres_data` and `redis_data`.

## Kubernetes

```bash
kubectl create namespace apex-os
kubectl apply -f k8s/configmap.yaml -f k8s/secret.yaml
kubectl apply -f k8s/backend-deployment.yaml -f k8s/backend-service.yaml
kubectl apply -f k8s/frontend-deployment.yaml -f k8s/frontend-service.yaml
kubectl apply -f k8s/ingress.yaml -f k8s/hpa.yaml
```

Or via Helm: `helm install apex-os ./helm -n apex-os --create-namespace`

## Environment Variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `JWT_SECRET` | Token signing key |
| `SECRET_KEY` | App encryption key |
| `ENVIRONMENT` | `development` / `staging` / `production` |
| `DB_PASSWORD` | Postgres password (compose) |
| `REDIS_PASSWORD` | Redis password (compose) |

Store secrets in K8s Secrets or a vault — never commit them.

## Health Checks

- **Backend**: `GET /health` (port 8000) — used by Docker HEALTHCHECK and K8s liveness/readiness probes
- **Frontend**: `GET /healthz` (port 3000) — K8s liveness probe
- **Postgres**: `pg_isready -U apex -d apex_db`
- **Redis**: `redis-cli -a $REDIS_PASSWORD ping`

## Migrations (Alembic)

```bash
# Local
alembic upgrade head

# Docker
docker compose run --rm backend alembic upgrade head

# Kubernetes (one-shot job)
kubectl run alembic-migrate --rm -i --restart=Never \
  --image=apex-os-backend:latest -- alembic upgrade head
```

Migrations live in `migrations/versions/`. Run before deploying new app code.

## Backup & Restore

```bash
# PostgreSQL backup
pg_dump "$DATABASE_URL" | gzip > backup-$(date +%Y%m%d-%H%M%S).sql.gz

# Restore
gunzip -c backup-20240101.sql.gz | psql "$DATABASE_URL"

# Redis
redis-cli BGSAVE && cp /data/dump.rdb /backups/redis-$(date +%Y%m%d).rdb
```

Schedule daily backups via a K8s CronJob. Retain 30 days minimum; use WAL archiving for point-in-time recovery in production.
