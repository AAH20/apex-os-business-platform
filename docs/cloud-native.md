# Cloud-Native Strategy

## 1. Cloud-Native Principles

- **Microservices**: Decompose the platform into loosely coupled, independently deployable services aligned with business domains.
- **Immutable Infrastructure**: Treat servers as disposable; never patch in place. Rebuild and redeploy from versioned artifacts.
- **Declarative Configuration**: Define desired state in code (YAML/JSON). Systems converge to that state automatically.
- **Resilience by Design**: Assume failures happen. Design for graceful degradation, retries with backoff, and circuit breakers.
- **API-First**: Every service exposes well-documented, versioned APIs. Internal communication is contract-driven.
- **Stateless Services**: Keep application state external to the process. Store sessions, caches, and data in dedicated stores.
- **Observability-Driven Development**: Build with logging, metrics, and tracing from day one — not as an afterthought.
- **Shift-Left Security**: Embed security into CI/CD pipelines. Scan images, dependencies, and IaC templates before deployment.
- **GitOps**: Use Git as the single source of truth for infrastructure and application state. All changes are pull-request driven.
- **Portability**: Avoid vendor lock-in where practical. Use open standards and abstract cloud-specific services behind interfaces.

## 2. Containerization Strategy

### Base Images
- Use minimal, distroless, or slim base images (e.g., `distroless`, `alpine`) to reduce attack surface and image size.
- Pin base image digests for reproducibility. Never use `latest` tags in production.
- Maintain a small set of approved base images per language/runtime.

### Image Build
- Multi-stage builds: separate build-time dependencies from runtime artifacts.
- Leverage layer caching: order Dockerfile instructions from least to most frequently changing.
- Scan images for CVEs in CI. Block merges on critical vulnerabilities.
- Sign images with Cosign or Notary. Verify signatures at deploy time.

### Runtime
- Run containers as non-root users. Set `readOnlyRootFilesystem: true` where possible.
- Drop all Linux capabilities and add back only those required.
- Set resource requests and limits for CPU and memory on every container.
- Use `distroless` or scratch-based images for Go/Rust services; JRE slim images for Java.

### Registry
- Use a private container registry (ECR, GCR, ACR, or self-hosted Harbor).
- Enforce immutable tags. Retain images for rollback windows.
- Replicate images across regions for multi-region deployments.

## 3. Orchestration Strategy

### Kubernetes as the Control Plane
- Deploy managed Kubernetes (EKS, GKE, AKS) or self-hosted clusters with Kubeadm/Rancher.
- Separate workloads by namespace per environment (dev, staging, production) and per domain.
- Use node pools / node groups to isolate workloads by resource profile (CPU-optimized, memory-optimized, GPU).

### Workload Management
- All services run as Deployments with `replicas >= 2` for high availability.
- Use StatefulSets only for stateful workloads (databases, message brokers) with persistent volume claims.
- Define PodDisruptionBudgets to ensure voluntary disruptions never drop below minimum available replicas.
- Use HorizontalPodAutoscaler (HPA) based on CPU, memory, or custom metrics (queue depth, request rate).
- Use VerticalPodAutoscaler (VPA) in recommendation mode to right-size resource requests.

### Scheduling & Placement
- Use `podAntiAffinity` to spread replicas across nodes and availability zones.
- Apply `tolerations` and `taints` to dedicate node pools to specific workload classes.
- Use `topologySpreadConstraints` for zone-aware distribution.

### Configuration & Secrets
- Externalize configuration via ConfigMaps and Secrets. Never bake config into images.
- Use External Secrets Operator to sync secrets from cloud KMS / Vault into Kubernetes Secrets.
- Rotate secrets automatically and on a defined schedule.

### Networking
- Use a CNI plugin that supports Network Policies (Calico, Cilium).
- Default-deny all ingress/egress. Allow only explicitly required traffic between namespaces.
- Use Ingress Controllers (NGINX, Traefik, or cloud-native ALB/NLB) with TLS termination.
- Use Gateway API for advanced traffic management (canary, blue-green, weighted routing).

## 4. Service Mesh

### Why a Service Mesh
- Provides mTLS, traffic management, and deep observability without application code changes.
- Offloads cross-cutting concerns (retries, timeouts, circuit breaking) from service code.

### Mesh Selection
- **Istio**: Full-featured, mature, larger resource footprint. Best for complex multi-cluster environments.
- **Linkerd**: Lightweight, simpler, lower operational overhead. Best for teams prioritizing simplicity.
- **Consul Connect**: Good fit for hybrid environments with non-Kubernetes workloads.

### mTLS & Security
- Enable STRICT mTLS mode. All service-to-service traffic is encrypted and authenticated.
- Define `AuthorizationPolicy` to enforce which services can communicate with which.
- Use `PeerAuthentication` to enforce mesh-wide TLS policies.

### Traffic Management
- Use `VirtualService` and `DestinationRule` for canary releases, A/B testing, and blue-green deployments.
- Configure automatic retries with exponential backoff and jitter.
- Set explicit timeouts on all service calls. Fail fast rather than cascade.
- Use `fault injection` in staging to test resilience (chaos engineering).

### Multi-Cluster
- Use a flat network model or mesh federation for cross-cluster service discovery.
- Ensure consistent identity and trust domains across clusters.

## 5. Observability

### Three Pillars
1. **Metrics**: Quantitative system health data (request rate, error rate, latency, resource utilization).
2. **Logs**: Structured, timestamped events with correlation IDs.
3. **Traces**: End-to-end request flow across service boundaries.

### Metrics
- Use Prometheus for scraping and storing time-series data.
- Define SLOs/SLIs for every critical service (availability, latency, error rate).
- Alert on SLO burn rate, not just static thresholds.
- Use Grafana for dashboards. Build per-service and per-domain views.

### Logging
- Emit structured JSON logs to stdout. Let the log collector (Fluent Bit, Fluentd, Vector) handle shipping.
- Centralize logs in Elasticsearch, Loki, or a cloud-native solution (CloudWatch, Stackdriver).
- Include `trace_id`, `span_id`, `service_name`, and `environment` in every log entry.
- Set retention policies based on compliance and debugging needs (hot: 7 days, warm: 30 days, cold: 1 year).

### Tracing
- Use OpenTelemetry as the standard for instrumentation.
- Export traces to Jaeger, Tempo, or a vendor solution (Datadog, Honeycomb).
- Sample traces: 100% for errors, configurable rate for success paths (e.g., 10%).
- Propagate trace context across all service boundaries (HTTP headers, message attributes).

### Alerting
- Route alerts to PagerDuty, Opsgenie, or Slack with clear severity levels (P1–P4).
- Every alert must be actionable. If it doesn't require a response, it's a dashboard, not an alert.
- Maintain runbooks for every alert. Link them directly in the alert payload.

### Continuous Profiling
- Use Parca, Pyroscope, or cloud-native profiling to continuously collect CPU and memory profiles.
- Identify hot paths and memory leaks without waiting for incidents.

### Chaos Engineering
- Regularly run chaos experiments (kill pods, inject latency, exhaust memory) in staging.
- Use LitmusChaos or Gremlin to automate experiments.
- Validate that observability catches injected failures before they reach production.
