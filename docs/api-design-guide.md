# API Design Guide

## 1. REST API Design Principles

- **Statelessness**: Each request must contain all information needed to process it. No server-side session state.
- **Resource-oriented**: Model APIs around resources (nouns), not actions (verbs).
- **Uniform interface**: Use standard HTTP methods (GET, POST, PUT, PATCH, DELETE) consistently.
- **Representation independence**: Clients interact with representations (JSON), not internal data models.
- **HATEOAS (where practical)**: Include links to related resources and available actions in responses.
- **Versioning**: Use URL path versioning (`/v1/`) or header versioning (`Accept: application/vnd.api+json;version=1`).
- **Idempotency**: PUT and DELETE must be idempotent. POST may use idempotency keys for safe retries.
- **Content negotiation**: Support `Accept` and `Content-Type` headers; default to `application/json`.
- **HTTPS only**: All endpoints must be served over TLS in production.

## 2. Resource Naming Conventions

- **Use plural nouns**: `/users`, `/orders`, `/products` — not `/user`, `/order`.
- **Use kebab-case for multi-word paths**: `/order-items`, `/shipping-addresses`.
- **Nest for relationships**: `/users/{id}/orders`, `/orders/{id}/items`.
- **Avoid verbs in paths**: Use HTTP methods instead of `/getUsers`, `/createOrder`.
- **Use query parameters for filtering/sorting**: `/orders?status=pending&sort=-created_at`.
- **Keep paths shallow**: Prefer `/users/{id}/orders` over `/organizations/{orgId}/users/{userId}/orders`.
- **Use consistent casing**: All lowercase in paths; camelCase or snake_case in JSON fields.
- **Avoid file extensions**: Use `Accept` header, not `/users.json`.
- **Use UUIDs or opaque IDs**: Avoid exposing sequential integer IDs when possible.

## 3. Error Handling Patterns

### Standard Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "message": "Must be a valid email address"
      }
    ],
    "request_id": "req_abc123",
    "timestamp": "2026-10-02T12:00:00Z"
  }
}
```

### HTTP Status Code Usage

| Code | Usage |
|------|-------|
| 400 | Malformed request or validation failure |
| 401 | Missing or invalid authentication |
| 403 | Authenticated but not authorized |
| 404 | Resource not found |
| 409 | Conflict (e.g., duplicate resource) |
| 422 | Semantic validation errors |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
| 503 | Service temporarily unavailable |

### Guidelines

- Use standard HTTP status codes correctly; don't return 200 for errors.
- Provide a machine-readable `code` for programmatic handling.
- Include a human-readable `message` for debugging.
- Add `details` array for field-level validation errors.
- Include `request_id` for traceability and support correlation.
- Log full error details server-side; return safe messages to clients.
- Never expose stack traces, internal paths, or sensitive data in responses.

## 4. Pagination Strategies

### Cursor-Based Pagination (Recommended for large datasets)

```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTAwfQ==",
    "has_more": true,
    "limit": 50
  }
}
```

- Use for large, frequently changing datasets.
- Stable under concurrent inserts/deletes.
- Opaque cursor encoding (base64 of offset or last-seen ID).
- Clients cannot skip pages; they must follow cursors.

### Offset-Based Pagination (For smaller datasets)

```json
{
  "data": [...],
  "pagination": {
    "total": 1000,
    "page": 3,
    "per_page": 25,
    "total_pages": 40
  }
}
```

- Use when total count is needed for UI.
- Simple to implement and understand.
- Performance degrades with large offsets; cap at reasonable limits.

### Guidelines

- Default page size: 25 items. Maximum: 100 items.
- Always include pagination metadata in list responses.
- Use `limit` and `offset` (or `cursor`) query parameters.
- Sort with `sort` parameter: `sort=-created_at` for descending.
- Document sort fields explicitly.
- Return empty `data` array with valid pagination when no results exist.

## 5. Rate Limiting Patterns

### Rate Limit Headers

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1696252800
Retry-After: 60
```

### Strategies

- **Token bucket**: Smooth burst handling; refills at constant rate.
- **Sliding window**: More accurate than fixed window; prevents edge bursts.
- **Fixed window**: Simple but allows 2x burst at window boundaries.

### Guidelines

- Return `429 Too Many Requests` when limit exceeded.
- Include `Retry-After` header with seconds to wait.
- Apply limits per authenticated user, API key, or IP.
- Use tiered limits: free tier, pro tier, enterprise tier.
- Document rate limits in API documentation.
- Implement at API gateway level for consistency.
- Use Redis or similar for distributed rate limit counters.
- Return clear error message when limit is exceeded:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 60 seconds.",
    "retry_after": 60
  }
}
```

- Consider separate limits for different endpoint classes (read vs. write).
- Implement exponential backoff guidance for clients.
- Monitor and alert on rate limit hit rates.
