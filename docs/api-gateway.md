# APEX-OS Business Platform — API Gateway Configuration

> **Version:** 1.0.0 | **Last Updated:** 2026-10-01 | **Gateway:** Kong Gateway 3.x (KIC)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Kong Gateway Configuration](#2-kong-gateway-configuration)
3. [Rate Limiting](#3-rate-limiting)
4. [Authentication](#4-authentication)
5. [Authorization](#5-authorization)
6. [Logging](#6-logging)
7. [Monitoring](#7-monitoring)
8. [Deployment](#8-deployment)
9. [Operations Runbook](#9-operations-runbook)

---

## 1. Architecture Overview

```
                    ┌─────────────────────────────────────┐
                    │       Internet / Clients              │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │    AWS WAF / Cloudflare (Edge)       │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  NGINX Ingress (TLS termination)     │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │   Kong Gateway (KIC) — 3 replicas    │
                    │  ┌────────┐ ┌────────┐ ┌──────────┐ │
                    │  │ Rate   │ │ AuthN/ │ │ Logging &│ │
                    │  │ Limit  │ │ AuthZ  │ │ Monitoring│ │
                    │  └────────┘ └────────┘ └──────────┘ │
                    └──────────────┬──────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
      ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
      │  apex-os-api │    │  apex-os-web │    │ apex-os-     │
      │  :8080       │    │  :80         │    │ worker :8080 │
      └──────────────┘    └──────────────┘    └──────────────┘
```

### Design Principles

| Principle | Implementation |
|---|---|
| **Zero-trust** | mTLS between services; JWT/OAuth2 at the edge |
| **Defense in depth** | WAF → Ingress ACL → Kong rate limiting → AuthN/Z → Service RBAC |
| **Observability** | Structured logs → Loki; metrics → Prometheus; traces → Tempo |
| **High availability** | 3 Kong replicas across AZs; PostgreSQL Multi-AZ; Redis with replica |
| **Declarative** | All Kong config as Kubernetes CRDs / YAML (GitOps-friendly) |

---

## 2. Kong Gateway Configuration

### 2.1 Kong Ingress Controller (KIC) — Helm Values

```yaml
# kong-values.yaml
image:
  repository: kong
  tag: "3.5"

env:
  database: "off"
  declarative_config: /kong_dbless/kong.yml
  log_level: info
  error_log_level: warn
  proxy_access_log: /dev/stdout
  proxy_error_log: /dev/stderr
  admin_access_log: /dev/stdout
  admin_error_log: /dev/stderr
  status_listen: 0.0.0.0:127.0.0.1:8100
  proxy_listen: 0.0.0.0:8000, 0.0.0.0:8443 ssl
  admin_listen: 0.0.0.0:8001, 0.0.0.0:8444 ssl
  cluster_listen: 0.0.0.0:8005

ingressController:
  enabled: true
  installCRDs: false
  log_level: info
  watchNamespaces: []
  env:
    kong_admin_token:
      valueFrom:
        secretKeyRef:
          name: kong-admin-token
          key: token

replicaCount: 3

resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: "2"
    memory: 2Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

podDisruptionBudget:
  enabled: true
  minAvailable: 2

serviceAccount:
  create: true
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/kong-gateway-role

podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8100"
  prometheus.io/path: "/metrics"

proxy:
  enabled: true
  type: LoadBalancer
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"

admin:
  enabled: true
  type: ClusterIP
  http:
    enabled: true
    servicePort: 8001
    containerPort: 8001

status:
  enabled: true
  http:
    enabled: true
    containerPort: 8100

postgresql:
  enabled: false
```

### 2.2 Kong Declarative Configuration (DB-less)

```yaml
# kong.yml — Full declarative configuration
_format_version: "3.0"
_transform: true

# ─── Services ───
services:
  - name: apex-os-api
    url: http://apex-os-api.apex-os-core.svc.cluster.local:8080
    protocol: http
    host: apex-os-api.apex-os-core.svc.cluster.local
    port: 8080
    path: /
    connect_timeout: 60000
    write_timeout: 60000
    read_timeout: 60000
    retries: 5
    tags: [api, core]
    routes:
      - name: api-v1
        paths: [/api/v1]
        strip_path: false
        preserve_host: false
        methods: [GET, POST, PUT, PATCH, DELETE]
        https_redirect_status_code: 426
        regex_priority: 0
        tags: [api, v1]
        plugins:
          - name: rate-limiting
            config:
              minute: 100
              hour: 1000
              day: 10000
              policy: redis
              redis_host: apex-os-redis.apex-os-core.svc.cluster.local
              redis_port: 6379
              redis_timeout: 2000
              fault_tolerant: true
              hide_client_headers: false
          - name: jwt
            config:
              uri_param_names: []
              cookie_names: []
              key_claim_name: iss
              secret_is_base64: false
              claims_to_verify: [exp]
              maximum_expiration: 86400
              run_on_preflight: true
          - name: request-transformer
            config:
              remove:
                headers: [X-Powered-By, Server]
              add:
                headers:
                  - "X-Request-ID:$(uuid)"
                  - "X-Gateway:Kong"
                  - "X-Forwarded-For:$(client_ip)"
          - name: cors
            config:
              origins: ["https://apex-os.example.com", "https://app.apex-os.example.com"]
              methods: [GET, POST, PUT, PATCH, DELETE, OPTIONS]
              headers: [Authorization, Content-Type, X-Request-ID, X-API-Key]
              exposed_headers: [X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining]
              credentials: true
              max_age: 3600
              preflight_continue: false
      - name: api-health
        paths: [/api/health]
        strip_path: false
        methods: [GET]
        tags: [api, health]
        plugins:
          - name: request-transformer
            config:
              remove:
                headers: [Authorization, Cookie]

  - name: apex-os-web
    url: http://apex-os-web.apex-os-core.svc.cluster.local:80
    protocol: http
    host: apex-os-web.apex-os-core.svc.cluster.local
    port: 80
    path: /
    connect_timeout: 60000
    write_timeout: 60000
    read_timeout: 60000
    retries: 3
    tags: [web, frontend]
    routes:
      - name: web-root
        paths: [/]
        strip_path: false
        preserve_host: false
        methods: [GET, HEAD]
        tags: [web]
        plugins:
          - name: rate-limiting
            config:
              minute: 200
              hour: 2000
              day: 20000
              policy: redis
              redis_host: apex-os-redis.apex-os-core.svc.cluster.local
              redis_port: 6379
              redis_timeout: 2000
              fault_tolerant: true
              hide_client_headers: false
          - name: cors
            config:
              origins: ["https://apex-os.example.com"]
              methods: [GET, HEAD, OPTIONS]
              headers: [Accept, Content-Type]
              credentials: true
              max_age: 3600

  - name: apex-os-worker
    url: http://apex-os-worker.apex-os-core.svc.cluster.local:8080
    protocol: http
    host: apex-os-worker.apex-os-core.svc.cluster.local
    port: 8080
    path: /
    connect_timeout: 60000
    write_timeout: 60000
    read_timeout: 60000
    retries: 3
    tags: [worker, internal]
    routes:
      - name: worker-internal
        paths: [/internal/worker]
        strip_path: false
        methods: [GET, POST]
        tags: [worker, internal]
        plugins:
          - name: key-auth
            config:
              key_names: [X-Internal-API-Key]
              hide_credentials: true
              run_on_preflight: true
          - name: ip-restriction
            config:
              allow: [10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16]
              deny: []

# ─── Consumers ───
consumers:
  - username: web-frontend
    custom_id: web-frontend-001
    tags: [consumer, web]
    jwt_secrets:
      - algorithm: RS256
        rsa_public_key: |
          -----BEGIN PUBLIC KEY-----
          MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
          -----END PUBLIC KEY-----
        key: "https://auth.apex-os.example.com"
        issuer: "https://auth.apex-os.example.com"
        audience: [apex-os-api]
    acls:
      - group: web-users

  - username: mobile-app
    custom_id: mobile-app-001
    tags: [consumer, mobile]
    jwt_secrets:
      - algorithm: RS256
        rsa_public_key: |
          -----BEGIN PUBLIC KEY-----
          MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
          -----END PUBLIC KEY-----
        key: "https://auth.apex-os.example.com"
        issuer: "https://auth.apex-os.example.com"
        audience: [apex-os-api]
    acls:
      - group: mobile-users

  - username: partner-api
    custom_id: partner-api-001
    tags: [consumer, partner]
    keyauth_credentials:
      - key: "PARTNER-API-KEY-2026"
    acls:
      - group: partners

  - username: internal-worker
    custom_id: internal-worker-001
    tags: [consumer, internal]
    keyauth_credentials:
      - key: "INTERNAL-WORKER-KEY-2026"
    acls:
      - group: internal

# ─── ACL Groups ───
acls:
  - {consumer: web-frontend, group: web-users}
  - {consumer: mobile-app, group: mobile-users}
  - {consumer: partner-api, group: partners}
  - {consumer: internal-worker, group: internal}

# ─── Global Plugins ───
plugins:
  - name: prometheus
    config:
      per_consumer: true
      status_code_metrics: true
      latency_metrics: true
      bandwidth_metrics: true
      upstream_health_metrics: true

  - name: correlation-id
    config:
      header_name: X-Request-ID
      generator: uuid
      echo_downstream: true

  - name: bot-detection
    config:
      deny: ["curl/", "PostmanRuntime/", "python-requests/", "Go-http-client/"]

  - name: request-size-limiting
    config:
      allowed_payload_size: 50
      size_unit: megabyte
      require_content_length: true

  - name: file-log
    config:
      path: /dev/stdout
      reopen: false

  - name: http-log
    config:
      http_endpoint: http://loki-gateway.apex-os-monitoring.svc.cluster.local:3100/loki/api/v1/push
      method: POST
      timeout: 10000
      keepalive: 60000
      content_type: application/json
      flush_timeout: 2
      retry_count: 3
      queue_size: 1000
      queue_timeout: 5
```

---

## 3. Rate Limiting

### 3.1 Strategy

| Layer | Mechanism | Scope |
|---|---|---|
| Edge (WAF) | AWS WAF rate-based rules | Per-IP, per-URI |
| Ingress | NGINX `limit_req` | Per-IP |
| Kong route | `rate-limiting` plugin | Per-consumer, per-route |
| Kong global | `response-ratelimiting` | Per-consumer fallback |
| Service | Application-level | Per-user, per-tenant |

### 3.2 Rate Limit Tiers

| Consumer | Minute | Hour | Day | Burst |
|---|---|---|---|---|
| web-frontend | 100 | 1,000 | 10,000 | 20 |
| mobile-app | 100 | 1,000 | 10,000 | 20 |
| partner-api | 30 | 300 | 3,000 | 10 |
| internal-worker | 600 | 6,000 | 60,000 | 100 |
| Anonymous (health) | 10 | 100 | 1,000 | 5 |

### 3.3 Kong Rate Limiting Configuration

```yaml
# Per-route rate limiting (applied as route plugin)
plugins:
  - name: rate-limiting
    config:
      minute: 100
      hour: 1000
      day: 10000
      policy: redis
      redis_host: apex-os-redis.apex-os-core.svc.cluster.local
      redis_port: 6379
      redis_timeout: 2000
      redis_database: 0
      fault_tolerant: true
      hide_client_headers: false
      redis_ssl: false
      redis_ssl_verify: false
      header_name: X-RateLimit-Limit
      retry_after_header: true
```

### 3.4 NGINX Ingress Rate Limiting

```yaml
# Ingress annotations
metadata:
  annotations:
    nginx.ingress.kubernetes.io/limit-rps: "10"
    nginx.ingress.kubernetes.io/limit-connections: "5"
    nginx.ingress.kubernetes.io/limit-burst-multiplier: "3"
    nginx.ingress.kubernetes.io/limit-rate: "100k"
    nginx.ingress.kubernetes.io/limit-rate-after: "1m"
```

### 3.5 Rate Limit Response Headers

When a rate limit is exceeded, Kong returns:

```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit-Minute: 100
X-RateLimit-Remaining-Minute: 0
X-RateLimit-Reset-Minute: 45
Retry-After: 45
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

---

## 4. Authentication

### 4.1 Authentication Methods

| Method | Use Case | Plugin |
|---|---|---|
| **JWT (RS256)** | Web/Mobile SPA, API clients | `jwt` |
| **OAuth2 / OIDC** | Third-party integrations | `openid-connect` |
| **Key Auth** | Server-to-server, partners | `key-auth` |
| **mTLS** | Internal service-to-service | `mtls-auth` |
| **Session** | Browser-based admin | `session` |

### 4.2 JWT Configuration

```yaml
plugins:
  - name: jwt
    config:
      uri_param_names: []
      cookie_names: []
      key_claim_name: iss
      secret_is_base64: false
      claims_to_verify: [exp]
      maximum_expiration: 86400
      run_on_preflight: true
```

**JWT Claims Structure:**

```json
{
  "iss": "https://auth.apex-os.example.com",
  "sub": "user-12345",
  "aud": "apex-os-api",
  "exp": 1735689600,
  "iat": 1735603200,
  "scope": ["read:orders", "write:orders"],
  "org_id": "org-001",
  "role": "admin"
}
```

### 4.3 Key Auth Configuration

```yaml
plugins:
  - name: key-auth
    config:
      key_names: [X-Internal-API-Key, apikey]
      hide_credentials: true
      run_on_preflight: true
```

### 4.4 mTLS Configuration (Internal Services)

```yaml
# Kong cluster certificate for mTLS
volumes:
  - name: kong-cluster-cert
    secret:
      secretName: kong-cluster-tls

env:
  cluster_cert: /kong/tls/cluster.crt
  cluster_cert_key: /kong/tls/cluster.key
  cluster_ca_cert: /kong/tls/ca.crt
  ssl_verify_depth: 2
```

### 4.5 OAuth2 / OIDC (Future)

```yaml
plugins:
  - name: openid-connect
    config:
      issuer: "https://auth.apex-os.example.com/.well-known/openid-configuration"
      client_id: "kong-gateway"
      client_secret: "${OIDC_CLIENT_SECRET}"
      redirect_uri: "https://apex-os.example.com/api/v1/callback"
      scopes: ["openid", "profile", "email"]
      bearer_only: false
      ssl_verify: false
      consumer_claim: ["sub"]
      credential_claim: ["sub"]
```

---

## 5. Authorization

### 5.1 Authorization Model

```
┌─────────────────────────────────────────────────────────┐
│                    Authorization Flow                     │
│                                                          │
│  Request → JWT/Key Auth → ACL Group → Route Permission   │
│              ↓              ↓              ↓              │
│         Consumer      Group Membership   Service ACL     │
│         Identity      (web-users,        (read/write)    │
│                       partners,                          │
│                       internal)                          │
└─────────────────────────────────────────────────────────┘
```

### 5.2 ACL Groups

| Group | Consumers | Access |
|---|---|---|
| `web-users` | web-frontend | Read/write own resources |
| `mobile-users` | mobile-app | Read/write own resources |
| `partners` | partner-api | Read-only shared resources |
| `internal` | internal-worker | Full internal access |

### 5.3 ACL Configuration

```yaml
acls:
  - {consumer: web-frontend, group: web-users}
  - {consumer: mobile-app, group: mobile-users}
  - {consumer: partner-api, group: partners}
  - {consumer: internal-worker, group: internal}
```

### 5.4 Route-Level Authorization

```yaml
# Partner API — read-only access
routes:
  - name: partner-orders
    paths: [/api/v1/orders]
    methods: [GET]
    plugins:
      - name: jwt
        config: {}
      - name: acl
        config:
          allow: [partners]
          hide_groups_header: true

# Internal worker — full access
routes:
  - name: worker-admin
    paths: [/internal/worker]
    methods: [GET, POST, PUT, DELETE]
    plugins:
      - name: key-auth
        config: {}
      - name: acl
        config:
          allow: [internal]
          hide_groups_header: true
```

### 5.5 Service-Level RBAC (Application)

```yaml
# Kubernetes RBAC for service-to-service
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: apex-os-api-role
  namespace: apex-os-core
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list"]
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

---

## 6. Logging

### 6.1 Log Architecture

```
Kong Gateway → stdout/stderr → Fluent Bit → Loki → Grafana
                                ↓
                          S3 (archive)
```

### 6.2 Log Formats

**Access Log (JSON):**

```json
{
  "timestamp": "2026-10-01T12:00:00.000Z",
  "level": "info",
  "type": "access",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_ip": "203.0.113.42",
  "method": "GET",
  "uri": "/api/v1/orders",
  "status": 200,
  "response_size": 1024,
  "request_size": 0,
  "latency": {
    "request": 45,
    "upstream": 32,
    "kong": 13
  },
  "consumer": "web-frontend",
  "service": "apex-os-api",
  "route": "api-v1",
  "user_agent": "Mozilla/5.0...",
  "tls_version": "TLSv1.3",
  "tls_cipher": "TLS_AES_256_GCM_SHA384"
}
```

**Error Log (JSON):**

```json
{
  "timestamp": "2026-10-01T12:00:00.000Z",
  "level": "error",
  "type": "error",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "rate limiting exceeded",
  "plugin": "rate-limiting",
  "consumer": "partner-api",
  "route": "partner-orders",
  "status": 429
}
```

### 6.3 Kong Log Plugins

```yaml
plugins:
  # File log → stdout (picked up by Fluent Bit)
  - name: file-log
    config:
      path: /dev/stdout
      reopen: false

  # HTTP log → Loki
  - name: http-log
    config:
      http_endpoint: http://loki-gateway.apex-os-monitoring.svc.cluster.local:3100/loki/api/v1/push
      method: POST
      timeout: 10000
      keepalive: 60000
      content_type: application/json
      flush_timeout: 2
      retry_count: 3
      queue_size: 1000
      queue_timeout: 5

  # StatsD → Prometheus
  - name: statsd
    config:
      host: statsd-exporter.apex-os-monitoring.svc.cluster.local
      port: 9125
      metrics:
        - {name: request_count, stat_type: counter, sample_rate: 1}
        - {name: request_latency, stat_type: timer}
        - {name: upstream_latency, stat_type: timer}
        - {name: kong_latency, stat_type: timer}
        - {name: status_count, stat_type: counter, sample_rate: 1}
        - {name: bandwidth, stat_type: counter, sample_rate: 1}
        - {name: unique_users, stat_type: set}
```

### 6.4 Fluent Bit Configuration

```yaml
# fluent-bit-config.yaml
service:
  flush: 1
  log_level: info
  parsers_file: parsers.conf

pipeline:
  inputs:
    - name: tail
      path: /var/log/kong/access.log
      parser: json
      tag: kong.access
      refresh_interval: 5
      mem_buf_limit: 50MB

    - name: tail
      path: /var/log/kong/error.log
      parser: json
      tag: kong.error
      refresh_interval: 5
      mem_buf_limit: 50MB

  filters:
    - name: kubernetes
      match: kong.*
      kube_url: https://kubernetes.default.svc:443
      kube_ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
      kube_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
      merge_log: true
      keep_log: false
      k8s-logging.parser: on
      k8s-logging.exclude: off

    - name: nest
      match: kong.*
      operation: lift
      nested_under: kubernetes
      add_prefix: k8s_

    - name: record_modifier
      match: kong.*
      record:
        cluster: apex-os-prod
        platform: apex-os

  outputs:
    - name: loki
      match: kong.*
      host: loki-gateway.apex-os-monitoring.svc.cluster.local
      port: 3100
      uri: /loki/api/v1/push
      labels:
        job: kong-gateway
        cluster: apex-os-prod
      line_format: json
      drop_single_key: true

    - name: s3
      match: kong.error
      bucket: apex-os-logs
      region: us-east-1
      total_file_size: 100M
      s3_key_format: /kong/$TAG/%Y/%m/%d/%H/%M/%S/$UUID.log
      compression: gzip
      store_dir: /tmp/fluent-bit/s3
```

### 6.5 Log Retention

| Destination | Retention | Purpose |
|---|---|---|
| Loki | 30 days | Real-time search, debugging |
| S3 | 1 year | Compliance, audit |
| CloudWatch | 90 days | Alerting, metrics |

---

## 7. Monitoring

### 7.1 Monitoring Stack

```
Kong Gateway → Prometheus → Grafana
                    ↓
              Alertmanager → PagerDuty/Slack
                    ↓
              Loki (logs) → Grafana
                    ↓
              Tempo (traces) → Grafana
```

### 7.2 Prometheus ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: kong-gateway
  namespace: kong
  labels:
    release: prometheus
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: kong
  namespaceSelector:
    matchNames:
      - kong
  endpoints:
    - port: status
      path: /metrics
      interval: 15s
      scrapeTimeout: 10s
      honorLabels: true
      metricRelabelings:
        - sourceLabels: [__name__]
          regex: 'kong_(.+)'
          targetLabel: component
          replacement: 'kong'
```

### 7.3 Key Metrics

| Metric | Type | Labels | Alert Threshold |
|---|---|---|---|
| `kong_http_requests_total` | Counter | service, route, code | — |
| `kong_http_request_duration_ms` | Histogram | service, route, le | p99 > 500ms |
| `kong_upstream_latency_ms` | Histogram | service, le | p99 > 200ms |
| `kong_kong_latency_ms` | Histogram | le | p99 > 50ms |
| `kong_bandwidth_bytes` | Counter | service, direction | — |
| `kong_nginx_connections` | Gauge | state | > 10,000 |
| `kong_rate_limiting_exceeded` | Counter | consumer, route | > 10/min |
| `kong_upstream_health` | Gauge | service, upstream | < 1 |

### 7.4 Grafana Dashboard (Key Panels)

```json
{
  "dashboard": {
    "title": "APEX-OS API Gateway",
    "panels": [
      {
        "title": "Request Rate",
        "type": "timeseries",
        "targets": [{
          "expr": "sum(rate(kong_http_requests_total[5m])) by (service, route)"
        }]
      },
      {
        "title": "Error Rate",
        "type": "timeseries",
        "targets": [{
          "expr": "sum(rate(kong_http_requests_total{code=~\"5..\"}[5m])) by (service)"
        }]
      },
      {
        "title": "P99 Latency",
        "type": "timeseries",
        "targets": [{
          "expr": "histogram_quantile(0.99, sum(rate(kong_http_request_duration_ms_bucket[5m])) by (le, service))"
        }]
      },
      {
        "title": "Rate Limit Hits",
        "type": "timeseries",
        "targets": [{
          "expr": "sum(rate(kong_rate_limiting_exceeded[5m])) by (consumer)"
        }]
      },
      {
        "title": "Active Connections",
        "type": "gauge",
        "targets": [{
          "expr": "kong_nginx_connections{state=\"active\"}"
        }]
      },
      {
        "title": "Upstream Health",
        "type": "stat",
        "targets": [{
          "expr": "kong_upstream_health"
        }]
      }
    ]
  }
}
```

### 7.5 Prometheus Alert Rules

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: kong-gateway-alerts
  namespace: apex-os-monitoring
spec:
  groups:
    - name: kong-gateway
      rules:
        - alert: KongHighErrorRate
          expr: |
            sum(rate(kong_http_requests_total{code=~"5.."}[5m])) by (service)
            / sum(rate(kong_http_requests_total[5m])) by (service) > 0.05
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "Kong high error rate for {{ $labels.service }}"
            description: "Error rate is {{ $value | humanizePercentage }}"

        - alert: KongHighLatency
          expr: |
            histogram_quantile(0.99, sum(rate(kong_http_request_duration_ms_bucket[5m])) by (le, service)) > 0.5
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Kong P99 latency > 500ms for {{ $labels.service }}"

        - alert: KongRateLimitExceeded
          expr: |
            sum(rate(kong_rate_limiting_exceeded[5m])) by (consumer) > 10
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Rate limit exceeded for {{ $labels.consumer }}"

        - alert: KongUpstreamDown
          expr: kong_upstream_health == 0
          for: 2m
          labels:
            severity: critical
          annotations:
            summary: "Kong upstream {{ $labels.upstream }} is down"

        - alert: KongHighConnections
          expr: kong_nginx_connections{state="active"} > 10000
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Kong active connections > 10,000"
```

### 7.6 Distributed Tracing (Tempo)

```yaml
# OpenTelemetry plugin for Kong
plugins:
  - name: opentelemetry
    config:
      endpoint: http://tempo.apex-os-monitoring.svc.cluster.local:4318
      resource_attributes:
        service.name: kong-gateway
        service.version: "3.5"
        deployment.environment: production
      batch_span_count: 100
      batch_timeout: 5
      connect_timeout: 1000
      send_timeout: 5000
      read_timeout: 5000
```

---

## 8. Deployment

### 8.1 Install Kong Gateway

```bash
# Add Kong Helm repo
helm repo add kong https://charts.konghq.com
helm repo update

# Install Kong Ingress Controller
helm install kong kong/kong \
  --namespace kong \
  --create-namespace \
  -f kong-values.yaml \
  --set ingressController.installCRDs=true

# Apply declarative configuration
kubectl create configmap kong-dbless-config \
  --from-file=kong.yml=kong.yml \
  -n kong \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart Kong to pick up config
kubectl rollout restart deployment/kong-kong -n kong
```

### 8.2 Verify Deployment

```bash
# Check Kong pods
kubectl get pods -n kong

# Check Kong proxy
kubectl port-forward svc/kong-kong-proxy 8000:8000 -n kong
curl -s http://localhost:8000/api/health

# Check Kong admin
kubectl port-forward svc/kong-kong-admin 8001:8001 -n kong
curl -s http://localhost:8001/status | jq .

# Check routes
curl -s http://localhost:8001/routes | jq .

# Check services
curl -s http://localhost:8001/services | jq .

# Check plugins
curl -s http://localhost:8001/plugins | jq .
```

### 8.3 Terraform Integration

```hcl
# terraform/modules/kong/main.tf
resource "helm_release" "kong" {
  name       = "kong"
  repository = "https://charts.konghq.com"
  chart      = "kong"
  namespace  = "kong"
  create_namespace = true

  values = [
    file("${path.module}/values/kong-values.yaml")
  ]

  set {
    name  = "ingressController.installCRDs"
    value = "true"
  }
}

resource "kubectl_manifest" "kong_config" {
  yaml_body = file("${path.module}/values/kong.yml")

  depends_on = [helm_release.kong]
}
```

---

## 9. Operations Runbook

### 9.1 Common Operations

| Task | Command |
|---|---|
| View routes | `curl -s $KONG_ADMIN/routes \| jq .` |
| View services | `curl -s $KONG_ADMIN/services \| jq .` |
| View consumers | `curl -s $KONG_ADMIN/consumers \| jq .` |
| View plugins | `curl -s $KONG_ADMIN/plugins \| jq .` |
| Reload config | `kubectl rollout restart deploy/kong-kong -n kong` |
| View logs | `kubectl logs -n kong -l app.kubernetes.io/name=kong --tail=100` |
| Check metrics | `curl -s $KONG_STATUS/metrics \| grep kong_` |
| Test route | `curl -H "Authorization: Bearer $TOKEN" $PROXY/api/v1/orders` |

### 9.2 Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| 401 Unauthorized | Missing/invalid JWT | Check token expiry, issuer, audience |
| 403 Forbidden | ACL group mismatch | Verify consumer ACL group assignment |
| 429 Too Many Requests | Rate limit exceeded | Check rate limit tier; increase if needed |
| 502 Bad Gateway | Upstream unhealthy | Check upstream pods, service endpoints |
| 504 Gateway Timeout | Upstream timeout | Increase `read_timeout`, check upstream latency |
| 500 Internal Error | Kong config error | Check Kong error logs, validate config |

### 9.3 Security Checklist

- [ ] JWT tokens use RS256 with strong keys
- [ ] JWT `exp` claim verified; max 24h
- [ ] Rate limiting enabled on all public routes
- [ ] ACL groups assigned to all consumers
- [ ] mTLS enabled for internal service communication
- [ ] Bot detection enabled
- [ ] Request size limiting configured
- [ ] Sensitive headers stripped (X-Powered-By, Server)
- [ ] Admin API not exposed publicly
- [ ] Kong admin token stored in Kubernetes Secret
- [ ] Log aggregation to Loki configured
- [ ] Prometheus scraping enabled
- [ ] Alert rules configured and tested
- [ ] S3 log archival configured
- [ ] TLS 1.3 enforced at edge
- [ ] WAF rules active

---

## Appendix A: Environment Variables

| Variable | Description | Example |
|---|---|---|
| `KONG_ADMIN_TOKEN` | Admin API token | `changeme` |
| `OIDC_CLIENT_SECRET` | OAuth2 client secret | `secret` |
| `JWT_RS256_PUBLIC_KEY` | JWT public key | `-----BEGIN PUBLIC KEY-----...` |
| `REDIS_HOST` | Redis host for rate limiting | `apex-os-redis.apex-os-core.svc.cluster.local` |
| `LOKI_ENDPOINT` | Loki push endpoint | `http://loki-gateway...:3100/loki/api/v1/push` |
| `TEMPO_ENDPOINT` | Tempo OTLP endpoint | `http://tempo...:4318` |

## Appendix B: File Reference

| File | Purpose |
|---|---|
| `kong-values.yaml` | Helm values for Kong deployment |
| `kong.yml` | Kong declarative configuration |
| `fluent-bit-config.yaml` | Fluent Bit log shipping config |
| `kong-gateway-alerts.yaml` | Prometheus alert rules |
| `kong-service-monitor.yaml` | Prometheus ServiceMonitor |
| `kong-dashboard.json` | Grafana dashboard JSON |
