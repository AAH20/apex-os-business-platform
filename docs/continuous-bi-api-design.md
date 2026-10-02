# Continuous BI API Design

Base URL: `/api/v1`  
Auth: Bearer token (JWT)  
Content-Type: `application/json`

---

## 1. Query API

Execute ad-hoc queries against the BI data layer.

### POST /queries

Execute a query and return results.

**Request:**
```json
{
  "dataset": "sales",
  "dimensions": ["region", "product"],
  "measures": ["revenue", "units"],
  "filters": [
    { "field": "date", "op": "between", "value": ["2025-01-01", "2025-03-31"] }
  ],
  "order_by": [{ "field": "revenue", "direction": "desc" }],
  "limit": 1000,
  "offset": 0
}
```

**Response (200):**
```json
{
  "query_id": "q_abc123",
  "status": "completed",
  "columns": ["region", "product", "revenue", "units"],
  "rows": [
    { "region": "EMEA", "product": "Widget A", "revenue": 125000, "units": 500 }
  ],
  "total_rows": 42,
  "execution_time_ms": 312
}
```

**Errors:** `400` invalid query, `401` unauthorized, `403` dataset not permitted, `422` validation error

### GET /queries/{query_id}

Retrieve a previously executed query's results (cached for 15 min).

**Response (200):** Same shape as POST /queries response.

### POST /queries/validate

Dry-run a query without executing. Returns estimated cost and validation errors.

**Request:** Same as POST /queries (no limit/offset required).

**Response (200):**
```json
{
  "valid": true,
  "estimated_cost": "low",
  "warnings": ["Filter on 'date' may benefit from an index"]
}
```

---

## 2. Dashboard API

Manage dashboard definitions and retrieve rendered data.

### GET /dashboards

List dashboards accessible to the caller.

**Query params:** `page`, `per_page`, `sort`, `filter`

**Response (200):**
```json
{
  "dashboards": [
    {
      "id": "dash_001",
      "name": "Q1 Sales Overview",
      "description": "Quarterly sales performance",
      "owner": "user_123",
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-03-20T14:30:00Z",
      "widget_count": 6,
      "tags": ["sales", "quarterly"]
    }
  ],
  "total": 12
}
```

### POST /dashboards

Create a new dashboard.

**Request:**
```json
{
  "name": "Marketing Funnel",
  "description": "Full-funnel conversion metrics",
  "tags": ["marketing", "funnel"],
  "widgets": [
    {
      "type": "chart",
      "chart_type": "bar",
      "title": "Conversions by Stage",
      "query": { "dataset": "marketing", "dimensions": ["stage"], "measures": ["count"] }
    }
  ]
}
```

**Response (201):** The created dashboard object.

### GET /dashboards/{id}

Retrieve a dashboard definition with all widgets.

**Response (200):**
```json
{
  "id": "dash_001",
  "name": "Q1 Sales Overview",
  "widgets": [
    {
      "id": "w_001",
      "type": "chart",
      "chart_type": "line",
      "title": "Revenue Trend",
      "query": { "dataset": "sales", "dimensions": ["date"], "measures": ["revenue"] },
      "position": { "x": 0, "y": 0, "w": 6, "h": 4 }
    }
  ]
}
```

### PUT /dashboards/{id}

Update a dashboard (full replacement).

**Request:** Same as POST /dashboards.

**Response (200):** Updated dashboard object.

### DELETE /dashboards/{id}

Delete a dashboard.

**Response:** `204 No Content`

### POST /dashboards/{id}/render

Execute all widget queries and return rendered data.

**Query params:** `refresh` (bool, bypass cache)

**Response (200):**
```json
{
  "dashboard_id": "dash_001",
  "rendered_at": "2025-03-25T09:00:00Z",
  "widgets": [
    {
      "widget_id": "w_001",
      "status": "ok",
      "data": { "columns": ["date", "revenue"], "rows": [...] },
      "error": null
    }
  ]
}
```

---

## 3. Alert API

Define and manage threshold-based alerts on BI data.

### GET /alerts

List alerts for the caller.

**Query params:** `page`, `per_page`, `status` (active/paused/triggered), `severity`

**Response (200):**
```json
{
  "alerts": [
    {
      "id": "alert_001",
      "name": "Revenue Drop",
      "description": "Daily revenue below threshold",
      "severity": "critical",
      "status": "active",
      "query": { "dataset": "sales", "dimensions": ["date"], "measures": ["revenue"] },
      "condition": { "operator": "lt", "value": 50000 },
      "notification_channels": ["email", "slack"],
      "last_triggered": "2025-03-20T08:00:00Z",
      "created_at": "2025-01-10T12:00:00Z"
    }
  ],
  "total": 5
}
```

### POST /alerts

Create a new alert.

**Request:**
```json
{
  "name": "Revenue Drop",
  "description": "Daily revenue below threshold",
  "severity": "critical",
  "query": { "dataset": "sales", "dimensions": ["date"], "measures": ["revenue"] },
  "condition": { "operator": "lt", "value": 50000 },
  "notification_channels": ["email", "slack"],
  "schedule": "0 8 * * *"
}
```

**Response (201):** The created alert object.

### GET /alerts/{id}

Retrieve a single alert.

**Response (200):** Alert object.

### PUT /alerts/{id}

Update an alert.

**Request:** Same as POST /alerts.

**Response (200):** Updated alert object.

### DELETE /alerts/{id}

Delete an alert.

**Response:** `204 No Content`

### POST /alerts/{id}/pause

Pause an active alert.

**Response (200):** Updated alert with `status: "paused"`.

### POST /alerts/{id}/resume

Resume a paused alert.

**Response (200):** Updated alert with `status: "active"`.

### GET /alerts/{id}/history

Retrieve trigger history for an alert.

**Query params:** `page`, `per_page`, `from`, `to`

**Response (200):**
```json
{
  "history": [
    {
      "triggered_at": "2025-03-20T08:00:00Z",
      "value": 42000,
      "threshold": 50000,
      "message": "Revenue 42000 is below threshold 50000",
      "acknowledged": false
    }
  ],
  "total": 3
}
```

---

## 4. Export API

Export query results or dashboard data in various formats.

### POST /exports

Create an export job.

**Request:**
```json
{
  "source": {
    "type": "query",
    "query": {
      "dataset": "sales",
      "dimensions": ["region", "product"],
      "measures": ["revenue", "units"],
      "filters": []
    }
  },
  "format": "csv",
  "options": {
    "include_headers": true,
    "delimiter": ",",
    "compression": "gzip"
  }
}
```

**Response (202):**
```json
{
  "export_id": "exp_001",
  "status": "pending",
  "estimated_completion": "2025-03-25T09:01:00Z",
  "download_url": null
}
```

### GET /exports/{export_id}

Check export status and get download URL when ready.

**Response (200) — pending:**
```json
{
  "export_id": "exp_001",
  "status": "processing",
  "progress": 45,
  "download_url": null
}
```

**Response (200) — completed:**
```json
{
  "export_id": "exp_001",
  "status": "completed",
  "progress": 100,
  "download_url": "/api/v1/exports/exp_001/download",
  "expires_at": "2025-03-26T09:00:00Z",
  "file_size_bytes": 204800
}
```

### GET /exports/{export_id}/download

Download the exported file.

**Response (200):** Binary file stream with appropriate `Content-Type` and `Content-Disposition` headers.

### GET /exports

List export jobs for the caller.

**Query params:** `page`, `per_page`, `status`

**Response (200):**
```json
{
  "exports": [
    {
      "export_id": "exp_001",
      "format": "csv",
      "status": "completed",
      "created_at": "2025-03-25T09:00:30Z",
      "file_size_bytes": 204800
    }
  ],
  "total": 8
}
```

### DELETE /exports/{export_id}

Cancel a pending export or delete a completed one.

**Response:** `204 No Content`

---

## 5. Subscription API

Manage scheduled report subscriptions for automated delivery.

### GET /subscriptions

List subscriptions for the caller.

**Query params:** `page`, `per_page`, `status` (active/paused/expired)

**Response (200):**
```json
{
  "subscriptions": [
    {
      "id": "sub_001",
      "name": "Weekly Sales Report",
      "description": "Every Monday at 8am",
      "status": "active",
      "dashboard_id": "dash_001",
      "query": null,
      "format": "pdf",
      "schedule": "0 8 * * 1",
      "delivery": {
        "channels": ["email"],
        "recipients": ["team@example.com"]
      },
      "last_delivered": "2025-03-24T08:00:00Z",
      "next_delivery": "2025-03-31T08:00:00Z",
      "created_at": "2025-01-05T10:00:00Z"
    }
  ],
  "total": 4
}
```

### POST /subscriptions

Create a new subscription.

**Request:**
```json
{
  "name": "Weekly Sales Report",
  "description": "Every Monday at 8am",
  "dashboard_id": "dash_001",
  "format": "pdf",
  "schedule": "0 8 * * 1",
  "delivery": {
    "channels": ["email"],
    "recipients": ["team@example.com"]
  }
}
```

**Response (201):** The created subscription object.

### GET /subscriptions/{id}

Retrieve a single subscription.

**Response (200):** Subscription object.

### PUT /subscriptions/{id}

Update a subscription.

**Request:** Same as POST /subscriptions.

**Response (200):** Updated subscription object.

### DELETE /subscriptions/{id}

Delete a subscription.

**Response:** `204 No Content`

### POST /subscriptions/{id}/pause

Pause a subscription.

**Response (200):** Updated subscription with `status: "paused"`.

### POST /subscriptions/{id}/resume

Resume a paused subscription.

**Response (200):** Updated subscription with `status: "active"`.

### POST /subscriptions/{id}/trigger

Manually trigger a subscription delivery immediately.

**Response (202):**
```json
{
  "delivery_id": "del_001",
  "status": "queued",
  "estimated_completion": "2025-03-25T09:02:00Z"
}
```

### GET /subscriptions/{id}/deliveries

Retrieve delivery history for a subscription.

**Query params:** `page`, `per_page`, `status` (success/failed)

**Response (200):**
```json
{
  "deliveries": [
    {
      "delivery_id": "del_001",
      "triggered_at": "2025-03-24T08:00:00Z",
      "status": "success",
      "format": "pdf",
      "file_size_bytes": 1024000,
      "recipients": ["team@example.com"],
      "error": null
    }
  ],
  "total": 12
}
```

---

## Common Error Format

All endpoints return errors in a consistent format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid query: missing required field 'dataset'",
    "details": [
      { "field": "dataset", "issue": "required" }
    ]
  }
}
```

## Rate Limits

- Standard tier: 100 requests/minute
- Export API: 10 requests/minute
- Burst: 200 requests/minute

Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
