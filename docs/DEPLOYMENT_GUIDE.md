# APEX-OS Business Platform — Deployment Guide

## 1. Docker Deployment

### Dockerfile

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM node:20-alpine AS production
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package*.json ./
RUN addgroup -g 1001 -S nodejs && adduser -S apex -u 1001
USER apex
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1
CMD ["node", "dist/main.js"]
```

### docker-compose.yml

```yaml
version: "3.9"
services:
  app:
    build: { context: ., dockerfile: Dockerfile, target: production }
    ports: ["3000:3000"]
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgres://apex:${DB_PASSWORD}@db:5432/apex_os
      - REDIS_URL=redis://cache:6379
    depends_on:
      db: { condition: service_healthy }
      cache: { condition: service_started }
    restart: unless-stopped
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: apex_os
      POSTGRES_USER: apex
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U apex"]
      interval: 10s
      retries: 5
  cache:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes: [redisdata:/data]
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on: [app]
volumes:
  pgdata:
  redisdata:
```

```bash
docker build -t apex-os:latest .
docker-compose up -d
docker-compose up -d --scale app=3
```

---

## 2. Kubernetes Deployment

### Helm Chart Structure

```
charts/apex-os/
├── Chart.yaml
├── values.yaml
├── values-staging.yaml
├── values-production.yaml
└── templates/
    ├── _helpers.tpl
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    ├── configmap.yaml
    ├── secret.yaml
    ├── hpa.yaml
    └── pdb.yaml
```

### deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "apex-os.fullname" . }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels: { app: {{ include "apex-os.name" . }} }
  template:
    metadata:
      labels: { app: {{ include "apex-os.name" . }} }
    spec:
      containers:
        - name: apex-os
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          ports: [{ containerPort: 3000 }]
          envFrom:
            - configMapRef: { name: {{ include "apex-os.fullname" . }}-config }
            - secretRef: { name: {{ include "apex-os.fullname" . }}-secrets }
          resources: { { toYaml .Values.resources | nindent 12 } }
          livenessProbe:
            httpGet: { path: /health, port: 3000 }
            initialDelaySeconds: 10
          readinessProbe:
            httpGet: { path: /ready, port: 3000 }
            initialDelaySeconds: 5
```

### hpa.yaml

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "apex-os.fullname" . }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "apex-os.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
    - type: Resource
      resource: { name: memory, target: { type: Utilization, averageUtilization: 80 } }
```

```bash
helm install apex-os ./charts/apex-os -n apex-os --create-namespace
helm upgrade apex-os ./charts/apex-os -n apex-os -f values-production.yaml
helm rollback apex-os 1 -n apex-os
```

---

## 3. Cloud Deployment

### AWS (ECS Fargate)

```bash
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json
aws ecs update-service --cluster apex-os --service apex-os --task-definition apex-os:1
```

Task definition: Fargate, 0.5 vCPU / 1GB, container port 3000, env from Secrets Manager, logs to CloudWatch.

### Azure (Container Instances / AKS)

```bash
az container create --resource-group apex-os-rg --name apex-os \
  --image <registry>.azurecr.io/apex-os:latest --cpu 1 --memory 2 --ports 3000 \
  --environment-variables NODE_ENV=production

az aks get-credentials --resource-group apex-os-rg --name apex-os-cluster
helm install apex-os ./charts/apex-os -n apex-os
```

### GCP (Cloud Run)

```bash
gcloud run deploy apex-os --image gcr.io/<project>/apex-os:latest \
  --platform managed --region us-central1 --allow-unauthenticated \
  --set-env-vars NODE_ENV=production --memory 1Gi --cpu 1 \
  --concurrency 80 --max-instances 10
```

---

## 4. CI/CD Pipeline

### GitHub Actions (.github/workflows/deploy.yml)

```yaml
name: Build, Test & Deploy
on:
  push: { branches: [main, develop] }
  pull_request: { branches: [main] }
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm }
      - run: npm ci && npm run lint && npm run test -- --coverage && npm run build
  build:
    needs: test
    runs-on: ubuntu-latest
    permissions: { contents: read, packages: write }
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with: { registry: ${{ env.REGISTRY }}, username: ${{ github.actor }}, password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: type=sha,type=ref,event=branch
      - uses: docker/build-push-action@v5
        with: { context: ., push: true, tags: ${{ steps.meta.outputs.tags }}, cache-from: type=gha, cache-to: type=gha,mode=max }
  deploy-staging:
    needs: build
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - run: helm upgrade --install apex-os ./charts/apex-os -n apex-os-staging --set image.tag=${{ github.sha }} -f charts/apex-os/values-staging.yaml
  deploy-production:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - run: helm upgrade --install apex-os ./charts/apex-os -n apex-os-production --set image.tag=${{ github.sha }} -f charts/apex-os/values-production.yaml
```

### GitLab CI (.gitlab-ci.yml)

```yaml
stages: [test, build, deploy]
variables:
  DOCKER_IMAGE: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA
test:
  stage: test
  image: node:20-alpine
  script: [npm ci, npm run lint, npm run test -- --coverage, npm run build]
build:
  stage: build
  image: docker:24
  services: [docker:24-dind]
  script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker build -t $DOCKER_IMAGE . && docker push $DOCKER_IMAGE
deploy_staging:
  stage: deploy
  image: alpine/helm:3.14
  environment: { name: staging }
  script: [helm upgrade --install apex-os ./charts/apex-os -n apex-os-staging --set image.tag=$CI_COMMIT_SHORT_SHA -f charts/apex-os/values-staging.yaml]
  only: [develop]
deploy_production:
  stage: deploy
  image: alpine/helm:3.14
  environment: { name: production }
  script: [helm upgrade --install apex-os ./charts/apex-os -n apex-os-production --set image.tag=$CI_COMMIT_SHORT_SHA -f charts/apex-os/values-production.yaml]
  only: [main]
  when: manual
```

---

## 5. Environment Configuration

| Variable | Dev | Staging | Production |
|---|---|---|---|
| `NODE_ENV` | `development` | `staging` | `production` |
| `LOG_LEVEL` | `debug` | `info` | `warn` |
| `DATABASE_URL` | Local Docker | Staging cluster | Production cluster |
| `REDIS_URL` | Local Docker | Staging cluster | Production cluster |
| `JWT_SECRET` | Dev secret | Staging secret | Production secret |
| `CORS_ORIGIN` | `*` | `https://staging.apex-os.io` | `https://apex-os.io` |
| `RATE_LIMIT` | Disabled | 1000/min | 100/min |
| `REPLICA_COUNT` | 1 | 2 | 3+ |

```yaml
# ConfigMap
apiVersion: v1
kind: ConfigMap
metadata: { name: apex-os-config }
data:
  NODE_ENV: "production"
  LOG_LEVEL: "info"
  CORS_ORIGIN: "https://apex-os.io"
---
# Secret
apiVersion: v1
kind: Secret
metadata: { name: apex-os-secrets }
type: Opaque
stringData:
  DATABASE_URL: "postgres://..."
  JWT_SECRET: "<openssl rand -base64 32>"
```

```bash
cp .env.example .env                    # local
kubectl create configmap apex-os-config --from-env-file=.env.production
kubectl create secret generic apex-os-secrets --from-env-file=.env.production.secrets
```

---

## 6. Database Migration

```bash
# Create migration
db-migrate create add-users-table --sql-file

# Up / down
db-migrate up
db-migrate down

# Docker
docker-compose run --rm app npx db-migrate up

# Kubernetes (Helm pre-upgrade hook in templates/migration-job.yaml)
#   annotations:
#     "helm.sh/hook": pre-upgrade,pre-install
#     "helm.sh/hook-weight": "-5"
```

```sql
-- migrations/20240101000001_add-users-table.sql
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_users_email ON users(email);
```

**Best practices:** Test on staging copy first; use transactions; keep migrations idempotent; never modify applied migrations; run migrations before deploying new app code.

---

## 7. Backup and Restore

```bash
# PostgreSQL backup
pg_dump $DATABASE_URL | gzip > backup-$(date +%Y%m%d-%H%M%S).sql.gz
aws s3 cp backup-*.sql.gz s3://apex-os-backups/postgres/

# PostgreSQL restore
gunzip -c backup-20240101.sql.gz | psql $DATABASE_URL

# Redis backup
redis-cli BGSAVE && cp /var/lib/redis/dump.rdb /backups/redis-$(date +%Y%m%d).rdb
```

```yaml
# Kubernetes CronJob
apiVersion: batch/v1
kind: CronJob
metadata: { name: apex-os-backup }
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:16-alpine
              command: [/bin/sh, -c, 'pg_dump $DATABASE_URL | gzip > /backup/apex-os-$(date +%Y%m%d).sql.gz && aws s3 cp /backup/ s3://apex-os-backups/ --recursive']
              env:
                - name: DATABASE_URL
                  valueFrom: { secretKeyRef: { name: apex-os-secrets, key: DATABASE_URL } }
              volumeMounts: [{ name: backup-vol, mountPath: /backup }]
          volumes: [{ name: backup-vol, emptyDir: {} }]
          restartPolicy: OnFailure
```

| Environment | Frequency | Retention |
|---|---|---|
| Development | Weekly | 2 weeks |
| Staging | Daily | 4 weeks |
| Production | Daily + WAL | 30 days + 7 years (WAL) |

---

## 8. Scaling Strategy

```yaml
# HPA with custom metrics
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: apex-os }
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: apex-os }
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
    - type: Pods
      pods:
        metric: { name: http_requests_per_second }
        target: { type: AverageValue, averageValue: "1000" }
```

```yaml
# values-production.yaml
resources:
  requests: { memory: "512Mi", cpu: "250m" }
  limits: { memory: "2Gi", cpu: "1000m" }
database:
  primary: { instance: db.r6g.xlarge }
  replicas: { count: 2, instance: db.r6g.large }
redis:
  cluster: { enabled: true, slaveCount: 3 }
```

| Metric | Scale Up | Scale Down |
|---|---|---|
| CPU | > 70% for 2 min | < 30% for 5 min |
| Memory | > 80% for 2 min | < 40% for 5 min |
| p99 latency | > 500ms | < 100ms |

---

## 9. Load Balancing

```nginx
# nginx.conf
upstream apex_os {
    least_conn;
    server app:3000 weight=5;
    keepalive 32;
}
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    location / {
        proxy_pass http://apex_os;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```yaml
# Kubernetes Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: apex-os-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
    - hosts: [apex-os.io]
      secretName: apex-os-tls
  rules:
    - host: apex-os.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend: { service: { name: apex-os, port: { number: 3000 } } }
```

---

## 10. SSL/TLS Configuration

```yaml
# cert-manager ClusterIssuer
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata: { name: letsencrypt-prod }
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@apex-os.io
    privateKeySecretRef: { name: letsencrypt-prod }
    solvers:
      - http01: { ingress: { class: nginx } }
```

```nginx
# SSL hardening
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;
add_header Strict-Transport-Security "max-age=63072000" always;
```

```bash
# Verify certificate
openssl s_client -connect apex-os.io:443 -servername apex-os.io </dev/null 2>/dev/null | openssl x509 -noout -dates
# Force renewal
kubectl delete secret apex-os-tls -n apex-os
```

| Service | Certificate | Auto-Renew |
|---|---|---|
| AWS ACM | Managed | Yes |
| Azure Key Vault | Managed | Yes |
| Google Cloud SSL | Managed | Yes |
| Cloudflare | Universal | Yes |
| Let's Encrypt | cert-manager | Yes |

---

## Quick Reference

```bash
docker-compose up -d                                    # local dev
helm upgrade --install apex-os ./charts/apex-os -n apex-os-staging -f charts/apex-os/values-staging.yaml
helm upgrade --install apex-os ./charts/apex-os -n apex-os-production -f charts/apex-os/values-production.yaml
kubectl run db-migrate --rm -i --restart=Never --image=ghcr.io/apex-os/apex-os:latest -- npx db-migrate up
kubectl logs -f deployment/apex-os -n apex-os-production
kubectl scale deployment apex-os --replicas=5 -n apex-os-production
helm rollback apex-os 1 -n apex-os-production
```
