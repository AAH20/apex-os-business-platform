# APEX-OS Business Platform — CRUD API Reference

## 1. CRUD Endpoints

| Resource | Base Path | Methods |
|----------|-----------|---------|
| Users | `/api/v1/users` | GET, POST, PUT, PATCH, DELETE |
| Organizations | `/api/v1/organizations` | GET, POST, PUT, PATCH, DELETE |
| Projects | `/api/v1/projects` | GET, POST, PUT, PATCH, DELETE |
| Tasks | `/api/v1/tasks` | GET, POST, PUT, PATCH, DELETE |
| Documents | `/api/v1/documents` | GET, POST, PUT, PATCH, DELETE |
| Workflows | `/api/v1/workflows` | GET, POST, PUT, PATCH, DELETE |
| Reports | `/api/v1/reports` | GET, POST, PUT, PATCH, DELETE |
| Notifications | `/api/v1/notifications` | GET, POST, PUT, PATCH, DELETE |
| Roles | `/api/v1/roles` | GET, POST, PUT, PATCH, DELETE |
| Permissions | `/api/v1/permissions` | GET, POST, PUT, PATCH, DELETE |
| Audit Logs | `/api/v1/audit-logs` | GET |
| Settings | `/api/v1/settings` | GET, PUT, PATCH |
| Billing | `/api/v1/billing` | GET, POST, PUT, PATCH, DELETE |
| Integrations | `/api/v1/integrations` | GET, POST, PUT, PATCH, DELETE |
| Teams | `/api/v1/teams` | GET, POST, PUT, PATCH, DELETE |
| Comments | `/api/v1/comments` | GET, POST, PUT, PATCH, DELETE |
| Attachments | `/api/v1/attachments` | GET, POST, DELETE |
| Tags | `/api/v1/tags` | GET, POST, PUT, PATCH, DELETE |
| Sessions | `/api/v1/sessions` | GET, DELETE |
| Webhooks | `/api/v1/webhooks` | GET, POST, PUT, PATCH, DELETE |

---

## 2. CRUD Operations

### Create (POST)
- **Purpose:** Create a new resource instance.
- **Idempotency:** Not idempotent by default; use `Idempotency-Key` header for safe retries.
- **Response:** `201 Created` with the created resource body.
- **Required Headers:** `Content-Type: application/json`, `Authorization: Bearer <token>`

### Read (GET)
- **List:** `GET /api/v1/{resource}` — returns paginated collection.
- **Retrieve:** `GET /api/v1/{resource}/{id}` — returns single resource.
- **Query Params:** `page`, `per_page`, `sort`, `order`, `filter[field]=value`, `include=relation`, `fields=field1,field2`
- **Response:** `200 OK` with resource(s).

### Update (PUT / PATCH)
- **PUT:** Full replacement of resource. All fields required.
- **PATCH:** Partial update. Only modified fields needed.
- **Response:** `200 OK` with updated resource.
- **Optimistic Locking:** Use `If-Match: <etag>` header to prevent lost updates.

### Delete (DELETE)
- **Purpose:** Remove a resource permanently.
- **Soft Delete:** Resources with `deleted_at` field are recoverable within 30 days.
- **Hard Delete:** Use `?permanent=true` for immediate irreversible deletion.
- **Response:** `204 No Content`.

### Bulk Operations
- **Bulk Create:** `POST /api/v1/{resource}/bulk` — array of resources.
- **Bulk Update:** `PATCH /api/v1/{resource}/bulk` — array with `id` + changes.
- **Bulk Delete:** `DELETE /api/v1/{resource}/bulk` — array of IDs.
- **Limits:** Max 100 items per bulk request.

---

## 3. CRUD Examples

### Create a User
```bash
curl -X POST https://api.apex-os.com/api/v1/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-key-123" \
  -d '{
    "email": "jane.doe@example.com",
    "name": "Jane Doe",
    "role": "member",
    "organization_id": "org_abc123"
  }'
```
**Response (201):**
```json
{
  "id": "usr_xyz789",
  "email": "jane.doe@example.com",
  "name": "Jane Doe",
  "role": "member",
  "organization_id": "org_abc123",
  "created_at": "2026-10-03T10:00:00Z",
  "updated_at": "2026-10-03T10:00:00Z"
}
```

### Read Users (List with Filters)
```bash
curl "https://api.apex-os.com/api/v1/users?page=1&per_page=20&sort=created_at&order=desc&filter[role]=member" \
  -H "Authorization: Bearer $TOKEN"
```
**Response (200):**
```json
{
  "data": [ ... ],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

### Read Single User
```bash
curl https://api.apex-os.com/api/v1/users/usr_xyz789 \
  -H "Authorization: Bearer $TOKEN"
```

### Update User (PATCH)
```bash
curl -X PATCH https://api.apex-os.com/api/v1/users/usr_xyz789 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "If-Match: \"a1b2c3\"" \
  -d '{"name": "Jane Smith", "role": "admin"}'
```

### Full Update (PUT)
```bash
curl -X PUT https://api.apex-os.com/api/v1/users/usr_xyz789 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane.smith@example.com",
    "name": "Jane Smith",
    "role": "admin",
    "organization_id": "org_abc123"
  }'
```

### Delete User
```bash
curl -X DELETE https://api.apex-os.com/api/v1/users/usr_xyz789 \
  -H "Authorization: Bearer $TOKEN"
```

### Bulk Create Projects
```bash
curl -X POST https://api.apex-os.com/api/v1/projects/bulk \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '[
    {"name": "Project Alpha", "status": "active"},
    {"name": "Project Beta", "status": "draft"}
  ]'
```

### Bulk Delete Tasks
```bash
curl -X DELETE https://api.v1/tasks/bulk \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ids": ["tsk_001", "tsk_002", "tsk_003"]}'
```

---

## 4. Error Codes

| HTTP Code | Error Code | Description | Resolution |
|-----------|-----------|-------------|------------|
| 400 | `bad_request` | Malformed request body or invalid syntax | Check JSON syntax and field types |
| 401 | `unauthorized` | Missing or invalid authentication | Verify Bearer token is valid and not expired |
| 403 | `forbidden` | Insufficient permissions | Check role/permission assignments |
| 404 | `not_found` | Resource does not exist | Verify resource ID is correct |
| 409 | `conflict` | Resource already exists or version conflict | Use unique values or retry with updated ETag |
| 412 | `precondition_failed` | ETag mismatch (optimistic locking) | Re-fetch resource and retry with current ETag |
| 422 | `validation_error` | Field validation failed | Check `errors` array for field-level details |
| 429 | `rate_limit_exceeded` | Too many requests | Implement exponential backoff; check `Retry-After` header |
| 500 | `internal_server_error` | Unexpected server error | Retry with backoff; contact support if persistent |
| 503 | `service_unavailable` | Service temporarily down | Retry after `Retry-After` header value |

### Error Response Format
```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "errors": [
      {
        "field": "email",
        "message": "must be a valid email address"
      }
    ],
    "request_id": "req_abc123"
  }
}
```

---

## 5. Best Practices

### Authentication & Security
- Always use HTTPS for API requests.
- Store tokens securely; never expose in client-side code or logs.
- Rotate API keys every 90 days.
- Use scoped tokens with minimum required permissions.
- Validate and sanitize all input server-side.

### Idempotency
- Include `Idempotency-Key` header on all POST/PUT/PATCH requests.
- Use UUIDs or unique client-generated keys for idempotency keys.
- Retain idempotency keys for at least 24 hours for retry safety.

### Pagination
- Always handle pagination; never assume all results fit in one page.
- Use cursor-based pagination (`cursor` param) for stable large-dataset traversal.
- Default `per_page` to 20; maximum is 100.

### Filtering & Sorting
- Use indexed fields for filtering to avoid full table scans.
- Combine filters with AND logic; use `filter[field]=value` syntax.
- Sort by indexed columns only; avoid sorting on text/JSON fields.

### Optimistic Locking
- Always include `If-Match` header with current ETag for updates.
- Handle `412 Precondition Failed` by re-fetching and retrying.
- Never blind-overwrite; always read-before-write.

### Rate Limiting
- Respect `X-RateLimit-Remaining` and `X-RateLimit-Reset` headers.
- Implement exponential backoff with jitter on `429` responses.
- Use `Retry-After` header value when present.
- Target < 100 requests/second per API key.

### Bulk Operations
- Keep bulk payloads under 100 items per request.
- Process bulk operations asynchronously for large sets.
- Validate all items before submitting; partial failures return per-item errors.

### Webhooks
- Verify webhook signatures using the `X-Apex-Signature` header.
- Respond to webhooks within 5 seconds; process asynchronously.
- Implement idempotency in webhook handlers using `event_id`.
- Retry failed webhook deliveries with exponential backoff.

### Data Integrity
- Use transactions for multi-resource operations.
- Enforce referential integrity; cascade deletes explicitly.
- Soft-delete by default; hard-delete only when legally required.
- Audit all mutations via the Audit Logs API.

### Performance
- Use `fields` param to request only needed fields.
- Use `include` for eager-loading relations (max 3 levels deep).
- Cache GET responses with appropriate TTL; invalidate on writes.
- Use conditional requests with `If-None-Match` for caching.

### Error Handling
- Always check HTTP status code before parsing response body.
- Log `request_id` for all errors; include in support tickets.
- Implement circuit breakers for downstream service failures.
- Provide user-friendly messages; log technical details server-side.

### Versioning
- Pin to a specific API version in production (`/api/v1/`).
- Monitor deprecation headers (`Deprecation`, `Sunset`).
- Migrate to new versions within the deprecation window.
- Test against staging before production upgrades.
