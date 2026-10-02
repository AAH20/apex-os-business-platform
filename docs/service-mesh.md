# Service Mesh

## 1. Architecture

APEX-OS uses a sidecar-based service mesh (Istio/Envoy) for all inter-service communication.

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','primaryBorderColor':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#0f3460','edgeLabelBackground':'#1a1a2e'}}}%%
graph TB
    subgraph "External"
        Client[Client]
        GW[Ingress Gateway]
    end

    subgraph "Service Mesh"
        subgraph "Service A"
            A1[App Container] --- A2[Envoy Sidecar]
        end
        subgraph "Service B"
            B1[App Container] --- B2[Envoy Sidecar]
        end
        subgraph "Service C"
            C1[App Container] --- C2[Envoy Sidecar]
        end
        subgraph "Service D"
            D1[App Container] --- D2[Envoy Sidecar]
        end
    end

    subgraph "Control Plane"
        Istiod[Istiod / Pilot]
        Citadel[Citadel / Cert Manager]
    end

    Client --> GW
    GW --> A2
    A2 --> B2
    A2 --> C2
    B2 --> D2
    C2 --> D2

    Istiod -.->|xDS| A2
    Istiod -.->|xDS| B2
    Istiod -.->|xDS| C2
    Istiod -.->|xDS| D2
    Citadel -.->|mTLS Certs| A2
    Citadel -.->|mTLS Certs| B2
    Citadel -.->|mTLS Certs| C2
    Citadel -.->|mTLS Certs| D2
```

### Components

| Component | Role |
|-----------|------|
| **Envoy Sidecar** | L4/L7 proxy; handles routing, mTLS, retries, circuit breaking |
| **Istiod (Pilot)** | Service discovery, config distribution (xDS API) |
| **Citadel** | Certificate authority; issues and rotates mTLS certs |
| **Ingress Gateway** | North-south traffic entry point (Envoy-based) |

---

## 2. Traffic Management

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','primaryBorderColor':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#0f3460','edgeLabelBackground':'#1a1a2e'}}}%%
flowchart LR
    Req[Request] --> VS{VirtualService}
    VS -->|v1: 90%| S1[Service A v1]
    VS -->|v2: 10%| S2[Service A v2]
    VS -->|mirror: 5%| S3[Service A v2 Shadow]

    S1 --> DR{DestinationRule}
    S2 --> DR
    DR -->|least_request| E1[Endpoint 1]
    DR -->|least_request| E2[Endpoint 2]
    DR -->|least_request| E3[Endpoint 3]

    E1 --> CB{Circuit Breaker}
    E2 --> CB
    E3 --> CB
    CB -->|open| Fallback[Fallback Response]
```

### Routing Strategies

| Strategy | Use Case | Resource |
|----------|----------|----------|
| **Canary** | Gradual rollout by weight | `VirtualService` + `DestinationRule` |
| **Blue/Green** | Instant cutover | `VirtualService` subset swap |
| **A/B Testing** | Header/cookie-based routing | `VirtualService` match rules |
| **Traffic Mirroring** | Shadow testing | `VirtualService.mirror` |
| **Fault Injection** | Chaos testing | `VirtualService.fault` |

### Resilience Patterns

- **Retries**: 3 attempts with exponential backoff (base 25ms, max 1s)
- **Timeouts**: 500ms default, 5s max per hop
- **Circuit Breakers**: Ejection after 5 consecutive 5xx errors; 30s ejection window
- **Outlier Detection**: Automatic endpoint ejection on error rate > 50%

---

## 3. Security

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','primaryBorderColor':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#0f3460','edgeLabelBackground':'#1a1a2e'}}}%%
flowchart TB
    subgraph "Zero Trust"
        A[Service A] -->|mTLS| B[Service B]
        B -->|mTLS| C[Service C]
    end

    subgraph "Policy Enforcement"
        PA[PeerAuthentication<br/>STRICT mTLS]
        Au[AuthorizationPolicy<br/>deny-by-default]
        Ra[RequestAuthentication<br/>JWT validation]
    end

    subgraph "Identity"
        SA[ServiceAccount<br/>K8s]
        SPIFFE[SPIFFE ID<br/>spiffe://apex/ns/sa/svc]
    end

    SA --> SPIFFE
    SPIFFE --> PA
    PA --> Au
    Au --> Ra
```

### Security Layers

| Layer | Mechanism | Details |
|-------|-----------|---------|
| **Transport** | mTLS (STRICT) | All pod-to-pod traffic encrypted; certs rotated every 24h |
| **Identity** | SPIFFE / SPIRE | Workload identity via Kubernetes ServiceAccount |
| **Authorization** | AuthorizationPolicy | Deny-by-default; explicit allow rules per service |
| **Authentication** | RequestAuthentication | JWT validation at mesh edge (JWKS endpoint) |
| **Network** | NetworkPolicy | L3/L4 segmentation between namespaces |

### Certificate Lifecycle

1. Citadel issues X.509 cert with SPIFFE URI SAN
2. Envoy sidecar picks up cert via SDS (Secret Discovery Service)
3. Automatic rotation at 80% of cert lifetime
4. Old cert remains valid during 1h overlap window

---

## 4. Observability

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','primaryBorderColor':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#0f3460','edgeLabelBackground':'#1a1a2e'}}}%%
flowchart LR
    subgraph "Data Sources"
        M[Envoy Metrics<br/>Prometheus]
        L[Envoy Access Logs<br/>JSON]
        T[Distributed Traces<br/>OpenTelemetry]
    end

    subgraph "Collection"
        P[Prometheus]
        J[Jaeger / Tempo]
        K[Kafka Buffer]
    end

    subgraph "Storage"
        TSDB[(Prometheus TSDB)]
        S3[(Object Storage)]
    end

    subgraph "Visualization"
        G[Grafana Dashboards]
        A[Alertmanager]
    end

    M --> P
    L --> K
    T --> J
    P --> TSDB
    K --> S3
    J --> S3
    TSDB --> G
    TSDB --> A
```

### Metrics (RED Method)

| Metric | Type | Labels |
|--------|------|--------|
| `istio_requests_total` | Counter | `source`, `destination`, `response_code` |
| `istio_request_duration_milliseconds` | Histogram | `source`, `destination` |
| `istio_request_bytes` | Histogram | `source`, `destination` |
| `istio_response_bytes` | Histogram | `source`, `destination` |
| `istio_tcp_connections_opened_total` | Counter | `source`, `destination` |

### Tracing

- **Sampler**: 10% default, 100% for errors
- **Propagation**: W3C Trace Context (`traceparent` header)
- **Span Tags**: `service.name`, `k8s.pod.name`, `k8s.namespace`, `http.status_code`

### Alerting Rules

| Alert | Condition | Severity |
|-------|-----------|----------|
| HighErrorRate | `rate(5xx) > 5%` for 5m | critical |
| HighLatency | `p99 > 500ms` for 5m | warning |
| PodCrashLooping | `restart_count > 3` in 10m | warning |
| CertExpiring | `cert_expiry < 7d` | warning |

---

## 5. Deployment

```mermaid
%%{init: {'theme':'dark', 'themeVariables': {'primaryColor':'#1a1a2e','primaryTextColor':'#e0e0e0','lineColor':'#4fc3f7','primaryBorderColor':'#4fc3f7','clusterBkg':'#16213e','clusterBorder':'#0f3460','edgeLabelBackground':'#1a1a2e'}}}%%
flowchart LR
    subgraph "Build"
        CI[CI Pipeline] -->|build| Image[Container Image]
        Image -->|push| Registry[Registry]
    end

    subgraph "GitOps"
        Git[Git Repo<br/>Manifests] -->|sync| Argo[ArgoCD]
        Argo -->|apply| K8s[K8s API]
    end

    subgraph "Mesh Config"
        MC[Mesh Config<br/>IstioOperator] -->|apply| Istiod
        VS[VirtualService] -->|apply| Istiod
        DR[DestinationRule] -->|apply| Istiod
    end

    subgraph "Runtime"
        K8s -->|create| Pod[Pod + Sidecar]
        Pod -->|inject| Envoy[Envoy Sidecar]
        Istiod -.->|xDS| Envoy
    end

    Registry --> Argo
    Git --> Argo
    MC --> K8s
    VS --> K8s
    DR --> K8s
```

### Deployment Stages

| Stage | Strategy | Mesh Config |
|-------|----------|-------------|
| **Dev** | Direct push | Permissive mTLS, no auth |
| **Staging** | GitOps sync | STRICT mTLS, JWT auth |
| **Canary** | Argo Rollouts | 5% → 25% → 50% → 100% |
| **Production** | Blue/Green | STRICT mTLS, full auth + authz |

### Sidecar Injection

```yaml
# Namespace label enables auto-injection
apiVersion: v1
kind: Namespace
metadata:
  name: apex-services
  labels:
    istio-injection: enabled
```

### Resource Budgets

| Resource | Request | Limit |
|----------|---------|-------|
| Envoy Sidecar CPU | 100m | 500m |
| Envoy Sidecar Memory | 128Mi | 256Mi |
| Istiod CPU | 500m | 2000m |
| Istiod Memory | 512Mi | 2Gi |

### Upgrade Procedure

1. **Istiod upgrade**: Rolling update; new pods serve xDS to new sidecars
2. **Sidecar upgrade**: Triggered by pod restart; `istioctl proxy-status` verifies sync
3. **Rollback**: `kubectl rollout undo` for control plane; restart pods for sidecars
