# APEX-OS Business Platform — Complete API Reference

**Version:** 1.0.0  
**Base URL:** `https://api.apex-os.local/v1`  
**Content-Type:** `application/json`  
**Authentication:** Bearer token via `Authorization: Bearer <token>`

---

## 1. Agent-Reach Module

Agent-Reach provides AI agent orchestration, task delegation, and multi-model routing.

### 1.1 Create Agent Session

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/agent-reach/sessions` |
| **Description** | Initialize a new agent session with a specified model configuration |

**Request Body:**
```json
{
  "agent_id": "string (required)",
  "model": "string (required) — e.g. claude-sonnet-4, gpt-4o",
  "system_prompt": "string (optional)",
  "metadata": {}
}
```

**Response Body (201 Created):**
```json
{
  "session_id": "sess_abc123",
  "agent_id": "agent_xyz",
  "model": "claude-sonnet-4",
  "status": "active",
  "created_at": "2026-10-03T10:00:00Z"
}
```

**Status Codes:** `201` Created · `400` Bad Request · `401` Unauthorized · `429` Rate Limited

---

### 1.2 Send Message to Agent

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/agent-reach/sessions/{session_id}/messages` |
| **Description** | Send a user message and receive an agent response |

**Request Body:**
```json
{
  "role": "user",
  "content": "string (required)",
  "attachments": [],
  "context": {}
}
```

**Response Body (200 OK):**
```json
{
  "message_id": "msg_001",
  "role": "assistant",
  "content": "Agent response text",
  "model": "claude-sonnet-4",
  "usage": { "input_tokens": 150, "output_tokens": 320 },
  "finish_reason": "stop"
}
```

**Status Codes:** `200` OK · `400` Bad Request · `404` Session Not Found · `429` Rate Limited

---

### 1.3 List Agent Sessions

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/agent-reach/sessions` |
| **Description** | List all active and historical agent sessions |

**Query Parameters:** `status` (active/archived), `limit` (default 20), `offset` (default 0)

**Response Body (200 OK):**
```json
{
  "sessions": [
    {
      "session_id": "sess_abc123",
      "agent_id": "agent_xyz",
      "status": "active",
      "message_count": 12,
      "created_at": "2026-10-03T10:00:00Z",
      "last_activity": "2026-10-03T10:05:00Z"
    }
  ],
  "total": 1
}
```

**Status Codes:** `200` OK · `401` Unauthorized

---

### 1.4 Get Session History

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/agent-reach/sessions/{session_id}/history` |
| **Description** | Retrieve full message history for a session |

**Response Body (200 OK):**
```json
{
  "session_id": "sess_abc123",
  "messages": [
    { "role": "user", "content": "...", "timestamp": "..." },
    { "role": "assistant", "content": "...", "timestamp": "..." }
  ]
}
```

**Status Codes:** `200` OK · `404` Session Not Found

---

### 1.5 Terminate Session

| Field | Value |
|-------|-------|
| **Method** | `DELETE` |
| **Path** | `/agent-reach/sessions/{session_id}` |
| **Description** | End and archive an agent session |

**Response Body (200 OK):**
```json
{ "session_id": "sess_abc123", "status": "terminated" }
```

**Status Codes:** `200` OK · `404` Session Not Found

---

### 1.6 Route to Optimal Model

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/agent-reach/route` |
| **Description** | Select the best model for a given task based on cost/latency/quality |

**Request Body:**
```json
{
  "task_type": "classification|generation|embedding|vision",
  "constraints": { "max_latency_ms": 2000, "max_cost_per_1k": 0.01 }
}
```

**Response Body (200 OK):**
```json
{
  "selected_model": "claude-sonnet-4",
  "reason": "best quality-to-cost ratio for generation task",
  "estimated_latency_ms": 800,
  "estimated_cost_per_1k_tokens": 0.003
}
```

**Status Codes:** `200` OK · `400` Bad Request

---

## 2. BigData Module

BigData handles large-scale data ingestion, transformation, and analytics.

### 2.1 Ingest Data Stream

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/bigdata/ingest` |
| **Description** | Ingest a batch of records into the data lake |

**Request Body:**
```json
{
  "source": "string (required) — e.g. kafka, s3, api",
  "dataset": "string (required)",
  "records": [],
  "schema": {},
  "options": { "upsert": false, "partition_key": "date" }
}
```

**Response Body (202 Accepted):**
```json
{
  "job_id": "job_789",
  "status": "processing",
  "records_received": 10000,
  "estimated_completion": "2026-10-03T10:02:00Z"
}
```

**Status Codes:** `202` Accepted · `400` Bad Request · `413` Payload Too Large · `429` Rate Limited

---

### 2.2 Query Dataset

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/bigdata/query` |
| **Description** | Run a SQL-like query against a dataset |

**Request Body:**
```json
{
  "dataset": "string (required)",
  "query": "string (required) — SQL or DSL",
  "limit": 1000,
  "format": "json|csv|parquet"
}
```

**Response Body (200 OK):**
```json
{
  "columns": ["id", "name", "value"],
  "rows": [["1", "Alice", "42"]],
  "row_count": 1,
  "execution_time_ms": 145
}
```

**Status Codes:** `200` OK · `400` Bad Request · `404` Dataset Not Found · `500` Query Error

---

### 2.3 Get Dataset Schema

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/bigdata/datasets/{dataset}/schema` |
| **Description** | Retrieve the schema definition for a dataset |

**Response Body (200 OK):**
```json
{
  "dataset": "sales_data",
  "fields": [
    { "name": "id", "type": "string", "nullable": false },
    { "name": "amount", "type": "float", "nullable": false },
    { "name": "date", "type": "timestamp", "nullable": false }
  ],
  "partition_keys": ["date"],
  "record_count": 5000000
}
```

**Status Codes:** `200` OK · `404` Dataset Not Found

---

### 2.4 List Datasets

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/bigdata/datasets` |
| **Description** | List all available datasets |

**Query Parameters:** `tag`, `limit`, `offset`

**Response Body (200 OK):**
```json
{
  "datasets": [
    { "name": "sales_data", "size_bytes": 1073741824, "record_count": 5000000, "tags": ["finance"] }
  ],
  "total": 1
}
```

**Status Codes:** `200` OK

---

### 2.5 Transform Data

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/bigdata/transform` |
| **Description** | Apply transformations (filter, aggregate, join) to a dataset |

**Request Body:**
```json
{
  "source_dataset": "string (required)",
  "target_dataset": "string (required)",
  "transformations": [
    { "type": "filter", "condition": "amount > 100" },
    { "type": "aggregate", "group_by": ["region"], "metrics": [{ "column": "amount", "fn": "sum" }] }
  ]
}
```

**Response Body (202 Accepted):**
```json
{
  "job_id": "job_transform_001",
  "status": "processing",
  "target_dataset": "sales_aggregated"
}
```

**Status Codes:** `202` Accepted · `400` Bad Request · `404` Dataset Not Found

---

### 2.6 Get Job Status

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/bigdata/jobs/{job_id}` |
| **Description** | Check the status of an async BigData job |

**Response Body (200 OK):**
```json
{
  "job_id": "job_789",
  "status": "completed|processing|failed",
  "progress_percent": 100,
  "result": { "records_processed": 10000 },
  "error": null
}
```

**Status Codes:** `200` OK · `404` Job Not Found

---

## 3. DataScience Module

DataScience provides ML model training, evaluation, and inference endpoints.

### 3.1 Train Model

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/datascience/models/train` |
| **Description** | Train a new ML model on a dataset |

**Request Body:**
```json
{
  "dataset": "string (required)",
  "model_type": "classification|regression|clustering|timeseries",
  "hyperparameters": { "n_estimators": 100, "max_depth": 10 },
  "target_column": "string (required)",
  "feature_columns": ["string"],
  "validation_split": 0.2
}
```

**Response Body (202 Accepted):**
```json
{
  "training_job_id": "train_001",
  "model_id": "model_abc",
  "status": "training",
  "estimated_duration_minutes": 15
}
```

**Status Codes:** `202` Accepted · `400` Bad Request · `404` Dataset Not Found

---

### 3.2 Get Model Details

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/datascience/models/{model_id}` |
| **Description** | Retrieve model metadata, metrics, and status |

**Response Body (200 OK):**
```json
{
  "model_id": "model_abc",
  "model_type": "classification",
  "status": "trained|training|failed",
  "metrics": { "accuracy": 0.94, "f1": 0.92, "precision": 0.93, "recall": 0.91 },
  "feature_importance": { "age": 0.4, "income": 0.35 },
  "created_at": "2026-10-03T10:00:00Z"
}
```

**Status Codes:** `200` OK · `404` Model Not Found

---

### 3.3 Run Inference

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/datascience/models/{model_id}/predict` |
| **Description** | Run predictions using a trained model |

**Request Body:**
```json
{
  "inputs": [
    { "age": 30, "income": 50000 },
    { "age": 45, "income": 75000 }
  ],
  "return_probabilities": true
}
```

**Response Body (200 OK):**
```json
{
  "predictions": [
    { "predicted_class": "yes", "probabilities": { "yes": 0.87, "no": 0.13 } },
    { "predicted_class": "no", "probabilities": { "yes": 0.32, "no": 0.68 } }
  ],
  "model_id": "model_abc",
  "inference_time_ms": 45
}
```

**Status Codes:** `200` OK · `400` Bad Request · `404` Model Not Found · `422` Model Not Ready

---

### 3.4 List Models

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/datascience/models` |
| **Description** | List all trained models |

**Query Parameters:** `status`, `model_type`, `limit`, `offset`

**Response Body (200 OK):**
```json
{
  "models": [
    { "model_id": "model_abc", "model_type": "classification", "status": "trained", "accuracy": 0.94 }
  ],
  "total": 1
}
```

**Status Codes:** `200` OK

---

### 3.5 Evaluate Model

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/datascience/models/{model_id}/evaluate` |
| **Description** | Evaluate a model against a test dataset |

**Request Body:**
```json
{
  "test_dataset": "string (required)",
  "metrics": ["accuracy", "precision", "recall", "f1", "auc"]
}
```

**Response Body (200 OK):**
```json
{
  "model_id": "model_abc",
  "evaluation_results": { "accuracy": 0.94, "precision": 0.93, "recall": 0.91, "f1": 0.92, "auc": 0.97 },
  "confusion_matrix": [[450, 50], [30, 470]]
}
```

**Status Codes:** `200` OK · `404` Model/Dataset Not Found

---

### 3.6 Deploy Model

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/datascience/models/{model_id}/deploy` |
| **Description** | Deploy a trained model to a serving endpoint |

**Request Body:**
```json
{
  "environment": "staging|production",
  "replicas": 2,
  "auto_scaling": { "min_replicas": 1, "max_replicas": 5, "target_cpu": 70 }
}
```

**Response Body (201 Created):**
```json
{
  "deployment_id": "deploy_001",
  "model_id": "model_abc",
  "endpoint": "https://api.apex-os.local/v1/datascience/models/model_abc/predict",
  "status": "deploying"
}
```

**Status Codes:** `201` Created · `404` Model Not Found · `422` Model Not Trained

---

## 4. ContinuousBI Module

ContinuousBI provides real-time dashboards, KPI monitoring, and alerting.

### 4.1 Create Dashboard

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/continuousbi/dashboards` |
| **Description** | Create a new real-time dashboard |

**Request Body:**
```json
{
  "name": "string (required)",
  "description": "string",
  "widgets": [
    { "type": "line_chart", "data_source": "sales_stream", "metric": "revenue", "time_range": "1h" },
    { "type": "kpi_card", "data_source": "orders_stream", "metric": "order_count", "aggregation": "sum" }
  ],
  "refresh_interval_seconds": 30
}
```

**Response Body (201 Created):**
```json
{
  "dashboard_id": "dash_001",
  "name": "Real-Time Sales",
  "status": "active",
  "url": "https://bi.apex-os.local/dashboards/dash_001"
}
```

**Status Codes:** `201` Created · `400` Bad Request

---

### 4.2 Get Dashboard

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/continuousbi/dashboards/{dashboard_id}` |
| **Description** | Retrieve dashboard configuration and current data |

**Response Body (200 OK):**
```json
{
  "dashboard_id": "dash_001",
  "name": "Real-Time Sales",
  "widgets": [
    { "type": "line_chart", "current_value": 15230, "trend": "up", "data_points": [...] }
  ],
  "last_updated": "2026-10-03T10:00:30Z"
}
```

**Status Codes:** `200` OK · `404` Dashboard Not Found

---

### 4.3 Update Dashboard

| Field | Value |
|-------|-------|
| **Method** | `PUT` |
| **Path** | `/continuousbi/dashboards/{dashboard_id}` |
| **Description** | Update dashboard configuration |

**Request Body:**
```json
{
  "name": "Updated Name",
  "widgets": [],
  "refresh_interval_seconds": 60
}
```

**Response Body (200 OK):**
```json
{ "dashboard_id": "dash_001", "status": "updated" }
```

**Status Codes:** `200` OK · `404` Dashboard Not Found

---

### 4.4 Delete Dashboard

| Field | Value |
|-------|-------|
| **Method** | `DELETE` |
| **Path** | `/continuousbi/dashboards/{dashboard_id}` |
| **Description** | Permanently delete a dashboard |

**Response Body (200 OK):**
```json
{ "dashboard_id": "dash_001", "status": "deleted" }
```

**Status Codes:** `200` OK · `404` Dashboard Not Found

---

### 4.5 List Dashboards

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/continuousbi/dashboards` |
| **Description** | List all dashboards |

**Query Parameters:** `status`, `limit`, `offset`

**Response Body (200 OK):**
```json
{
  "dashboards": [
    { "dashboard_id": "dash_001", "name": "Real-Time Sales", "status": "active", "widget_count": 5 }
  ],
  "total": 1
}
```

**Status Codes:** `200` OK

---

### 4.6 Create Alert Rule

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/continuousbi/alerts` |
| **Description** | Create a real-time alert rule |

**Request Body:**
```json
{
  "name": "string (required)",
  "data_source": "string (required)",
  "metric": "string (required)",
  "condition": "gt|lt|eq|gte|lte",
  "threshold": 1000,
  "notification_channels": ["email", "slack", "webhook"],
  "cooldown_minutes": 15
}
```

**Response Body (201 Created):**
```json
{
  "alert_id": "alert_001",
  "name": "High Revenue Alert",
  "status": "active",
  "trigger_count": 0
}
```

**Status Codes:** `201` Created · `400` Bad Request

---

### 4.7 Get Real-Time Metrics

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/continuousbi/metrics` |
| **Description** | Fetch current real-time metric values |

**Query Parameters:** `data_source`, `metric`, `time_range` (e.g. 5m, 1h, 24h)

**Response Body (200 OK):**
```json
{
  "metrics": [
    { "data_source": "sales_stream", "metric": "revenue", "value": 15230, "timestamp": "2026-10-03T10:00:00Z" }
  ]
}
```

**Status Codes:** `200` OK · `400` Bad Request

---

### 4.8 Get Alert History

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/continuousbi/alerts/{alert_id}/history` |
| **Description** | Retrieve trigger history for an alert |

**Response Body (200 OK):**
```json
{
  "alert_id": "alert_001",
  "triggers": [
    { "timestamp": "2026-10-03T09:15:00Z", "value": 1200, "threshold": 1000, "channels_notified": ["slack"] }
  ]
}
```

**Status Codes:** `200` OK · `404` Alert Not Found

---

## 5. CRUD Module

Generic CRUD operations for platform entities (users, projects, configurations, etc.).

### 5.1 Create Entity

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/crud/{entity_type}` |
| **Description** | Create a new entity of the specified type |

**Path Parameters:** `entity_type` — e.g. `users`, `projects`, `configurations`

**Request Body:**
```json
{
  "name": "string (required)",
  "description": "string",
  "tags": [],
  "metadata": {},
  "custom_fields": {}
}
```

**Response Body (201 Created):**
```json
{
  "id": "entity_001",
  "entity_type": "projects",
  "name": "New Project",
  "created_at": "2026-10-03T10:00:00Z",
  "updated_at": "2026-10-03T10:00:00Z"
}
```

**Status Codes:** `201` Created · `400` Bad Request · `409` Conflict (duplicate)

---

### 5.2 Get Entity

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/crud/{entity_type}/{entity_id}` |
| **Description** | Retrieve a single entity by ID |

**Response Body (200 OK):**
```json
{
  "id": "entity_001",
  "entity_type": "projects",
  "name": "New Project",
  "description": "A sample project",
  "tags": ["alpha"],
  "metadata": {},
  "created_at": "2026-10-03T10:00:00Z",
  "updated_at": "2026-10-03T10:00:00Z"
}
```

**Status Codes:** `200` OK · `404` Entity Not Found

---

### 5.3 List Entities

| Field | Value |
|-------|-------|
| **Method** | `GET` |
| **Path** | `/crud/{entity_type}` |
| **Description** | List entities of a given type with filtering and pagination |

**Query Parameters:** `filter` (e.g. `name=foo`), `sort` (e.g. `-created_at`), `limit` (default 20), `offset` (default 0)

**Response Body (200 OK):**
```json
{
  "entities": [
    { "id": "entity_001", "name": "New Project", "created_at": "2026-10-03T10:00:00Z" }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

**Status Codes:** `200` OK · `400` Bad Request

---

### 5.4 Update Entity

| Field | Value |
|-------|-------|
| **Method** | `PUT` |
| **Path** | `/crud/{entity_type}/{entity_id}` |
| **Description** | Full update of an entity (replaces all fields) |

**Request Body:**
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "tags": ["beta"],
  "metadata": {}
}
```

**Response Body (200 OK):**
```json
{
  "id": "entity_001",
  "entity_type": "projects",
  "name": "Updated Name",
  "updated_at": "2026-10-03T10:05:00Z"
}
```

**Status Codes:** `200` OK · `400` Bad Request · `404` Entity Not Found · `409` Conflict

---

### 5.5 Partial Update Entity

| Field | Value |
|-------|-------|
| **Method** | `PATCH` |
| **Path** | `/crud/{entity_type}/{entity_id}` |
| **Description** | Partial update — only specified fields are modified |

**Request Body:**
```json
{
  "name": "Partially Updated Name"
}
```

**Response Body (200 OK):**
```json
{
  "id": "entity_001",
  "name": "Partially Updated Name",
  "updated_at": "2026-10-03T10:06:00Z"
}
```

**Status Codes:** `200` OK · `400` Bad Request · `404` Entity Not Found

---

### 5.6 Delete Entity

| Field | Value |
|-------|-------|
| **Method** | `DELETE` |
| **Path** | `/crud/{entity_type}/{entity_id}` |
| **Description** | Permanently delete an entity |

**Response Body (200 OK):**
```json
{ "id": "entity_001", "entity_type": "projects", "status": "deleted" }
```

**Status Codes:** `200` OK · `404` Entity Not Found

---

### 5.7 Bulk Create

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/crud/{entity_type}/bulk` |
| **Description** | Create multiple entities in a single request |

**Request Body:**
```json
{
  "entities": [
    { "name": "Entity A" },
    { "name": "Entity B" }
  ]
}
```

**Response Body (201 Created):**
```json
{
  "created_count": 2,
  "entities": [
    { "id": "entity_002", "name": "Entity A" },
    { "id": "entity_003", "name": "Entity B" }
  ]
}
```

**Status Codes:** `201` Created · `400` Bad Request · `422` Partial Failure

---

### 5.8 Bulk Delete

| Field | Value |
|-------|-------|
| **Method** | `POST` |
| **Path** | `/crud/{entity_type}/bulk-delete` |
| **Description** | Delete multiple entities by ID |

**Request Body:**
```json
{
  "ids": ["entity_001", "entity_002"]
}
```

**Response Body (200 OK):**
```json
{
  "deleted_count": 2,
  "failed_ids": []
}
```

**Status Codes:** `200` OK · `400` Bad Request

---

## Appendix: Common Error Response Format

All endpoints return errors in the following structure:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested resource was not found.",
    "details": {},
    "request_id": "req_abc123"
  }
}
```

## Appendix: Standard HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK — Request succeeded |
| 201 | Created — Resource created successfully |
| 202 | Accepted — Async job accepted for processing |
| 400 | Bad Request — Invalid input |
| 401 | Unauthorized — Missing or invalid token |
| 403 | Forbidden — Insufficient permissions |
| 404 | Not Found — Resource does not exist |
| 409 | Conflict — Resource already exists or state conflict |
| 413 | Payload Too Large — Request body exceeds limit |
| 422 | Unprocessable Entity — Semantic validation failed |
| 429 | Rate Limited — Too many requests |
| 500 | Internal Server Error — Unexpected server error |
| 503 | Service Unavailable — Temporary maintenance or overload |

---

*End of API Reference — APEX-OS Business Platform v1.0.0*
