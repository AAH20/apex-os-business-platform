# APEX-OS Business Platform — Complete Deployment Guide

## 1. Docker Compose Deployment

### Prerequisites
- Docker 24.0+ and Docker Compose v2+
- 4 vCPU, 8 GB RAM, 20 GB disk minimum

### Quick Start
```bash
git clone https://github.com/your-org/apex-os-business-platform.git
cd apex-os-business-platform
cp .env.example .env
# Edit .env with your secrets
docker compose up -d
```

### docker-compose.yml
```yaml
version: "3.9"
services:
  api:
    build: ./api
    ports: ["8080:8080"]
    environment:
      - DATABASE_URL=postgres://postgres:postgres@db:5432/apexos
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET=${JWT_SECRET}
    depends_on: [db, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  web:
    build: ./web
    ports: ["3000:3000"]
    environment:
      - API_URL=http://api:8080
    depends_on: [api]
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}
      POSTGRES_DB: apexos
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes: ["redisdata:/data"]
    restart: unless-stopped

  worker:
    build: ./worker
    environment:
      - DATABASE_URL=postgres://postgres:postgres@db:5432/apexos
      - REDIS_URL=redis://redis:6379
    depends_on: [db, redis]
    restart: unless-stopped

volumes:
  pgdata:
  redisdata:
```

### Production Hardening
```bash
docker swarm init && docker stack deploy -c docker-compose.yml apexos
# Or: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 2. Kubernetes Deployment

### Prerequisites
- kubectl 1.28+ and a running cluster (EKS/GKE/AKS/k3s)

### Namespace & Secrets
```bash
kubectl create namespace apexos
kubectl create secret generic apexos-secrets \
  --from-literal=jwt-secret=$(openssl rand -base64 32) \
  --from-literal=db-password=$(openssl rand -base64 24) -n apexos
```

### Deployment (k8s/deployment.yaml)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apexos-api
  namespace: apexos
spec:
  replicas: 3
  selector:
    matchLabels: { app: apexos-api }
  template:
    metadata:
      labels: { app: apexos-api }
    spec:
      containers:
        - name: api
          image: your-registry/apexos-api:latest
          ports: [{ containerPort: 8080 }]
          env:
            - name: DATABASE_URL
              valueFrom: { secretKeyRef: { name: apexos-secrets, key: db-url } }
            - name: JWT_SECRET
              valueFrom: { secretKeyRef: { name: apexos-secrets, key: jwt-secret } }
          resources:
            requests: { cpu: 250m, memory: 256Mi }
            limits: { cpu: "1", memory: 512Mi }
          livenessProbe:
            httpGet: { path: /health, port: 8080 }
            initialDelaySeconds: 15
          readinessProbe:
            httpGet: { path: /ready, port: 8080 }
            initialDelaySeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: apexos-api
  namespace: apexos
spec:
  selector: { app: apexos-api }
  ports: [{ port: 80, targetPort: 8080 }]
  type: ClusterIP
```

### Apply
```bash
kubectl apply -f k8s/
kubectl rollout status deployment/apexos-api -n apexos
```

### Ingress (nginx)
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: apexos-ingress
  namespace: apexos
  annotations: { cert-manager.io/cluster-issuer: letsencrypt-prod }
spec:
  tls:
    - hosts: [api.yourdomain.com]
      secretName: apexos-tls
  rules:
    - host: api.yourdomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend: { service: { name: apexos-api, port: { number: 80 } } }
```

---

## 3. Helm Chart Deployment

### Chart Structure
```
apexos/
  Chart.yaml
  values.yaml
  values-production.yaml
  templates/
    deployment.yaml
    service.yaml
    ingress.yaml
    hpa.yaml
    secret.yaml
```

### Chart.yaml
```yaml
apiVersion: v2
name: apexos
description: APEX-OS Business Platform
type: application
version: 1.0.0
appVersion: "2.0.0"
```

### values.yaml (key values)
```yaml
replicaCount: 3
image:
  repository: your-registry/apexos-api
  tag: latest
  pullPolicy: IfNotPresent
service:
  type: ClusterIP
  port: 80
ingress:
  enabled: true
  className: nginx
  hosts:
    - host: api.yourdomain.com
      paths: [{ path: /, pathType: Prefix }]
resources:
  requests: { cpu: 250m, memory: 256Mi }
  limits: { cpu: "1", memory: 512Mi }
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

### Install / Upgrade
```bash
helm repo add apexos https://charts.yourdomain.com
helm install apexos ./apexos -n apexos --create-namespace
helm upgrade apexos ./apexos -n apexos -f apexos/values-production.yaml
helm rollback apexos 1 -n apexos
```

---

## 4. Terraform Deployment

### main.tf (EKS example)
```hcl
terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {
    bucket = "apexos-tfstate"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" { region = "us-east-1" }

module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  cluster_name    = "apexos-prod"
  cluster_version = "1.28"
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets
  eks_managed_node_groups = {
    main = {
      min_size     = 2
      max_size     = 6
      desired_size = 3
      instance_types = ["m6i.large"]
    }
  }
}

resource "aws_db_instance" "postgres" {
  identifier        = "apexos-db"
  engine            = "postgres"
  engine_version    = "16"
  instance_class    = "db.t3.medium"
  allocated_storage = 50
  db_name           = "apexos"
  username          = "apexos_admin"
  password          = var.db_password
  multi_az          = true
  storage_encrypted = true
  skip_final_snapshot = false
  final_snapshot_identifier = "apexos-final"
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id      = "apexos-redis"
  engine          = "redis"
  node_type       = "cache.t3.micro"
  num_cache_nodes = 1
  port            = 6379
}

variable "db_password" { type = string, sensitive = true }
```

### Apply
```bash
terraform init
terraform plan -out=tfplan
terraform apply tfplan
terraform output -raw kubeconfig > ~/.kube/config
```

---

## 5. CI/CD Pipeline

### GitHub Actions (.github/workflows/deploy.yml)
```yaml
name: Build & Deploy
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
env:
  REGISTRY: ghcr.io
  IMAGE: ghcr.io/${{ github.repository }}
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm ci && npm test -- --coverage && npm run lint
  build:
    needs: test
    runs-on: ubuntu-latest
    permissions: { contents: read, packages: write }
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ env.IMAGE }}:${{ github.sha }}
            ${{ env.IMAGE }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - uses: azure/setup-kubectl@v3
      - run: |
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > kubeconfig
          export KUBECONFIG=kubeconfig
          kubectl set image deployment/apexos-api api=${{ env.IMAGE }}:${{ github.sha }} -n apexos
          kubectl rollout status deployment/apexos-api -n apexos
```

### GitLab CI (.gitlab-ci.yml)
```yaml
stages: [test, build, deploy]
test:
  stage: test
  image: node:20
  script: [npm ci, npm test]
build:
  stage: build
  image: docker:24
  services: [docker:24-dind]
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
deploy:
  stage: deploy
  image: bitnami/kubectl:latest
  only: [main]
  script:
    - kubectl set image deployment/apexos-api api=$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA -n apexos
    - kubectl rollout status deployment/apexos-api -n apexos
```

---

## 6. Monitoring Setup

### Prometheus + Grafana (kube-prometheus-stack)
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  --set grafana.adminPassword=$(openssl rand -base64 16)
```

### ServiceMonitor
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: apexos-metrics
  namespace: monitoring
spec:
  selector:
    matchLabels: { app: apexos-api }
  endpoints:
    - port: metrics
      interval: 15s
      path: /metrics
```

### Alerts (PrometheusRule)
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: apexos-alerts
  namespace: monitoring
spec:
  groups:
    - name: apexos
      rules:
        - alert: HighErrorRate
          expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
          for: 5m
          labels: { severity: critical }
          annotations:
            summary: "High 5xx error rate on APEX-OS"
        - alert: PodCrashLooping
          expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
          for: 5m
          labels: { severity: warning }
```

### Log Aggregation (Loki)
```bash
helm install loki grafana/loki-stack -n monitoring
# Promtail or Fluent Bit ships logs to Loki
```

### Dashboards
- Import Grafana dashboard ID 1860 (Node Exporter) and 11074 (Kubernetes)
- Custom APEX-OS dashboard JSON in `monitoring/dashboards/apexos.json`

---

## 7. Backup and DR Setup

### Database Backups (CronJob)
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: apexos-db-backup
  namespace: apexos
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: backup
              image: postgres:16-alpine
              command: [sh, -c, "pg_dump $DATABASE_URL | gzip > /backup/apexos-$(date +%F).sql.gz && aws s3 cp /backup/ s3://apexos-backups/ --recursive"]
              env:
                - name: DATABASE_URL
                  valueFrom: { secretKeyRef: { name: apexos-secrets, key: db-url } }
              volumeMounts:
                - { name: backup, mountPath: /backup }
          volumes:
            - name: backup
              emptyDir: {}
```

### Velero (Cluster Backup)
```bash
helm install velero vmware-tanzu/velero \
  --namespace velero --create-namespace \
  --set configuration.provider=aws \
  --set configuration.backupStorageLocation.bucket=apexos-velero-backups \
  --set credentials.useSecret=false
velero schedule create apexos-daily --schedule="0 3 * * *"
velero backup create apexos-manual --include-namespaces apexos
```

### DR Runbook
```bash
# 1. Restore database
gunzip -c apexos-2024-01-15.sql.gz | psql $DATABASE_URL
# 2. Restore cluster state
velero restore create --from-backup apexos-daily
# 3. Verify
kubectl get pods -n apexos && curl -f https://api.yourdomain.com/health
# 4. Update DNS if needed
aws route53 change-resource-record-sets --hosted-zone-id Z1234567890 --change-batch file://dns-failover.json
```

### RPO / RTO Targets
| Component | RPO | RTO |
|-----------|-----|-----|
| PostgreSQL | 1 hour | 30 min |
| Redis | 5 min | 10 min |
| Cluster state | 24 hours | 1 hour |
| Static assets | 24 hours | 15 min |

### Cross-Region Replication
```hcl
resource "aws_db_instance" "replica" {
  replicate_source_db = aws_db_instance.postgres.arn
  instance_class      = "db.t3.medium"
  availability_zone   = "us-west-2a"
}
```
