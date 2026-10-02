# Integration Hub

## 1. Integration Architecture

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart TB
    subgraph External["External Systems"]
        CRM[CRM]
        ERP[ERP]
        WEB[Webhooks]
    end

    subgraph Gateway["API Gateway"]
        APIG[API Gateway]
        AUTH[AuthN/AuthZ]
        RATE[Rate Limiter]
    end

    subgraph Core["Core Platform"]
        SVC[Microservices]
        EB[Event Bus]
        MB[Message Broker]
    end

    subgraph Data["Data Layer"]
        DB[(Database)]
        CACHE[(Cache)]
        QUEUE[Queue]
    end

    CRM --> APIG
    ERP --> APIG
    WEB --> APIG
    APIG --> AUTH
    AUTH --> RATE
    RATE --> SVC
    SVC --> EB
    SVC --> MB
    EB --> SVC
    MB --> QUEUE
    SVC --> DB
    SVC --> CACHE
```

## 2. Integration Patterns

| Pattern | Use Case | Implementation |
|---------|----------|----------------|
| Request-Response | Sync CRUD | REST/gRPC via API Gateway |
| Event-Driven | Async domain events | Event Bus (pub/sub) |
| Message Queue | Reliable task processing | Message Broker (work queues) |
| Webhook | External notifications | HTTP callbacks with retry |
| Saga | Distributed transactions | Orchestration + compensation |
| CQRS | Read/write separation | Separate read models + projections |

### Pattern Selection Guide

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    A[Integration Need] --> B{Sync or Async?}
    B -->|Sync| C{Simple CRUD?}
    B -->|Async| D{Reliable delivery?}
    C -->|Yes| E[Request-Response]
    C -->|No| F[gRPC Streaming]
    D -->|Yes| G[Message Queue]
    D -->|No| H[Event Bus]
```

## 3. API Gateway

- **Routing**: Path-based routing to microservices
- **Authentication**: JWT validation, API key verification
- **Rate Limiting**: Token bucket per client/tenant
- **Transformation**: Request/response mapping, versioning
- **Observability**: Request logging, metrics, distributed tracing

```mermaid
%%{init: {'theme':'dark'}}%%
sequenceDiagram
    participant C as Client
    participant G as API Gateway
    participant S as Service
    participant D as Database

    C->>G: HTTP Request
    G->>G: Auth + Rate Limit
    G->>S: Forward Request
    S->>D: Query
    D-->>S: Result
    S-->>G: Response
    G-->>C: HTTP Response
```

## 4. Message Broker

- **Protocol**: AMQP 1.0 / MQTT
- **Delivery Guarantees**: At-least-once with idempotent consumers
- **Queue Types**: Work queues, pub/sub, dead-letter
- **Scaling**: Consumer groups with partition-aware routing

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    P[Publisher] --> EX[Exchange]
    EX --> Q1[Queue A]
    EX --> Q2[Queue B]
    Q1 --> C1[Consumer 1]
    Q1 --> C2[Consumer 2]
    Q2 --> C3[Consumer 3]
    Q1 --> DLQ[Dead Letter Queue]
```

## 5. Event Bus

- **Transport**: In-process mediator + outbox pattern
- **Event Types**: Domain events, integration events, system events
- **Delivery**: In-memory for same-process, broker-backed for cross-service
- **Ordering**: Per-aggregate ordering guarantees

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart TB
    subgraph Producers
        S1[Service A]
        S2[Service B]
    end

    EB[Event Bus]

    subgraph Consumers
        S3[Service C]
        S4[Service D]
        S5[Service E]
    end

    S1 -->|OrderCreated| EB
    S2 -->|PaymentReceived| EB
    EB -->|OrderCreated| S3
    EB -->|OrderCreated| S4
    EB -->|PaymentReceived| S5
```

### Event Envelope

```json
{
  "id": "uuid-v4",
  "type": "OrderCreated",
  "source": "order-service",
  "timestamp": "2026-10-02T12:00:00Z",
  "correlationId": "uuid-v4",
  "causationId": "uuid-v4",
  "payload": {}
}
```
