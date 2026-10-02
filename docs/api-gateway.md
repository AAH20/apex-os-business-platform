# API Gateway

## 1. Architecture

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    Client[Client Apps] -->|HTTPS| GW[API Gateway]
    GW -->|Route| Auth[Auth Service]
    GW -->|Route| Users[Users API]
    GW -->|Route| Orders[Orders API]
    GW -->|Route| Billing[Billing API]
    GW -->|Route| Notifications[Notifications API]
    Auth -->|Validate| Cache[(Redis Cache)]
    GW -->|Metrics| Mon[Monitoring]
    GW -->|Logs| Log[Log Aggregator]
```

The API Gateway is the single entry point for all client requests. It handles cross-cutting concerns (auth, rate limiting, logging) before routing to backend microservices.

## 2. Routing Strategy

- **Path-based routing**: `/api/v1/users/*` → Users Service, `/api/v1/orders/*` → Orders Service
- **Header routing**: `X-API-Version` header selects service version
- **Weighted routing**: Canary deployments via traffic split (e.g., 95/5)
- **Fallback routing**: Circuit breaker redirects to fallback service on failure

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart TD
    Req[Request] --> Check{Path Match?}
    Check -->|/api/v1/users| U[Users Service]
    Check -->|/api/v1/orders| O[Orders Service]
    Check -->|/api/v1/billing| B[Billing Service]
    Check -->|/api/v1/notifications| N[Notifications Service]
    Check -->|No match| E[404 Not Found]
```

## 3. Rate Limiting

- **Algorithm**: Token bucket per API key
- **Limits**: 1000 req/min default; 100 req/min for unauthenticated
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **Response**: HTTP 429 with `Retry-After` header when exceeded
- **Storage**: Redis-backed distributed counters for multi-instance consistency

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    Req[Request] --> RL{Rate Limit Check}
    RL -->|Under limit| Proxy[Proxy to Service]
    RL -->|Exceeded| Reject[429 Too Many Requests]
    Proxy -->|Response| Client[Client]
    Reject -->|Retry-After| Client
```

## 4. Authentication

- **Method**: JWT (RS256) with short-lived access tokens (15 min) + refresh tokens (7 days)
- **Validation**: Gateway verifies signature, expiry, and issuer before routing
- **API Keys**: Service-to-service auth via API keys with HMAC signing
- **OAuth2**: Third-party integrations use authorization code flow

```mermaid
%%{init: {'theme':'dark'}}%%
sequenceDiagram
    participant C as Client
    participant GW as Gateway
    participant AS as Auth Service
    C->>GW: Request + Bearer Token
    GW->>GW: Verify JWT signature
    GW->>AS: Introspect token (if needed)
    AS-->>GW: Token valid + claims
    GW->>GW: Check scopes/permissions
    GW->>C: 200 OK or 401/403
```

## 5. Monitoring

- **Metrics**: Request rate, latency (p50/p95/p99), error rate, saturation
- **Tracing**: OpenTelemetry with trace IDs propagated across services
- **Logging**: Structured JSON logs with correlation IDs
- **Alerting**: PagerDuty integration for SLO breaches (latency > 500ms p95, error rate > 1%)
- **Dashboards**: Grafana dashboards for real-time traffic and health

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    GW[API Gateway] -->|Metrics| Prom[Prometheus]
    GW -->|Traces| OTel[OpenTelemetry Collector]
    GW -->|Logs| ELK[ELK Stack]
    Prom --> Graf[Grafana Dashboards]
    OTel --> Graf
    ELK --> Graf
    Prom -->|Alerts| PD[PagerDuty]
```
