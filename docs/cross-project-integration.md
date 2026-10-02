# Cross-Project Integration

## 1. Integration Architecture

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    subgraph External["External Systems"]
        A1[CRM]
        A2[ERP]
        A3[Payment Gateway]
    end

    subgraph APEX["APEX-OS Platform"]
        B1[API Gateway]
        B2[Auth Service]
        B3[Event Bus]
        B4[Shared DB]
    end

    subgraph Projects["Business Projects"]
        C1[Project Alpha]
        C2[Project Beta]
        C3[Project Gamma]
    end

    A1 --> B1
    A2 --> B1
    A3 --> B1
    B1 --> B2
    B1 --> B3
    B2 --> B4
    B3 --> C1
    B3 --> C2
    B3 --> C3
    C1 --> B4
    C2 --> B4
    C3 --> B4
```

## 2. Shared Services

| Service | Purpose | Endpoint |
|---------|---------|----------|
| Auth Service | Authentication & authorization | `/auth/*` |
| Event Bus | Async event distribution | `/events/*` |
| Shared DB | Cross-project data store | Internal |
| API Gateway | Rate limiting, routing | `/api/*` |
| Notification | Email, SMS, push alerts | `/notify/*` |
| Audit Log | Compliance & traceability | `/audit/*` |

## 3. Data Flow Between Projects

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant P1 as Project Alpha
    participant EB as Event Bus
    participant P2 as Project Beta
    participant DB as Shared DB

    P1->>EB: publish(order.created)
    EB->>P2: consume(order.created)
    P2->>DB: write(inventory.update)
    DB-->>P2: ack
    P2->>EB: publish(inventory.updated)
    EB->>P1: consume(inventory.updated)
```

## 4. API Contracts

### 4.1 Authentication

```
POST /auth/login
Request:  { "email": "string", "password": "string" }
Response: { "token": "string", "expires_in": 3600 }
```

### 4.2 Event Publishing

```
POST /events/publish
Headers: Authorization: Bearer <token>
Request:  { "topic": "string", "payload": object }
Response: { "event_id": "uuid", "status": "published" }
```

### 4.3 Shared Data Access

```
GET /api/v1/shared-data/{project_id}
Headers: Authorization: Bearer <token>
Response: { "data": array, "meta": { "page": 1, "total": 100 } }
```

### 4.4 Notification

```
POST /notify/send
Headers: Authorization: Bearer <token>
Request:  { "channel": "email|sms|push", "recipient": "string", "message": "string" }
Response: { "notification_id": "uuid", "status": "queued" }
```

## 5. Event-Driven Integration

### 5.1 Event Topics

| Topic | Producer | Consumers |
|-------|----------|-----------|
| `order.created` | Project Alpha | Project Beta, Gamma |
| `inventory.updated` | Project Beta | Project Alpha |
| `payment.processed` | External | All projects |
| `user.registered` | Auth Service | All projects |
| `audit.entry` | All projects | Audit Log |

### 5.2 Event Schema

```json
{
  "event_id": "uuid",
  "topic": "string",
  "timestamp": "ISO8601",
  "source": "project_name",
  "payload": {},
  "metadata": {
    "version": "1.0",
    "trace_id": "uuid"
  }
}
```

### 5.3 Event Flow Diagram

```mermaid
%%{init: {'theme': 'dark'}}%%
graph LR
    E1[order.created] --> EB[Event Bus]
    E2[inventory.updated] --> EB
    E3[payment.processed] --> EB
    EB --> H1[Project Alpha Handler]
    EB --> H2[Project Beta Handler]
    EB --> H3[Project Gamma Handler]
    EB --> H4[Audit Log Handler]
```

### 5.4 Retry & Dead Letter Policy

- Max retries: 3
- Backoff: exponential (1s, 2s, 4s)
- Dead letter queue after max retries
- DLQ retention: 7 days
