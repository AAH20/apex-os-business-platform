# APEX-OS Business Platform — Deployment Guide

## 1. Docker Compose

### Prerequisites
- Docker 24+
- Docker Compose v2

### Quick Start
```bash
cp .env.example .env
docker compose up -d
```

### docker-compose.yml
```yaml
version: "3.9"
services:
  api:
    build: ./api
    ports: ["8080:8080"]
    env_file: .env
    depends_on: [db, redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
  web:
    build: ./web
    ports: ["3000:3000"]
    depends_on: [api]
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: apexos
      POSTGRES_USER: apexos
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes: ["pgdata:/var/lib/postgresql/data"]
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
volumes:
  pgdata:
```

### Commands
```bash
docker compose up -d --build
docker compose logs -f
docker compose down -v
```

---

## 2. Kubernetes

### Prerequisites
- kubectl 1.28+
- A running cluster

### Namespace & Secrets
```bash
kubectl create namespace apexos
kubectl create secret generic apexos-secrets \
  --from-literal=DB_PASSWORD=... \
  --from-literal=REDIS_PASSWORD=... \
  -n apexos
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
          image: ghcr.io/yourorg/apexos-api:latest
          ports: [{ containerPort: 8080 }]
          envFrom:
            - secretRef: { name: apexos-secrets }
          resources:
            requests: { cpu: 250m, memory: 256Mi }
            limits: { cpu: 500m, memory: 512Mi }
          livenessProbe:
            httpGet: { path: /health, port: 8080 }
            initialDelaySeconds: 15
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
kubectl get pods -n apexos
```

---

## 3. Helm Chart

### Prerequisites
- Helm 3.12+

### Chart Structure
```
charts/apexos/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    └── secret.yaml
```

### values.yaml
```yaml
replicaCount: 3
image:
  repository: ghcr.io/yourorg/apexos-api
  tag: latest
service:
  type: ClusterIP
  port: 80
ingress:
  enabled: true
  host: apexos.example.com
secrets:
  dbPassword: ""
  redisPassword: ""
```

### Install / Upgrade
```bash
helm install apexos ./charts/apexos -n apexos --create-namespace
helm upgrade apexos ./charts/apexos -n apexos -f values-prod.yaml
helm rollback apexos 1 -n apexos
```

---

## 4. Terraform

### Prerequisites
- Terraform 1.6+
- AWS CLI configured

### main.tf
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
  cluster_version = "1.29"
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets
}

resource "aws_db_instance" "postgres" {
  identifier     = "apexos-db"
  engine         = "postgres"
  instance_class = "db.t3.micro"
  username       = "apexos"
  password       = var.db_password
  allocated_storage = 20
}
```

### Commands
```bash
terraform init
terraform plan -out=tfplan
terraform apply tfplan
terraform destroy
```

---

## 5. CI/CD Pipeline

### GitHub Actions (.github/workflows/deploy.yml)
```yaml
name: Deploy
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with: { go-version: "1.22" }
      - run: go test ./... -race
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm ci && npm test

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/setup-kubectl@v3
      - run: |
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > kubeconfig
          export KUBECONFIG=kubeconfig
          kubectl set image deployment/apexos-api api=ghcr.io/${{ github.repository }}:${{ github.sha }} -n apexos
          kubectl rollout status deployment/apexos-api -n apexos
```

### GitLab CI (.gitlab-ci.yml)
```yaml
stages: [test, build, deploy]

test:
  stage: test
  image: golang:1.22
  script: go test ./... -race

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

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DB_PASSWORD` | PostgreSQL password | Yes |
| `REDIS_PASSWORD` | Redis password | Yes |
| `JWT_SECRET` | JWT signing key | Yes |
| `API_PORT` | API listen port | No (default 8080) |
