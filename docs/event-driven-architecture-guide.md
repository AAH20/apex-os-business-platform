# Event-Driven Architecture Guide

## 1. Event-Driven Patterns

Event-driven architecture (EDA) couples services through events instead of direct calls.

### Core Patterns

- **Event Notification**: Lightweight signal that something happened. Consumers decide what to do.
- **Event-Carried State Transfer**: Event carries full payload so consumers need no callback.
- **Event Sourcing**: State is derived from an append-only event log (see §2).
- **CQRS**: Separate read and write models (see §3).

### When to Use EDA

- Multiple services react to the same occurrence.
- You need loose coupling between producer and consumer.
- Workloads are asynchronous or bursty.
- Audit trails and replayability matter.

### When to Avoid

- Simple CRUD with a single consumer.
- Strong synchronous consistency is required.
- Low-latency request-response is the primary flow.

### Key Principles

- Events are immutable facts, not commands.
- Producers do not know who consumes.
- Consumers are responsible for idempotency.
- Use a message broker (Kafka, RabbitMQ, NATS) for delivery guarantees.

---

## 2. Event Sourcing

Store state as a sequence of events. Current state is a projection of the event log.

### How It Works

1. Every state change is captured as an event.
2. Events are appended to an immutable log.
3. Current state is rebuilt by replaying events.
4. Snapshots optimize replay for long-lived aggregates.

### Benefits

- Complete audit trail.
- Temporal queries (state at any point in time).
- Easy replay for bug fixes or new projections.

### Challenges

- Event schema evolution (upcasting).
- Eventual consistency in projections.
- Storage growth; use snapshots and retention policies.

### Upcasting

When event schemas change, transform old events to new format at read time.

```json
// v1
{ "type": "OrderPlaced", "orderId": "123", "total": 100 }
// v2 (upcast adds currency)
{ "type": "OrderPlaced", "orderId": "123", "total": 100, "currency": "USD" }
```

---

## 3. CQRS (Command Query Responsibility Segregation)

Separate the write model (commands) from the read model (queries).

### Write Side

- Handles commands (CreateOrder, CancelOrder).
- Validates business rules.
- Emits events.
- Optimized for consistency and invariants.

### Read Side

- Handles queries (GetOrder, ListOrders).
- Denormalized, query-optimized views.
- Updated asynchronously from events.
- Can use different databases (Elasticsearch, Redis, materialized views).

### Synchronous vs Asynchronous

| Mode | Consistency | Complexity | Use Case |
|------|-------------|------------|----------|
| Sync | Strong | Low | Simple apps |
| Async | Eventual | High | Scalable, distributed |

### Implementation Tips

- Use a single database with separate tables for small systems.
- Use separate databases for large-scale systems.
- Keep read models rebuildable from the event log.

---

## 4. Saga Pattern

Manage distributed transactions across services without 2PC.

### Orchestration-Based Saga

A central orchestrator coordinates the workflow.

```
OrderService → PaymentService → InventoryService → ShippingService
```

- Orchestrator sends commands and handles responses.
- Compensating actions roll back on failure.
- Easier to debug and monitor.

### Choreography-Based Saga

Services react to events without a central coordinator.

```
OrderPlaced → PaymentProcessed → InventoryReserved → ShipmentCreated
```

- More decoupled.
- Harder to track overall state.
- Risk of cyclic dependencies.

### Compensating Transactions

Each step has a compensating action:

| Step | Compensate |
|------|-----------|
| ReserveInventory | ReleaseInventory |
| ProcessPayment | RefundPayment |
| CreateShipment | CancelShipment |

### Best Practices

- Make every step idempotent.
- Use timeouts and retries with backoff.
- Persist saga state for crash recovery.
- Avoid long-running sagas; split into smaller transactions.

---

## 5. Event Schema Design

Well-designed events are the backbone of an event-driven system.

### Anatomy of an Event

```json
{
  "eventId": "uuid-v4",
  "type": "OrderPlaced",
  "version": 2,
  "aggregateId": "order-123",
  "aggregateType": "Order",
  "timestamp": "2026-10-02T10:00:00Z",
  "correlationId": "trace-abc",
  "causationId": "cmd-xyz",
  "payload": {
    "customerId": "cust-456",
    "items": [{ "sku": "A1", "qty": 2 }],
    "total": 100.00,
    "currency": "USD"
  },
  "metadata": {
    "source": "order-service",
    "userId": "user-789"
  }
}
```

### Field Guidelines

| Field | Purpose |
|-------|---------|
| `eventId` | Unique identifier for deduplication |
| `type` | Event name (past tense for facts) |
| `version` | Schema version for upcasting |
| `aggregateId` | Entity the event belongs to |
| `timestamp` | When the event occurred (UTC) |
| `correlationId` | Traces a full business flow |
| `causationId` | The command/event that caused this |
| `payload` | Event-specific data |
| `metadata` | Contextual information |

### Naming Conventions

- Use past tense for domain events: `OrderPlaced`, `PaymentFailed`.
- Use imperative for commands: `PlaceOrder`, `ProcessPayment`.
- Use consistent casing (PascalCase recommended).

### Schema Evolution Rules

1. **Additive changes are safe**: Add optional fields.
2. **Breaking changes require new version**: Bump `version`.
3. **Never remove fields**: Mark deprecated instead.
4. **Use a schema registry**: Confluent, AWS Glue, or custom.

### Versioning Strategy

- Embed `version` in the event.
- Consumers handle multiple versions.
- Upcast old events at the consumer or middleware level.
- Deprecate old versions with a sunset period.

### Payload Design

- Keep payloads small; reference large data by ID.
- Avoid deep nesting; flatten where possible.
- Use standard data types (ISO 8601 dates, decimal for money).
- Include enough context for consumers to act without callbacks.

---

## Summary

| Pattern | Best For |
|---------|----------|
| Event-Driven | Loose coupling, async workflows |
| Event Sourcing | Audit, temporal queries, replay |
| CQRS | Scale reads independently from writes |
| Saga | Distributed transactions |
| Schema Design | Interoperability, evolution |

Choose patterns based on your consistency, scalability, and complexity requirements. Start simple; add patterns only when justified.
