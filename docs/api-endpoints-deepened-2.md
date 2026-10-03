# APEX-OS Business Platform — Deepened API Endpoints (Part 2)

> Covers deepened modules: Database, API Gateway, Cache, Notifications, Integration.

---

## 1. Database Endpoints

### 1.1 Query Builder

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/db/query` | Execute a structured query via the query builder |
| POST | `/api/v2/db/query/validate` | Validate a query without executing |
| GET | `/api/v2/db/query/:id` | Get a saved query by ID |
| PUT | `/api/v2/db/query/:id` | Update a saved query |
| DELETE | `/api/v2/db/query/:id` | Delete a saved query |

**POST /api/v2/db/query**

Request:
```json
{
  "table": "orders",
  "select": ["id", "total", "status"],
  "where": [{"field": "status", "op": "eq", "value": "pending"}],
  "orderBy": [{"field": "created_at", "direction": "desc"}],
  "limit": 50,
  "offset": 0
}
```

Response `200 OK`:
```json
{
  "data": [{"id": 101, "total": 299.99, "status": "pending"}],
  "meta": {"count": 1, "limit": 50, "offset": 0, "total": 1}
}
```

Status codes: `200`, `400` (invalid query), `401`, `403`, `404`, `500`.

---

### 1.2 Connection Pooling

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/db/pools` | List all connection pools |
| GET | `/api/v2/db/pools/:name` | Get pool status and metrics |
| POST | `/api/v2/db/pools/:name/scale` | Scale pool min/max connections |
| GET | `/api/v2/db/pools/:name/stats` | Pool utilization stats |

**GET /api/v2/db/pools/:name/stats**

Response `200 OK`:
```json
{
  "pool": "primary",
  "active": 12,
  "idle": 8,
  "waiting": 0,
  "max": 50,
  "min": 5,
  "utilization": 0.24,
  "avg_wait_ms": 3.2
}
```

Status codes: `200`, `401`, `403`, `404`.

---

### 1.3 Read Replicas

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/db/replicas` | List read replicas |
| POST | `/api/v2/db/replicas/:name/promote` | Promote replica to primary |
| GET | `/api/v2/db/replicas/:name/lag` | Replication lag in ms |
| POST | `/api/v2/db/replicas/:name/drain` | Drain replica for maintenance |

**GET /api/v2/db/replicas/:name/lag**

Response `200 OK`:
```json
{"replica": "replica-us-east-1", "lag_ms": 42, "status": "healthy"}
```

Status codes: `200`, `401`, `403`, `404`, `503`.

---

### 1.4 Sharding

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/db/shards` | List shards and their ranges |
| POST | `/api/v2/db/shards/rebalance` | Trigger shard rebalancing |
| GET | `/api/v2/db/shards/:id/keys` | Get shard key distribution |
| POST | `/api/v2/db/shards/split` | Split a shard |

**GET /api/v2/db/shards**

Response `200 OK`:
```json
{
  "shards": [
    {"id": "shard-0", "range": "0-499999", "primary": "db-0", "replicas": ["db-0-r1"]},
    {"id": "shard-1", "range": "500000-999999", "primary": "db-1", "replicas": ["db-1-r1"]}
  ]
}
```

Status codes: `200`, `401`, `403`, `409` (rebalance in progress).

---

### 1.5 Full-Text Search

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/db/search` | Full-text search across indexed tables |
| POST | `/api/v2/db/search/index` | Create/update a full-text index |
| DELETE | `/api/v2/db/search/index/:name` | Drop a full-text index |

**POST /api/v2/db/search**

Request:
```json
{
  "query": "wireless headphones",
  "tables": ["products"],
  "filters": {"category": "electronics"},
  "fuzzy": true,
  "limit": 20
}
```

Response `200 OK`:
```json
{
  "results": [{"id": "p-101", "title": "Wireless Headphones Pro", "score": 0.92}],
  "meta": {"total": 1, "took_ms": 14}
}
```

Status codes: `200`, `400`, `401`, `403`, `500`.

---

## 2. API Gateway Endpoints

### 2.1 GraphQL

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/graphql` | Execute a GraphQL query/mutation |
| GET | `/api/v2/graphql/schema` | Fetch the GraphQL schema (SDL) |
| POST | `/api/v2/graphql/validate` | Validate a GraphQL operation |

**POST /api/v2/graphql**

Request:
```json
{
  "query": "query { orders(limit: 5) { id total status } }",
  "variables": {},
  "operationName": null
}
```

Response `200 OK`:
```json
{"data": {"orders": [{"id": 1, "total": 99.99, "status": "completed"}]}}
```

Status codes: `200`, `400`, `401`, `403`, `429`, `500`.

---

### 2.2 WebSockets

| Method | Path | Description |
|--------|------|-------------|
| WS | `/api/v2/ws` | WebSocket connection for real-time events |
| POST | `/api/v2/ws/broadcast` | Broadcast a message to connected clients |
| GET | `/api/v2/ws/connections` | List active WebSocket connections |

**WS /api/v2/ws** — Client sends:
```json
{"type": "subscribe", "channel": "orders"}
```

Server pushes:
```json
{"type": "event", "channel": "orders", "data": {"orderId": 200, "status": "shipped"}}
```

Status codes: `101` (upgrade), `4001` (server-closed), `4002` (unauthorized).

---

### 2.3 Versioning

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/versions` | List all API versions |
| GET | `/api/versions/:version` | Get version details and deprecation info |
| POST | `/api/versions/deprecate` | Mark a version as deprecated |

**GET /api/versions**

Response `200 OK`:
```json
{
  "versions": [
    {"version": "v1", "status": "deprecated", "eol": "2026-06-01"},
    {"version": "v2", "status": "current", "eol": null}
  ]
}
```

Status codes: `200`, `401`, `404`.

---

### 2.4 Rate Limiting

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/rate-limits` | List rate limit policies |
| POST | `/api/v2/rate-limits` | Create a rate limit policy |
| PUT | `/api/v2/rate-limits/:id` | Update a policy |
| DELETE | `/api/v2/rate-limits/:id` | Delete a policy |
| GET | `/api/v2/rate-limits/:id/usage` | Current usage against a policy |

**POST /api/v2/rate-limits**

Request:
```json
{"name": "burst-limit", "requests": 100, "window": "60s", "scope": "api-key"}
```

Response `201 Created`:
```json
{"id": "rl-1", "name": "burst-limit", "requests": 100, "window": "60s", "scope": "api-key"}
```

Status codes: `200`, `201`, `400`, `401`, `403`, `404`, `409`.

---

### 2.5 OpenAPI

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/openapi.json` | OpenAPI 3.1 spec (JSON) |
| GET | `/api/v2/openapi.yaml` | OpenAPI 3.1 spec (YAML) |
| GET | `/api/v2/docs` | Swagger UI |
| POST | `/api/v2/openapi/validate` | Validate an OpenAPI spec |

**GET /api/v2/openapi.json**

Response `200 OK`:
```json
{
  "openapi": "3.1.0",
  "info": {"title": "APEX-OS API", "version": "2.0.0"},
  "paths": {"/api/v2/orders": {"get": {"summary": "List orders"}}}
}
```

Status codes: `200`, `401`.

---

## 3. Cache Endpoints

### 3.1 Multi-Level Cache

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/cache/:key` | Get a cached value (L1 → L2 → L3) |
| PUT | `/api/v2/cache/:key` | Set a cached value |
| DELETE | `/api/v2/cache/:key` | Invalidate a key across all levels |
| GET | `/api/v2/cache/stats` | Cache hit/miss stats per level |

**PUT /api/v2/cache/:key**

Request:
```json
{"value": {"theme": "dark"}, "ttl": 3600, "levels": ["L1", "L2"]}
```

Response `200 OK`:
```json
{"key": "user:123:prefs", "stored_in": ["L1", "L2"], "ttl": 3600}
```

Status codes: `200`, `400`, `401`, `403`.

---

### 3.2 Cache Invalidation

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/cache/invalidate` | Invalidate by pattern or tags |
| POST | `/api/v2/cache/invalidate/:key` | Invalidate a single key |
| GET | `/api/v2/cache/invalidation-log` | Recent invalidation events |

**POST /api/v2/cache/invalidate**

Request:
```json
{"pattern": "user:*:prefs", "tags": ["preferences", "user-data"]}
```

Response `200 OK`:
```json
{"invalidated": 42, "pattern": "user:*:prefs"}
```

Status codes: `200`, `400`, `401`, `403`.

---

### 3.3 Cache Warming

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/cache/warm` | Warm cache with specified keys |
| GET | `/api/v2/cache/warm/status/:jobId` | Check warming job status |
| POST | `/api/v2/cache/warm/schedule` | Schedule recurring warming |

**POST /api/v2/cache/warm**

Request:
```json
{"keys": ["config:app", "products:featured"], "priority": "high"}
```

Response `202 Accepted`:
```json
{"jobId": "warm-123", "status": "queued", "keys_submitted": 2}
```

Status codes: `202`, `400`, `401`, `403`.

---

### 3.4 Cache Analytics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/cache/analytics` | Hit ratio, eviction rate, latency |
| GET | `/api/v2/cache/analytics/keys` | Top keys by access frequency |
| GET | `/api/v2/cache/analytics/evictions` | Eviction trends |

**GET /api/v2/cache/analytics**

Response `200 OK`:
```json
{
  "hit_ratio": 0.94,
  "eviction_rate": 12,
  "avg_latency_ms": 2.1,
  "total_keys": 150000,
  "memory_used_mb": 512
}
```

Status codes: `200`, `401`, `403`.

---

### 3.5 Redis Operations

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/redis/:command` | Execute a Redis command (restricted) |
| GET | `/api/v2/redis/info` | Redis server info |
| GET | `/api/v2/redis/slowlog` | Slow query log |

**POST /api/v2/redis/:command**

Request:
```json
{"args": ["GET", "user:123:prefs"]}
```

Response `200 OK`:
```json
{"result": "{\"theme\":\"dark\"}"}
```

Status codes: `200`, `400`, `401`, `403`, `405` (command not allowed).

---

## 4. Notification Endpoints

### 4.1 Push Notifications

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/notifications/push` | Send a push notification |
| POST | `/api/v2/notifications/push/batch` | Send batch push notifications |
| GET | `/api/v2/notifications/push/:id/status` | Delivery status of a push |

**POST /api/v2/notifications/push**

Request:
```json
{
  "tokens": ["device-token-1"],
  "title": "Order Shipped",
  "body": "Your order #101 has shipped",
  "data": {"orderId": 101},
  "platform": "fcm"
}
```

Response `200 OK`:
```json
{"sent": 1, "failed": 0, "messageId": "msg-abc"}
```

Status codes: `200`, `400`, `401`, `403`, `502` (provider error).

---

### 4.2 In-App Notifications

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/notifications/in-app` | List in-app notifications for current user |
| POST | `/api/v2/notifications/in-app` | Create an in-app notification |
| PUT | `/api/v2/notifications/in-app/:id/read` | Mark as read |
| DELETE | `/api/v2/notifications/in-app/:id` | Delete a notification |

**GET /api/v2/notifications/in-app**

Response `200 OK`:
```json
{
  "notifications": [
    {"id": "n-1", "title": "Welcome", "read": false, "createdAt": "2026-10-03T10:00:00Z"}
  ],
  "unread_count": 1
}
```

Status codes: `200`, `401`, `404`.

---

### 4.3 Notification Preferences

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/notifications/preferences` | Get user notification preferences |
| PUT | `/api/v2/notifications/preferences` | Update preferences |
| POST | `/api/v2/notifications/preferences/reset` | Reset to defaults |

**PUT /api/v2/notifications/preferences**

Request:
```json
{
  "channels": {"push": true, "email": false, "inApp": true},
  "topics": {"orders": true, "marketing": false}
}
```

Response `200 OK`:
```json
{"channels": {"push": true, "email": false, "inApp": true}, "topics": {"orders": true, "marketing": false}}
```

Status codes: `200`, `400`, `401`.

---

### 4.4 Notification Templates

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/notifications/templates` | List templates |
| POST | `/api/v2/notifications/templates` | Create a template |
| PUT | `/api/v2/notifications/templates/:id` | Update a template |
| DELETE | `/api/v2/notifications/templates/:id` | Delete a template |
| POST | `/api/v2/notifications/templates/:id/render` | Preview render a template |

**POST /api/v2/notifications/templates**

Request:
```json
{
  "name": "order-shipped",
  "subject": "Your order #{{orderId}} has shipped",
  "body": "Hi {{name}}, your order is on its way!",
  "channel": "push"
}
```

Response `201 Created`:
```json
{"id": "tpl-1", "name": "order-shipped", "channel": "push"}
```

Status codes: `200`, `201`, `400`, `401`, `403`, `404`.

---

### 4.5 Notification Analytics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/notifications/analytics` | Delivery/open/click rates |
| GET | `/api/v2/notifications/analytics/campaigns` | Per-campaign performance |
| GET | `/api/v2/notifications/analytics/channels` | Channel comparison |

**GET /api/v2/notifications/analytics**

Response `200 OK`:
```json
{
  "sent": 10000,
  "delivered": 9500,
  "opened": 4200,
  "clicked": 1800,
  "delivery_rate": 0.95,
  "open_rate": 0.44,
  "click_rate": 0.19
}
```

Status codes: `200`, `401`, `403`.

---

## 5. Integration Endpoints

### 5.1 Webhooks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/integrations/webhooks` | List registered webhooks |
| POST | `/api/v2/integrations/webhooks` | Register a webhook |
| PUT | `/api/v2/integrations/webhooks/:id` | Update a webhook |
| DELETE | `/api/v2/integrations/webhooks/:id` | Delete a webhook |
| POST | `/api/v2/integrations/webhooks/:id/test` | Send a test event |
| GET | `/api/v2/integrations/webhooks/:id/deliveries` | Delivery history |

**POST /api/v2/integrations/webhooks**

Request:
```json
{
  "url": "https://example.com/webhook",
  "events": ["order.created", "order.updated"],
  "secret": "whsec_...",
  "active": true
}
```

Response `201 Created`:
```json
{"id": "wh-1", "url": "https://example.com/webhook", "events": ["order.created"], "active": true}
```

Status codes: `200`, `201`, `400`, `401`, `403`, `404`.

---

### 5.2 API Keys

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/integrations/api-keys` | List API keys |
| POST | `/api/v2/integrations/api-keys` | Create an API key |
| PUT | `/api/v2/integrations/api-keys/:id` | Update/revoke an API key |
| DELETE | `/api/v2/integrations/api-keys/:id` | Delete an API key |
| POST | `/api/v2/integrations/api-keys/:id/rotate` | Rotate an API key |

**POST /api/v2/integrations/api-keys**

Request:
```json
{"name": "prod-key", "scopes": ["read:orders", "write:orders"], "expiresIn": "90d"}
```

Response `201 Created`:
```json
{"id": "key-1", "name": "prod-key", "prefix": "ak_live_...", "secret": "ak_live_abc123..."}
```

Status codes: `200`, `201`, `400`, `401`, `403`, `404`.

---

### 5.3 Marketplace

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/integrations/marketplace` | List available integrations |
| GET | `/api/v2/integrations/marketplace/:id` | Get integration details |
| POST | `/api/v2/integrations/marketplace/:id/install` | Install an integration |
| DELETE | `/api/v2/integrations/marketplace/:id` | Uninstall an integration |
| GET | `/api/v2/integrations/marketplace/installed` | List installed integrations |

**GET /api/v2/integrations/marketplace**

Response `200 OK`:
```json
{
  "integrations": [
    {"id": "slack", "name": "Slack", "category": "messaging", "installed": false},
    {"id": "stripe", "name": "Stripe", "category": "payments", "installed": true}
  ]
}
```

Status codes: `200`, `401`, `403`, `404`.

---

### 5.4 Field Mapping

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/integrations/mappings` | List field mappings |
| POST | `/api/v2/integrations/mappings` | Create a field mapping |
| PUT | `/api/v2/integrations/mappings/:id` | Update a mapping |
| DELETE | `/api/v2/integrations/mappings/:id` | Delete a mapping |
| POST | `/api/v2/integrations/mappings/:id/transform` | Test a mapping transform |

**POST /api/v2/integrations/mappings**

Request:
```json
{
  "integration": "stripe",
  "source": "order.total",
  "target": "amount",
  "transform": "cents"
}
```

Response `201 Created`:
```json
{"id": "map-1", "integration": "stripe", "source": "order.total", "target": "amount", "transform": "cents"}
```

Status codes: `200`, `201`, `400`, `401`, `403`, `404`.

---

### 5.5 Integration Analytics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/integrations/analytics` | Usage stats across integrations |
| GET | `/api/v2/integrations/analytics/:id` | Per-integration metrics |
| GET | `/api/v2/integrations/analytics/errors` | Error rates and top failures |

**GET /api/v2/integrations/analytics**

Response `200 OK`:
```json
{
  "total_calls": 50000,
  "success_rate": 0.98,
  "avg_latency_ms": 120,
  "top_integrations": [
    {"id": "stripe", "calls": 30000, "success_rate": 0.99},
    {"id": "slack", "calls": 20000, "success_rate": 0.96}
  ]
}
```

Status codes: `200`, `401`, `403`.

---

*End of deepened API endpoint documentation (Part 2).*
