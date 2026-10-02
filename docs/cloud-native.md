# APEX-OS Business Platform — Cloud-Native Deployment Guide

> **Version:** 1.0.0  
> **Last Updated:** 2026-10-01  
> **Scope:** Kubernetes, Helm, GitOps, Service Mesh, Monitoring

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Kubernetes Deployment](#3-kubernetes-deployment)
4. [Helm Charts](#4-helm-charts)
5. [GitOps with ArgoCD](#5-gitops-with-argocd)
6. [Service Mesh (Istio)](#6-service-mesh-istio)
7. [Monitoring & Observability](#7-monitoring--observability)
8. [Security Hardening](#8-security-hardening)
9. [Multi-Cloud Reference](#9-multi-cloud-reference)
10. [Runbooks & Troubleshooting](#10-runbooks--troubleshooting)

---

## 1. Architecture Overview

APEX-OS Business Platform is a cloud-native, multi-tier application deployed across Kubernetes clusters on AWS (EKS), Azure (AKS), and GCP (GKE). The platform follows a **GitOps-driven, infrastructure-as-code** methodology with Terraform provisioning the underlying cloud resources and Helm managing the Kubernetes workloads.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GitOps Control Plane                        │
│                    (ArgoCD / Flux CD)                               │
│         ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│         │  App     │  │  Infra   │  │  Config  │                  │
│         │  Repo    │  │  Repo    │  │  Repo    │                  │
│         └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└──────────────┼──────────────┼──────────────┼───────────────────────┘
               │              │              │
    ┌──────────▼──────────────▼──────────────▼──────────┐
    │              Kubernetes Clusters                   │
    │  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
    │  │ AWS EKS │  │Azure AKS│  │ GCP GKE │            │
    │  └────┬────┘  └────┬────┘  └────┬────┘            │
    │       │            │            │                  │
    │  ┌────▼────────────▼────────────▼────┐            │
    │  │        Service Mesh (Istio)        │            │
    │  └────┬────────────┬────────────┬────┘            │
    │       │            │            │                  │
    │  ┌────▼───┐  ┌─────▼──┐  ┌─────▼────┐            │
    │  │  API   │  │  Web   │  │  Worker  │            │
    │  │ (2-10) │  │  (2-6) │  │  (1-5)   │            │
    │  └────┬───┘  └────┬───┘  └────┬─────┘            │
    │       │           │           │                   │
    │  ┌────▼───────────▼───────────▼────┐             │
    │  │     PostgreSQL  +  Redis         │             │
    │  └──────────────────────────────────┘             │
    │  ┌──────────────────────────────────┐             │
    │  │  Monitoring (Prom/Grafana/Loki)  │             │
    │  └──────────────────────────────────┘             │
    └───────────────────────────────────────────────────┘
```

### Cloud Components (24 total)

| # | Component | Layer | Technology |
|---|-----------|-------|------------|
| 1 | API Service | Application | Node.js / Container |
| 2 | Web Frontend | Application | Nginx / Container |
| 3 | Background Worker | Application | Node.js / Container |
| 4 | PostgreSQL | Data | Bitnami PostgreSQL (Helm) |
| 5 | Redis | Data | Bitnami Redis (Helm) |
| 6 | Ingress Controller | Networking | NGINX Ingress |
| 7 | Network Policies | Security | K8s NetworkPolicy |
| 8 | Pod Disruption Budgets | Reliability | K8s PDB |
| 9 | Service Mesh | Networking | Istio |
| 10 | AWS VPC | Network | Terraform |
| 11 | AWS EKS | Compute | Terraform + EKS |
| 12 | AWS RDS | Data | Terraform + RDS |
| 13 | AWS S3 | Storage | Terraform + S3 |
| 14 | AWS IAM | Security | Terraform + IAM |
| 15 | Azure VNet | Network | Terraform |
| 16 | Azure AKS | Compute | Terraform + AKS |
| 17 | Azure Storage | Storage | Terraform |
| 18 | GCP VPC | Network | Terraform |
| 19 | GCP GKE | Compute | Terraform + GKE |
| 20 | GCP Storage | Storage | Terraform |
| 21 | K8s Namespaces | Organization | Terraform |
| 22 | Prometheus | Monitoring | Helm / Prometheus Operator |
| 23 | Grafana | Monitoring | Helm |
| 24 | Alertmanager | Monitoring | Helm |

---

## 2. Prerequisites

### 2.1 Required Tools

```bash
# Kubernetes CLI
kubectl version --client  # >= 1.28

# Helm
helm version  # >= 3.12

# Terraform
terraform version  # >= 1.5.0

# ArgoCD CLI (for GitOps)
argocd version  # >= 2.9

# Cloud CLIs
aws --version       # AWS CLI v2
az --version        # Azure CLI
gcloud --version    # Google Cloud SDK

# Mesh CLI
istioctl version    # >= 1.20
```

### 2.2 Cluster Bootstrap

Each cloud provider requires a running Kubernetes cluster. The Terraform modules in `terraform/` provision these:

```bash
# AWS EKS
cd terraform/
terraform init
terraform workspace new prod
terraform apply -var="environment=prod" -var="aws_region=us-east-1"

# Azure AKS
terraform apply -var="environment=prod" -var="azure_location=East US"

# GCP GKE
terraform apply -var="environment=prod" -var="gcp_project_id=my-project"
```

### 2.3 Namespace & RBAC Setup

```bash
# Create core namespaces
kubectl create namespace apex-os-core
kubectl create namespace apex-os-data
kubectl create namespace apex-os-monitoring
kubectl create namespace apex-os-security

# Label namespaces for Istio injection (if service mesh enabled)
kubectl label namespace apex-os-core istio-injection=enabled
kubectl label namespace apex-os-data istio-injection=enabled
```

---

## 3. Kubernetes Deployment

### 3.1 Raw Manifest Deployment (Without Helm)

For environments where Helm is not available, deploy components directly:

```yaml
# apex-os-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: apex-os-core
  labels:
    istio-injection: enabled
    app.kubernetes.io/part-of: apex-os-business-platform
---
# apex-os-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: apex-os-config
  namespace: apex-os-core
data:
  NODE_ENV: "production"
  LOG_LEVEL: "info"
  DB_HOST: "apex-os-postgres.apex-os-data.svc.cluster.local"
  DB_PORT: "5432"
  DB_NAME: "apexos"
  REDIS_HOST: "apex-os-redis.apex-os-data.svc.cluster.local"
  REDIS_PORT: "6379"
---
# apex-os-api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apex-os-api
  namespace: apex-os-core
  labels:
    app.kubernetes.io/name: apex-os-api
    app.kubernetes.io/component: api
    app.kubernetes.io/part-of: apex-os-business-platform
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: apex-os-api
  template:
    metadata:
      labels:
        app.kubernetes.io/name: apex-os-api
        app.kubernetes.io/component: api
    spec:
      serviceAccountName: apex-os-api
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: api
          image: apex-os/api:1.0.0
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8080
              protocol: TCP
          envFrom:
            - configMapRef:
                name: apex-os-config
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: apex-os-db-credentials
                  key: password
            - name: REDIS_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: apex-os-redis-credentials
                  key: password
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 5
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
---
# apex-os-api-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: apex-os-api
  namespace: apex-os-core
  labels:
    app.kubernetes.io/name: apex-os-api
spec:
  type: ClusterIP
  ports:
    - port: 8080
      targetPort: 8080
      protocol: TCP
      name: http
  selector:
    app.kubernetes.io/name: apex-os-api
---
# apex-os-api-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: apex-os-api
  namespace: apex-os-core
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: apex-os-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
---
# apex-os-api-pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: apex-os-api
  namespace: apex-os-core
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: apex-os-api
```

Apply all manifests:

```bash
kubectl apply -f apex-os-namespace.yaml
kubectl apply -f apex-os-configmap.yaml
kubectl apply -f apex-os-api-deployment.yaml
kubectl apply -f apex-os-api-service.yaml
kubectl apply -f apex-os-api-hpa.yaml
kubectl apply -f apex-os-api-pdb.yaml
```

### 3.2 Ingress Configuration

```yaml
# apex-os-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: apex-os-ingress
  namespace: apex-os-core
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/limit-rps: "50"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - apex-os.example.com
      secretName: apex-os-tls
  rules:
    - host: apex-os.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: apex-os-web
                port:
                  number: 80
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: apex-os-api
                port:
                  number: 8080
```

### 3.3 Network Policies

```yaml
# apex-os-network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: apex-os-api-policy
  namespace: apex-os-core
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: apex-os-api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: apex-os-web
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: apex-os-ingress-controller
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: apex-os-postgres
      ports:
        - protocol: TCP
          port: 5432
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: apex-os-redis
      ports:
        - protocol: TCP
          port: 6379
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
```

---

## 4. Helm Charts

### 4.1 Chart Structure

The Helm chart at `helm/` packages the entire APEX-OS application stack:

```
helm/
├── Chart.yaml          # Chart metadata (v1.0.0)
├── values.yaml         # Default configuration values
└── templates/          # (Generated by helm create)
    ├── _helpers.tpl
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    ├── hpa.yaml
    ├── pdb.yaml
    ├── serviceaccount.yaml
    ├── configmap.yaml
    ├── secret.yaml
    ├── networkpolicy.yaml
    ├── servicemonitor.yaml
    └── prometheusrule.yaml
```

### 4.2 Installation

```bash
# Add the chart repository (if published)
helm repo add apex-os https://charts.apex-os.io
helm repo update

# Install with default values
helm install apex-os ./helm \
  --namespace apex-os-core \
  --create-namespace

# Install with custom values
helm install apex-os ./helm \
  --namespace apex-os-core \
  --create-namespace \
  -f values-production.yaml

# Upgrade an existing release
helm upgrade apex-os ./helm \
  --namespace apex-os-core \
  -f values-production.yaml

# Uninstall
helm uninstall apex-os --namespace apex-os-core
```

### 4.3 Production Values File

```yaml
# values-production.yaml
global:
  environment: production
  imageRegistry: "registry.apex-os.io"
  imagePullSecrets:
    - name: apex-os-registry-credentials
  storageClass: "gp3-encrypted"

replicaCount:
  api: 3
  web: 3
  worker: 2

api:
  image:
    repository: apex-os/api
    tag: "1.0.0"
    pullPolicy: IfNotPresent
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: "2"
      memory: 1Gi
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20
    targetCPUUtilizationPercentage: 65
    targetMemoryUtilizationPercentage: 75
  env:
    - name: NODE_ENV
      value: production
    - name: LOG_LEVEL
      value: info
    - name: DB_HOST
      value: apex-os-postgres.apex-os-data.svc.cluster.local
    - name: DB_PORT
      value: "5432"
    - name: DB_NAME
      value: apexos
    - name: REDIS_HOST
      value: apex-os-redis.apex-os-data.svc.cluster.local
    - name: REDIS_PORT
      value: "6379"
  secrets:
    - apex-os-db-credentials
    - apex-os-redis-credentials

web:
  image:
    repository: apex-os/web
    tag: "1.0.0"
  resources:
    requests:
      cpu: 200m
      memory: 256Mi
    limits:
      cpu: "1"
      memory: 512Mi
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 12

worker:
  image:
    repository: apex-os/worker
    tag: "1.0.0"
  resources:
    requests:
      cpu: 300m
      memory: 384Mi
    limits:
      cpu: "1.5"
      memory: 768Mi
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 8

postgresql:
  enabled: true
  auth:
    username: apexos
    database: apexos
  primary:
    persistence:
      enabled: true
      storageClass: "gp3-encrypted"
      size: 50Gi
    resources:
      requests:
        cpu: 500m
        memory: 512Mi
      limits:
        cpu: "2"
        memory: 1Gi

redis:
  enabled: true
  auth:
    password: ""  # Pull from secret
  master:
    persistence:
      enabled: true
      storageClass: "gp3-encrypted"
      size: 10Gi
  replica:
    replicaCount: 1

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "600"
    nginx.ingress.kubernetes.io/rate-limit: "200"
    nginx.ingress.kubernetes.io/limit-rps: "100"
    nginx.ingress.kubernetes.io/enable-cors: "true"
  hosts:
    - host: app.apex-os.io
      paths:
        - path: /
          pathType: Prefix
          service: web
          port: 80
        - path: /api
          pathType: Prefix
          service: api
          port: 8080
  tls:
    enabled: true
    secretName: apex-os-tls
    hosts:
      - app.apex-os.io

networkPolicy:
  enabled: true

monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 15s
    scrapeTimeout: 10s
  prometheusRule:
    enabled: true
    rules:
      - alert: APEXOSHighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) 
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on APEX-OS API"
          description: "Error rate is above 5% for more than 5 minutes"
      - alert: APEXOSHighLatency
        expr: |
          histogram_quantile(0.95, 
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
          ) > 2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High latency on APEX-OS API"
          description: "95th percentile latency exceeds 2 seconds"

serviceMesh:
  enabled: true
  istio:
    enabled: true
    sidecar:
      inject: true

podDisruptionBudget:
  enabled: true
  minAvailable: 2

topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app.kubernetes.io/part-of: apex-os-business-platform
```

### 4.4 Chart Validation & Testing

```bash
# Lint the chart
helm lint ./helm

# Template rendering (dry-run)
helm template apex-os ./helm \
  --namespace apex-os-core \
  -f values-production.yaml \
  --debug

# Dry-run install
helm install apex-os ./helm \
  --namespace apex-os-core \
  --create-namespace \
  -f values-production.yaml \
  --dry-run --debug

# Run Helm unit tests (if using helm-unittest plugin)
helm unittest ./helm

# Package the chart
helm package ./helm --version 1.0.0 --app-version 1.0.0

# Verify the packaged chart
helm template apex-os ./helm-1.0.0.tgz --namespace apex-os-core
```

---

## 5. GitOps with ArgoCD

### 5.1 ArgoCD Installation

```bash
# Create ArgoCD namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for pods
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=120s

# Port-forward to access UI
kubectl port-forward svc/argocd-server -n argocd 8443:443

# Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d

# Login via CLI
argocd login localhost:8443 --username admin --password <password>

# Change password
argocd account update-password
```

### 5.2 App-of-Apps Pattern

The **App-of-Apps** pattern is the recommended GitOps structure for APEX-OS. A root "umbrella" application manages all child applications.

```yaml
# argocd/app-of-apps.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: apex-os-root
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: apex-os
  source:
    repoURL: https://github.com/apex-os/apex-os-gitops.git
    targetRevision: HEAD
    path: apps
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - PruneLast=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

### 5.3 Application Definitions

```yaml
# argocd/apps/apex-os-core.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: apex-os-core
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: apex-os
  source:
    repoURL: https://github.com/apex-os/apex-os-gitops.git
    targetRevision: HEAD
    path: environments/prod/core
    helm:
      valueFiles:
        - values-production.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: apex-os-core
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
---
# argocd/apps/apex-os-data.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: apex-os-data
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: apex-os
  source:
    repoURL: https://github.com/apex-os/apex-os-gitops.git
    targetRevision: HEAD
    path: environments/prod/data
  destination:
    server: https://kubernetes.default.svc
    namespace: apex-os-data
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
---
# argocd/apps/apex-os-monitoring.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: apex-os-monitoring
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: apex-os
  source:
    repoURL: https://github.com/apex-os/apex-os-gitops.git
    targetRevision: HEAD
    path: environments/prod/monitoring
  destination:
    server: https://kubernetes.default.svc
    namespace: apex-os-monitoring
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

### 5.4 Repository Structure

```
apex-os-gitops/
├── apps/
│   └── app-of-apps.yaml          # Root umbrella app
├── environments/
│   ├── dev/
│   │   ├── core/
│   │   │   ├── kustomization.yaml
│   │   │   └── values-dev.yaml
│   │   ├── data/
│   │   │   └── kustomization.yaml
│   │   └── monitoring/
│   │       └── kustomization.yaml
│   ├── staging/
│   │   ├── core/
│   │   │   ├── kustomization.yaml
│   │   │   └── values-staging.yaml
│   │   ├── data/
│   │   │   └── kustomization.yaml
│   │   └── monitoring/
│   │       └── kustomization.yaml
│   └── prod/
│       ├── core/
│       │   ├── kustomization.yaml
│       │   └── values-production.yaml
│       ├── data/
│       │   └── kustomization.yaml
│       └── monitoring/
│           └── kustomization.yaml
└── infrastructure/
    ├── argocd/
    │   ├── kustomization.yaml
    │   └── namespace.yaml
    ├── istio/
    │   ├── kustomization.yaml
    │   └── operator.yaml
    ├── cert-manager/
    │   ├── kustomization.yaml
    │   └── cluster-issuer.yaml
    └── ingress-nginx/
        ├── kustomization.yaml
        └── values.yaml
```

### 5.5 Secrets Management with External Secrets Operator

```yaml
# external-secrets/aws-secrets-manager.yaml
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secrets-manager
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
            namespace: apex-os-security
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: apex-os-db-credentials
  namespace: apex-os-data
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: apex-os-db-credentials
    creationPolicy: Owner
    template:
      type: Opaque
      data:
        username: "{{ .username }}"
        password: "{{ .password }}"
        url: "postgresql://{{ .username }}:{{ .password }}@apex-os-postgres:5432/apexos"
  data:
    - secretKey: username
      remoteRef:
        key: apex-os/prod/database
        property: username
    - secretKey: password
      remoteRef:
        key: apex-os/prod/database
        property: password
```

### 5.6 Progressive Delivery with Argo Rollouts

```yaml
# argocd/rollouts/apex-os-api-rollout.yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: apex-os-api
  namespace: apex-os-core
spec:
  replicas: 3
  strategy:
    canary:
      canaryService: apex-os-api-canary
      stableService: apex-os-api
      trafficRouting:
        istio:
          virtualService:
            name: apex-os-api-vs
            routes:
              - primary
      steps:
        - setWeight: 10
        - pause: { duration: 5m }
        - setWeight: 25
        - pause: { duration: 5m }
        - analysis:
            templates:
              - templateName: apex-os-success-rate
            args:
              - name: service-name
                value: apex-os-api-canary
        - setWeight: 50
        - pause: { duration: 5m }
        - setWeight: 75
        - pause: { duration: 5m }
        - setWeight: 100
  selector:
    matchLabels:
      app.kubernetes.io/name: apex-os-api
  template:
    metadata:
      labels:
        app.kubernetes.io/name: apex-os-api
    spec:
      containers:
        - name: api
          image: apex-os/api:1.0.0
          ports:
            - containerPort: 8080
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: apex-os-success-rate
  namespace: apex-os-core
spec:
  metrics:
    - name: success-rate
      interval: 1m
      count: 3
      successCondition: result[0] >= 0.95
      provider:
        prometheus:
          address: http://prometheus.apex-os-monitoring.svc:9090
          query: |
            sum(rate(http_requests_total{service="{{args.service-name}}",status!~"5.."}[1m]))
            /
            sum(rate(http_requests_total{service="{{args.service-name}}"}[1m]))
```

---

## 6. Service Mesh (Istio)

### 6.1 Istio Installation

```bash
# Install Istio with production profile
istioctl install --set profile=default -y

# Verify installation
istioctl verify-install

# Enable sidecar injection for namespaces
kubectl label namespace apex-os-core istio-injection=enabled
kubectl label namespace apex-os-data istio-injection=enabled
kubectl label namespace apex-os-monitoring istio-injection=enabled

# Verify sidecar injection
kubectl get namespace -L istio-injection
```

### 6.2 Traffic Management

```yaml
# istio/gateway.yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: apex-os-gateway
  namespace: apex-os-core
spec:
  selector:
    istio: ingressgateway
  servers:
    - port:
        number: 443
        name: https
        protocol: HTTPS
      tls:
        mode: SIMPLE
        credentialName: apex-os-tls
      hosts:
        - "app.apex-os.io"
    - port:
        number: 80
        name: http
        protocol: HTTP
      hosts:
        - "app.apex-os.io"
      tls:
        httpsRedirect: true
---
# istio/virtual-service.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: apex-os-vs
  namespace: apex-os-core
spec:
  hosts:
    - "app.apex-os.io"
  gateways:
    - apex-os-gateway
  http:
    - name: web-route
      match:
        - uri:
            prefix: /
      route:
        - destination:
            host: apex-os-web
            port:
              number: 80
    - name: api-route
      match:
        - uri:
            prefix: /api
      route:
        - destination:
            host: apex-os-api
            port:
              number: 8080
      retries:
        attempts: 3
        perTryTimeout: 5s
        retryOn: gateway-error,connect-failure,refused-stream
      timeout: 30s
      fault:
        delay:
          percentage:
            value: 0.1
          fixedDelay: 5s
---
# istio/destination-rule.yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: apex-os-api-dr
  namespace: apex-os-core
spec:
  host: apex-os-api
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
        maxRequestsPerConnection: 10
    loadBalancer:
      simple: LEAST_CONN
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
  subsets:
    - name: stable
      labels:
        version: stable
    - name: canary
      labels:
        version: canary
```

### 6.3 mTLS & Security Policies

```yaml
# istio/peer-authentication.yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: apex-os-core
spec:
  mtls:
    mode: STRICT
---
# istio/authorization-policy.yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: apex-os-api-authz
  namespace: apex-os-core
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: apex-os-api
  action: ALLOW
  rules:
    - from:
        - source:
            principals:
              - "cluster.local/ns/apex-os-core/sa/apex-os-web"
              - "cluster.local/ns/apex-os-core/sa/apex-os-ingress-controller"
      to:
        - operation:
            methods: ["GET", "POST", "PUT", "DELETE", "PATCH"]
            paths: ["/api/*", "/health", "/ready"]
    - from:
        - source:
            principals:
              - "cluster.local/ns/apex-os-monitoring/sa/prometheus"
      to:
        - operation:
            methods: ["GET"]
            paths: ["/metrics"]
```

### 6.4 Observability with Kiali

```yaml
# istio/kiali-dashboard.yaml
apiVersion: kiali.io/v1alpha1
kind: Kiali
metadata:
  name: kiali
  namespace: istio-system
spec:
  auth:
    strategy: anonymous
  deployment:
    accessible_namespaces:
      - "**"
    image_version: latest
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
  external_services:
    prometheus:
      url: http://prometheus.apex-os-monitoring.svc:9090
    grafana:
      url: http://grafana.apex-os-monitoring.svc:3000
    tracing:
      url: http://jaeger-query.apex-os-monitoring.svc:16686
```

---

## 7. Monitoring & Observability

### 7.1 Prometheus Stack Installation

```bash
# Add Helm repos
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install kube-prometheus-stack
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace apex-os-monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=gp3-encrypted \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
  --set grafana.adminPassword=admin \
  --set grafana.persistence.enabled=true \
  --set grafana.persistence.size=10Gi \
  --set alertmanager.alertmanagerSpec.storage.volumeClaimTemplate.spec.storageClassName=gp3-encrypted \
  --set alertmanager.alertmanagerSpec.storage.volumeClaimTemplate.spec.resources.requests.storage=5Gi
```

### 7.2 ServiceMonitor Configuration

```yaml
# monitoring/servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: apex-os-api-monitor
  namespace: apex-os-monitoring
  labels:
    release: monitoring
spec:
  namespaceSelector:
    matchNames:
      - apex-os-core
  selector:
    matchLabels:
      app.kubernetes.io/name: apex-os-api
  endpoints:
    - port: http
      interval: 15s
      scrapeTimeout: 10s
      path: /metrics
      scheme: http
      metricRelabelings:
        - sourceLabels: [__name__]
          regex: 'go_.*'
          action: drop
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: apex-os-web-monitor
  namespace: apex-os-monitoring
  labels:
    release: monitoring
spec:
  namespaceSelector:
    matchNames:
      - apex-os-core
  selector:
    matchLabels:
      app.kubernetes.io/name: apex-os-web
  endpoints:
    - port: http
      interval: 15s
      path: /metrics
```

### 7.3 Prometheus Rules (Alerting)

```yaml
# monitoring/prometheus-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: apex-os-alerts
  namespace: apex-os-monitoring
  labels:
    release: monitoring
spec:
  groups:
    - name: apex-os-api
      rules:
        - alert: APEXOSHighErrorRate
          expr: |
            sum(rate(http_requests_total{service="apex-os-api",status=~"5.."}[5m]))
            / sum(rate(http_requests_total{service="apex-os-api"}[5m])) > 0.05
          for: 5m
          labels:
            severity: critical
            team: platform
          service: apex-os-api
          annotations:
            summary: "High error rate on APEX-OS API"
            description: "Error rate is {{ $value | humanizePercentage }} for more than 5 minutes"
            runbook_url: "https://wiki.apex-os.io/runbooks/high-error-rate"

        - alert: APEXOSHighLatency
          expr: |
            histogram_quantile(0.95,
              sum(rate(http_request_duration_seconds_bucket{service="apex-os-api"}[5m])) by (le)
            ) > 2
          for: 10m
          labels:
            severity: warning
            team: platform
            service: apex-os-api
          annotations:
            summary: "High latency on APEX-OS API"
            description: "95th percentile latency is {{ $value }}s"

        - alert: APEXOSHighCPUUsage
          expr: |
            sum(rate(container_cpu_usage_seconds_total{namespace="apex-os-core",container="api"}[5m]))
            / sum(kube_pod_container_resource_limits{namespace="apex-os-core",container="api",resource="cpu"}) > 0.85
          for: 15m
          labels:
            severity: warning
            team: platform
          annotations:
            summary: "High CPU usage on APEX-OS API"
            description: "CPU usage is above 85% of limit for 15 minutes"

        - alert: APEXOSHighMemoryUsage
          expr: |
            sum(container_memory_working_set_bytes{namespace="apex-os-core",container="api"})
            / sum(kube_pod_container_resource_limits{namespace="apex-os-core",container="api",resource="memory"}) > 0.85
          for: 15m
          labels:
            severity: warning
            team: platform
          annotations:
            summary: "High memory usage on APEX-OS API"
            description: "Memory usage is above 85% of limit for 15 minutes"

        - alert: APEXOSPodCrashLooping
          expr: |
            rate(kube_pod_container_status_restarts_total{namespace="apex-os-core"}[15m]) > 0
          for: 5m
          labels:
            severity: critical
            team: platform
          annotations:
            summary: "Pod is crash looping"
            description: "Pod {{ $labels.pod }} is restarting frequently"

        - alert: APEXOSDatabaseConnectionsHigh
          expr: |
            pg_stat_activity_count{namespace="apex-os-data"} > 80
          for: 10m
          labels:
            severity: warning
            team: data
          annotations:
            summary: "High database connection count"
            description: "PostgreSQL has {{ $value }} active connections"

    - name: apex-os-worker
      rules:
        - alert: APEXOSWorkerQueueBacklog
          expr: |
            apex_os_worker_queue_depth > 1000
          for: 10m
          labels:
            severity: warning
            team: platform
          annotations:
            summary: "Worker queue backlog"
            description: "Worker queue depth is {{ $value }}"

        - alert: APEXOSWorkerDown
          expr: |
            up{job="apex-os-worker"} == 0
          for: 5m
          labels:
            severity: critical
            team: platform
          annotations:
            summary: "Worker is down"
            description: "Worker {{ $labels.instance }} is not responding"
```

### 7.4 Grafana Dashboards

```json
{
  "dashboard": {
    "title": "APEX-OS Business Platform",
    "uid": "apex-os-overview",
    "timezone": "browser",
    "schemaVersion": 39,
    "version": 1,
    "refresh": "30s",
    "time": { "from": "now-6h", "to": "now" },
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 0 },
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{service=\"apex-os-api\"}[5m])) by (status)",
            "legendFormat": "{{status}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Response Time (p95)",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 12, "y": 0 },
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service=\"apex-os-api\"}[5m])) by (le))",
            "legendFormat": "p95"
          }
        ]
      },
      {
        "id": 3,
        "title": "Error Rate",
        "type": "stat",
        "gridPos": { "h": 4, "w": 6, "x": 0, "y": 8 },
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{service=\"apex-os-api\",status=~\"5..\"}[5m])) / sum(rate(http_requests_total{service=\"apex-os-api\"}[5m]))",
            "legendFormat": "Error %"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                { "color": "green", "value": null },
                { "color": "yellow", "value": 0.01 },
                { "color": "red", "value": 0.05 }
              ]
            },
            "unit": "percentunit"
          }
        }
      },
      {
        "id": 4,
        "title": "Pod Count",
        "type": "stat",
        "gridPos": { "h": 4, "w": 6, "x": 6, "y": 8 },
        "targets": [
          {
            "expr": "count(kube_pod_status_phase{namespace=\"apex-os-core\",phase=\"Running\"})",
            "legendFormat": "Running Pods"
          }
        ]
      },
      {
        "id": 5,
        "title": "CPU Usage",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 12 },
        "targets": [
          {
            "expr": "sum(rate(container_cpu_usage_seconds_total{namespace=\"apex-os-core\"}[5m])) by (pod)",
            "legendFormat": "{{pod}}"
          }
        ]
      },
      {
        "id": 6,
        "title": "Memory Usage",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 12, "y": 12 },
        "targets": [
          {
            "expr": "sum(container_memory_working_set_bytes{namespace=\"apex-os-core\"}) by (pod)",
            "legendFormat": "{{pod}}"
          }
        ]
      }
    ]
  }
}
```

### 7.5 Log Aggregation with Loki

```yaml
# monitoring/loki-values.yaml
loki:
  enabled: true
  persistence:
    enabled: true
    size: 50Gi
    storageClassName: gp3-encrypted
  config:
    limits_config:
      retention_period: 720h
      reject_old_samples_max_age: 168h
    schema_config:
      configs:
        - from: 2024-01-01
          store: boltdb-shipper
          object_store: s3
          schema: v12
          index:
            prefix: loki_index_
            period: 24h
    storage_config:
      boltdb_shipper:
        active_index_directory: /var/loki/boltdb-shipper-active
        cache_location: /var/loki/boltdb-shipper-cache
        cache_ttl: 24h
        shared_store: s3
      aws:
        s3: s3://us-east-1/apex-os-loki-logs
        region: us-east-1

promtail:
  enabled: true
  config:
    snippets:
      pipelineStages:
        - docker: {}
        - cri: {}
        - json:
            expressions:
              level: level
              msg: message
        - labels:
            level:
```

### 7.6 Distributed Tracing with Tempo

```yaml
# monitoring/tempo-values.yaml
tempo:
  enabled: true
  persistence:
    enabled: true
    size: 20Gi
    storageClassName: gp3-encrypted
  config:
    storage:
      trace:
        backend: s3
        s3:
          bucket: apex-os-tempo-traces
          endpoint: s3.us-east-1.amazonaws.com
          region: us-east-1
    overrides:
      per_tenant_override_config: overrides.yaml

tempoQuery:
  enabled: true
```

### 7.7 Alertmanager Configuration

```yaml
# monitoring/alertmanager-config.yaml
apiVersion: v1
kind: Secret
metadata:
  name: alertmanager-config
  namespace: apex-os-monitoring
stringData:
  alertmanager.yml: |
    global:
      smtp_smarthost: email-smtp.us-east-1.amazonaws.com:587
      smtp_from: alerts@apex-os.io
      smtp_auth_username: ""
      smtp_auth_password: ""
      slack_api_url: ""
      pagerduty_url: https://events.pagerduty.com/v2/enqueue

    route:
      receiver: default
      group_by: ['alertname', 'severity', 'service']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      routes:
        - match:
            severity: critical
          receiver: pagerduty-critical
          group_wait: 0s
          repeat_interval: 1h
        - match:
            severity: warning
          receiver: slack-warnings
          group_wait: 30s
          repeat_interval: 4h
        - match_re:
            service: apex-os-(api|worker)
          receiver: platform-team
          group_wait: 30s

    receivers:
      - name: default
        email_configs:
          - to: platform-team@apex-os.io
            send_resolved: true

      - name: pagerduty-critical
        pagerduty_configs:
          - service_key: ""
            severity: critical
            description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'

      - name: slack-warnings
        slack_configs:
          - channel: '#apex-os-alerts'
            send_resolved: true
            title: '{{ .GroupLabels.alertname }}'
            text: '{{ .CommonAnnotations.description }}'

      - name: platform-team
        email_configs:
          - to: platform-team@apex-os.io
            send_resolved: true
        slack_configs:
          - channel: '#apex-os-platform'
            send_resolved: true

    inhibit_rules:
      - source_match:
          severity: critical
        target_match:
          severity: warning
        equal: ['alertname', 'service']
```

---

## 8. Security Hardening

### 8.1 Pod Security Standards

```yaml
# security/pod-security.yaml
apiVersion: policy/v1
kind: PodSecurityPolicy
metadata:
  name: apex-os-restricted
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
  readOnlyRootFilesystem: true
```

### 8.2 RBAC Configuration

```yaml
# security/rbac.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: apex-os-api-role
  namespace: apex-os-core
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "watch", "list"]
  - apiGroups: [""]
    resources: ["secrets"]
    resourceNames: ["apex-os-db-credentials", "apex-os-redis-credentials"]
    verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: apex-os-api-binding
  namespace: apex-os-core
subjects:
  - kind: ServiceAccount
    name: apex-os-api
    namespace: apex-os-core
roleRef:
  kind: Role
  name: apex-os-api-role
  apiGroup: rbac.authorization.k8s.io
```

### 8.3 Secrets Encryption

```yaml
# security/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64-encoded-32-byte-key>
      - identity: {}
```

### 8.4 Image Security

```bash
# Scan images with Trivy
trivy image apex-os/api:1.0.0
trivy image apex-os/web:1.0.0
trivy image apex-os/worker:1.0.0

# Scan with Grype
grype apex-os/api:1.0.0

# Verify image signatures with Cosign
cosign verify --key cosign.pub registry.apex-os.io/apex-os/api:1.0.0
```

### 8.5 Falco Runtime Security

```yaml
# security/falco-values.yaml
falco:
  rules:
    - rule: Terminal shell in container
      desc: A shell was used as the entrypoint/exec point into a container
      condition: >
        spawned_process and container
        and shell_procs and proc.tty != 0
        and container_entrypoint
      output: >
        A shell was spawned in a container with an attached terminal
        (user=%user.name %container.info shell=%proc.name parent=%proc.pname
        cmdline=%proc.cmdline terminal=%proc.tty)
      priority: WARNING

    - rule: Unauthorized database access
      desc: Detect unauthorized access to PostgreSQL
      condition: >
        inbound and fd.sport = 5432
        and not (fd.name in (allowed_db_clients))
      output: >
        Unauthorized connection to PostgreSQL
        (connection=%fd.name command=%proc.cmdline)
      priority: CRITICAL
```

---

## 9. Multi-Cloud Reference

### 9.1 AWS (EKS)

| Resource | Configuration |
|----------|--------------|
| VPC CIDR | 10.0.0.0/16 |
| Private Subnets | 10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24 |
| Public Subnets | 10.0.101.0/24, 10.0.102.0/24, 10.0.103.0/24 |
| EKS Version | 1.28 |
| Node Instance | t3.large |
| Node Scaling | 2-6 (desired: 3) |
| RDS Engine | PostgreSQL 15.4 |
| RDS Instance | db.t3.medium (Multi-AZ) |
| RDS Storage | 100 GB |
| S3 Buckets | apex-os-data, apex-os-backups, apex-os-logs |
| WAF | Enabled |
| GuardDuty | Enabled |
| Security Hub | Enabled |
| Flow Logs | Enabled |

### 9.2 Azure (AKS)

| Resource | Configuration |
|----------|--------------|
| VNet CIDR | 10.1.0.0/16 |
| Location | East US |
| AKS Version | 1.28 |
| Node VM Size | Standard_D2s_v3 |
| Node Count | 3 |
| Resource Group | apex-os-rg |

### 9.3 GCP (GKE)

| Resource | Configuration |
|----------|--------------|
| VPC CIDR | 10.2.0.0/16 |
| Region | us-central1 |
| GKE Version | 1.28 |
| Machine Type | e2-medium |
| Node Count | 3 |

### 9.4 Cross-Cloud DNS & Global Load Balancing

```yaml
# dns/global-dns.yaml
apiVersion: externaldns.k8s.io/v1alpha1
kind: DNSEndpoint
metadata:
  name: apex-os-global
  namespace: apex-os-core
spec:
  endpoints:
    - dnsName: app.apex-os.io
      recordType: A
      recordTTL: 300
      targets:
        - 1.2.3.4  # AWS ALB
        - 5.6.7.8  # Azure LB
        - 9.10.11.12  # GCP LB
      providerSpecific:
        - name: weight
          value: "100"
```

---

## 10. Runbooks & Troubleshooting

### 10.1 Common Issues

#### Pod Stuck in Pending

```bash
# Check events
kubectl describe pod <pod-name> -n apex-os-core

# Check resource quotas
kubectl get resourcequota -n apex-os-core

# Check node capacity
kubectl describe node <node-name>

# Check PVC status
kubectl get pvc -n apex-os-data
```

#### High Error Rate

```bash
# Check logs
kubectl logs -l app.kubernetes.io/name=apex-os-api -n apex-os-core --tail=500

# Check recent deployments
kubectl rollout history deployment/apex-os-api -n apex-os-core

# Rollback if needed
kubectl rollout undo deployment/apex-os-api -n apex-os-core

# Check HPA status
kubectl get hpa -n apex-os-core
```

#### Database Connection Issues

```bash
# Check PostgreSQL pod
kubectl get pods -n apex-os-data -l app.kubernetes.io/name=postgresql

# Check PostgreSQL logs
kubectl logs -n apex-os-data -l app.kubernetes.io/name=postgresql --tail=100

# Test connection from API pod
kubectl exec -it deploy/apex-os-api -n apex-os-core -- \
  nc -zv apex-os-postgres.apex-os-data.svc.cluster.local 5432

# Check connection pool
kubectl exec -it deploy/apex-os-postgres -n apex-os-data -- \
  psql -U apexos -c "SELECT count(*) FROM pg_stat_activity;"
```

#### Service Mesh Issues

```bash
# Check sidecar injection
kubectl get pods -n apex-os-core -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].name}{"\n"}{end}'

# Check Envoy proxy status
kubectl exec -it <pod-name> -n apex-os-core -c istio-proxy -- \
  pilot-agent request GET /config_dump

# Check Istio configuration
istioctl proxy-config cluster <pod-name> -n apex-os-core
istioctl proxy-config routes <pod-name> -n apex-os-core

# Analyze cluster configuration
istioctl analyze -n apex-os-core
```

### 10.2 Disaster Recovery

```bash
# Backup PostgreSQL
kubectl exec -it deploy/apex-os-postgres -n apex-os-data -- \
  pg_dump -U apexos apexos > apex-os-backup-$(date +%Y%m%d).sql

# Backup Redis
kubectl exec -it deploy/apex-os-redis -n apex-os-data -- \
  redis-cli SAVE

# Restore PostgreSQL
kubectl exec -i deploy/apex-os-postgres -n apex-os-data -- \
  psql -U apexos apexos < apex-os-backup-20261001.sql

# Velero backup (cluster-level)
velero backup create apex-os-daily \
  --include-namespaces apex-os-core,apex-os-data,apex-os-monitoring \
  --ttl 720h0m0s

# Velero restore
velero restore create --from-backup apex-os-daily
```

### 10.3 Performance Tuning

```yaml
# performance/vertical-pod-autoscaler.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: apex-os-api-vpa
  namespace: apex-os-core
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: apex-os-api
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
      - containerName: api
        minAllowed:
          cpu: 100m
          memory: 128Mi
        maxAllowed:
          cpu: "4"
          memory: 4Gi
        controlledResources: ["cpu", "memory"]
```

---

## Appendix A: Quick Reference Commands

```bash
# ── Cluster ──
kubectl config current-context
kubectl get nodes -o wide
kubectl get pods -A -o wide

# ── Helm ──
helm list -n apex-os-core
helm status apex-os -n apex-os-core
helm get values apex-os -n apex-os-core
helm rollback apex-os 1 -n apex-os-core

# ── ArgoCD ──
argocd app list
argocd app get apex-os-core
argocd app sync apex-os-core
argocd app logs apex-os-core

# ── Istio ──
istioctl proxy-status
istioctl dashboard kiali
istioctl dashboard grafana
istioctl dashboard prometheus

# ── Monitoring ──
kubectl port-forward svc/prometheus 9090:9090 -n apex-os-monitoring
kubectl port-forward svc/grafana 3000:3000 -n apex-os-monitoring
kubectl port-forward svc/alertmanager 9093:9093 -n apex-os-monitoring

# ── Logs ──
kubectl logs -f deploy/apex-os-api -n apex-os-core --tail=100
kubectl logs -f deploy/apex-os-worker -n apex-os-core --tail=100
stern apex-os -n apex-os-core
```

## Appendix B: Environment Promotion Pipeline

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│   Dev    │───▶│  Staging │───▶│  Pre-Prod│───▶│   Prod   │
│  (auto)  │    │  (auto)  │    │ (manual) │    │ (manual) │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │
     ▼               ▼               ▼               ▼
  PR merge       CI pass         QA sign-off     Change ticket
  + auto sync    + auto sync     + approval      + approval
```

---

*This guide is maintained by the APEX-OS Platform Team. For updates, contact platform-team@apex-os.io.*
