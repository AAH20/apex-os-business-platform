# APEX-OS Kubernetes Architecture

## 1. Architecture Overview

```mermaid
graph TB
    classDef cp fill:#1a1a2e,stroke:#4a9eff,color:#e0e0e0
    classDef wn fill:#16213e,stroke:#4a9eff,color:#e0e0e0
    classDef pod fill:#0f3460,stroke:#e94560,color:#e0e0e0
    classDef svc fill:#533483,stroke:#e94560,color:#e0e0e0
    API[API Server]:::cp
    ETCD[(etcd)]:::cp
    SCHED[Scheduler]:::cp
    CM[Controller Manager]:::cp
    KUBELET[Kubelet]:::wn
    KPROXY[kube-proxy]:::wn
    CRI[Container Runtime]:::wn
    API_POD[api-server]:::pod
    AUTH_POD[auth-service]:::pod
    DB_POD[(postgres)]:::pod
    WEB_POD[web-frontend]:::pod
    WORKER_POD[background-worker]:::pod
    CACHE_POD[(redis)]:::pod
    ING[Ingress]:::svc
    LB[Load Balancer]:::svc
    SVC_API[Service: api]:::svc
    SVC_WEB[Service: web]:::svc
    LB --> ING --> SVC_API --> API_POD
    ING --> SVC_WEB --> WEB_POD
    API_POD --> AUTH_POD & DB_POD & CACHE_POD
    WORKER_POD --> DB_POD & CACHE_POD
    API --> ETCD
    SCHED --> API
    CM --> API
    API --> KUBELET --> CRI
```

| Component | Role |
|-----------|------|
| API Server | Cluster gateway; validates and processes REST requests |
| etcd | Distributed key-value store for all cluster state |
| Scheduler | Assigns Pods to Nodes based on resource requirements |
| Controller Manager | Runs controller loops (replica, endpoint, namespace) |
| Kubelet | Node agent; ensures containers run in Pods |
| kube-proxy | Maintains network rules for Service abstraction |

---

## 2. Deployment Strategy

### Rolling Updates

```mermaid
graph LR
    classDef old fill:#1a1a2e,stroke:#e94560,color:#e0e0e0
    classDef new fill:#16213e,stroke:#4ade80,color:#e0e0e0
    O1[Pod v1]:::old
    O2[Pod v1]:::old
    N1[Pod v2]:::new
    O3[Pod v1]:::old
    N2[Pod v2]:::new
    N3[Pod v2]:::new
    N4[Pod v2]:::new
    N5[Pod v2]:::new
    N6[Pod v2]:::new
    O1 --> O2 --> N1 --> O3 --> N2 --> N3 --> N4 --> N5 --> N6
```

### Deployment Config

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apex-api
  namespace: apex-core
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: apex-api
  template:
    metadata:
      labels:
        app: apex-api
    spec:
      containers:
        - name: api
          image: apexos/api:v2.3.1
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
```

### Blue-Green Deployment

```mermaid
graph TB
    classDef blue fill:#1a1a2e,stroke:#4a9eff,color:#e0e0e0
    classDef green fill:#16213e,stroke:#4ade80,color:#e0e0e0
    classDef inactive fill:#1a1a2e,stroke:#666,color:#888
    B1[Pod v2.3.0]:::blue
    B2[Pod v2.3.0]:::blue
    G1[Pod v2.4.0]:::green
    G2[Pod v2.4.0]:::green
    SVC[Service Selector]:::inactive
    SVC -->|current: v2.3.0| B1
    SVC -->|current: v2.3.0| B2
    SVC -.->|switch: v2.4.0| G1
    SVC -.->|switch: v2.4.0| G2
```

---

## 3. Scaling Strategy

### HPA

```mermaid
graph TB
    classDef metric fill:#1a1a2e,stroke:#e94560,color:#e0e0e0
    classDef action fill:#16213e,stroke:#4ade80,color:#e0e0e0
    CPU[CPU > 70%]:::metric
    MEM[Memory > 80%]:::metric
    QPS[Queue Depth]:::metric
    HPA[HPA Controller]:::action
    SCALE[Scale Replicas]:::action
    CPU --> HPA
    MEM --> HPA
    QPS --> HPA
    HPA --> SCALE
```

### HPA Config

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: apex-api-hpa
  namespace: apex-core
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: apex-api
  minReplicas: 3
  maxReplicas: 20
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
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Percent
          value: 100
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

### Cluster Autoscaler

```mermaid
graph LR
    classDef trigger fill:#1a1a2e,stroke:#e94560,color:#e0e0e0
    classDef node fill:#16213e,stroke:#4a9eff,color:#e0e0e0
    PENDING[Pending Pods]:::trigger
    CA[Cluster Autoscaler]:::trigger
    NEW[New Node]:::node
    JOIN[Node Joins]:::node
    SCHED[Pods Scheduled]:::node
    PENDING --> CA --> NEW --> JOIN --> SCHED
```

| Layer | Mechanism | Trigger |
|-------|-----------|---------|
| Pod | HPA | CPU / Memory / Custom metrics |
| Node | Cluster Autoscaler | Pending pods / resource pressure |
| Cluster | Multi-AZ / Regional | Availability requirements |

---

## 4. Monitoring

### Observability Stack

```mermaid
graph TB
    classDef source fill:#1a1a2e,stroke:#4a9eff,color:#e0e0e0
    classDef collect fill:#16213e,stroke:#e94560,color:#e0e0e0
    classDef store fill:#533483,stroke:#e94560,color:#e0e0e0
    classDef viz fill:#0f3460,stroke:#4ade80,color:#e0e0e0
    PODS[Pod Metrics]:::source
    NODES[Node Metrics]:::source
    APP[App Logs]:::source
    DIST[Traces]:::source
    PROM[Prometheus]:::collect
    FLUENT[Fluent Bit]:::collect
    OTEL[OpenTelemetry]:::collect
    TSDB[(Prometheus TSDB)]:::store
    LOKI[(Loki)]:::store
    TEMPO[(Tempo)]:::store
    GRAFANA[Grafana]:::viz
    ALERT[Alertmanager]:::viz
    PODS --> PROM
    NODES --> PROM
    APP --> FLUENT
    DIST --> OTEL
    PROM --> TSDB
    FLUENT --> LOKI
    OTEL --> TEMPO
    TSDB --> GRAFANA
    LOKI --> GRAFANA
    TEMPO --> GRAFANA
    PROM --> ALERT
```

| Category | Metrics | Tool |
|----------|---------|------|
| Cluster | Node CPU, memory, disk, network | Prometheus + node-exporter |
| Pod | Restart count, readiness, resource usage | Prometheus + kube-state-metrics |
| Application | Request rate, error rate, latency (RED) | OpenTelemetry + Prometheus |
| Logs | Structured logs, error patterns | Loki + Fluent Bit |
| Traces | Request flow, bottleneck identification | Tempo + OpenTelemetry |

### Alert Rules

```yaml
groups:
  - name: apex-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
      - alert: PodCrashLooping
        expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
        for: 5m
        labels:
          severity: warning
      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.85
        for: 10m
        labels:
          severity: warning
```

---

## 5. Security

### Defense in Depth

```mermaid
graph TB
    classDef l1 fill:#1a1a2e,stroke:#e94560,color:#e0e0e0
    classDef l2 fill:#16213e,stroke:#4a9eff,color:#e0e0e0
    classDef l3 fill:#533483,stroke:#e94560,color:#e0e0e0
    classDef l4 fill:#0f3460,stroke:#4ade80,color:#e0e0e0
    RBAC[RBAC]:::l1
    NETPOL[Network Policies]:::l1
    AUDIT[Audit Logging]:::l1
    SELINUX[SELinux / AppArmor]:::l2
    SECCOMP[Seccomp]:::l2
    ROOTLESS[Rootless]:::l2
    PSA[Pod Security Admission]:::l3
    SA[Service Accounts]:::l3
    SECRETS[Secrets Encryption]:::l3
    SCAN[Image Scanning]:::l4
    SIGN[Image Signing]:::l4
    REGISTRY[Private Registry]:::l4
    RBAC --> NETPOL --> AUDIT --> SELINUX --> SECCOMP --> ROOTLESS --> PSA --> SA --> SECRETS --> SCAN --> SIGN --> REGISTRY
```

### RBAC Example

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: apex-core
  name: api-reader
rules:
  - apiGroups: [""]
    resources: ["pods", "services"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: api-reader-binding
  namespace: apex-core
subjects:
  - kind: ServiceAccount
    name: api-reader
    namespace: apex-core
roleRef:
  kind: Role
  name: api-reader
  apiGroup: rbac.authorization.k8s.io
```

### Network Policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: apex-api-netpol
  namespace: apex-core
spec:
  podSelector:
    matchLabels:
      app: apex-api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: apex-apps
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - protocol: TCP
          port: 5432
```

### Pod Security Standards

| Level | Description | Use Case |
|-------|-------------|----------|
| Privileged | Unrestricted | System components only |
| Baseline | Minimizes privilege escalation | Most workloads |
| Restricted | Hardened, follows best practices | Production workloads |

### Secrets Management

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: apex-db-credentials
  namespace: apex-core
type: Opaque
stringData:
  username: apex_app
  password: <encrypted-at-rest>
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: apex-db-credentials
  namespace: apex-core
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: apex-db-credentials
  data:
    - secretKey: password
      remoteRef:
        key: apex/prod/db
        property: password
```

### Security Checklist

- [ ] RBAC enabled with least-privilege roles
- [ ] Network Policies restrict pod-to-pod traffic
- [ ] Pod Security Standards enforced (restricted)
- [ ] Secrets encrypted at rest (KMS)
- [ ] Images scanned for vulnerabilities (Trivy/Grype)
- [ ] Images signed and verified (Cosign)
- [ ] Audit logging enabled and shipped
- [ ] Service accounts use minimal tokens
- [ ] Containers run as non-root
- [ ] Read-only root filesystem where possible
- [ ] Resource limits set on all containers
- [ ] Admission controllers enabled (OPA/Gatekeeper)
