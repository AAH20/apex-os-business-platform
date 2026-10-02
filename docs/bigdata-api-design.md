# Big Data API Design

## 1. Data Ingestion API

### POST /v1/ingest/batch
Ingest a batch of records into a specified dataset.

**Request**
```json
{
  "dataset_id": "string",
  "records": [
    { "field": "value" }
  ],
  "format": "json|csv|parquet",
  "mode": "append|upsert|replace"
}
```

**Response**
```json
{
  "job_id": "string",
  "status": "accepted|rejected",
  "records_received": 0,
  "records_accepted": 0,
  "errors": []
}
```

### POST /v1/ingest/stream
Open a streaming ingestion session (WebSocket upgrade).

**Headers**
- `X-Dataset-ID`: target dataset
- `X-Stream-Mode`: `append|upsert`

**Messages**
- Client sends JSON lines or binary frames
- Server acknowledges with offset + checksum per batch

### GET /v1/ingest/jobs/{job_id}
Poll ingestion job status.

**Response**
```json
{
  "job_id": "string",
  "status": "pending|running|completed|failed",
  "progress_percent": 0,
  "records_processed": 0,
  "error_summary": null
}
```

### POST /v1/ingest/validate
Validate records without persisting.

**Request**
```json
{
  "dataset_id": "string",
  "records": [],
  "schema_version": "string"
}
```

**Response**
```json
{
  "valid": true,
  "violations": [
    { "record_index": 0, "field": "name", "message": "required" }
  ]
}
```

---

## 2. Query API

### POST /v1/query
Execute an ad-hoc query against a dataset.

**Request**
```json
{
  "dataset_id": "string",
  "select": ["field1", "field2"],
  "where": { "field1": { "$gt": 100 } },
  "group_by": ["field2"],
  "order_by": [{ "field": "field1", "direction": "desc" }],
  "limit": 100,
  "offset": 0
}
```

**Response**
```json
{
  "query_id": "string",
  "columns": ["field1", "field2"],
  "rows": [],
  "total_rows": 0,
  "execution_time_ms": 0,
  "truncated": false
}
```

### POST /v1/query/sql
Execute a SQL-like query (read-only).

**Request**
```json
{
  "sql": "SELECT field1, COUNT(*) FROM dataset WHERE field2 > 10 GROUP BY field1",
  "timeout_ms": 30000
}
```

**Response**: Same envelope as `/v1/query`.

### GET /v1/query/jobs/{job_id}
Retrieve results of an async query.

**Query Params**
- `page`: page number (default 1)
- `page_size`: rows per page (default 1000)

### POST /v1/query/subscribe
Register a webhook for query result delivery.

**Request**
```json

{
  "query": {},
  "callback_url": "https://example.com/hook",
  "frequency": "once|interval",
  "interval_seconds": 60
}
```

---

## 3. Metadata API

### GET /v1/datasets
List all datasets.

**Query Params**
- `page`, `page_size`, `tag`, `owner`

**Response**
```json
{
  "datasets": [
    {
      "id": "string",
      "name": "string",
      "description": "string",
      "schema": {},
      "tags": [],
      "owner": "string",
      "created_at": "ISO8601",
      "updated_at": "ISO8601",
      "row_count": 0,
      "size_bytes": 0
    }
  ],
  "total": 0
}
```

### GET /v1/datasets/{dataset_id}
Retrieve dataset metadata.

### POST /v1/datasets
Create a new dataset.

**Request**
```json
{
  "name": "string",
  "description": "string",
  "schema": {
    "fields": [
      { "name": "id", "type": "string", "nullable": false },
      { "name": "value", "type": "double", "nullable": true }
    ],
    "primary_key": ["id"]
  },
  "tags": [],
  "retention_days": 90
}
```

### PUT /v1/datasets/{dataset_id}
Update dataset metadata (description, tags, retention).

### DELETE /v1/datasets/{dataset_id}
Delete a dataset and all its data.

### GET /v1/datasets/{dataset_id}/schema
Retrieve the schema definition.

### GET /v1/datasets/{dataset_id}/lineage
Retrieve data lineage graph.

**Response**
```json
{
  "dataset_id": "string",
  "upstream": [],
  "downstream": [],
  "transformations": []
}
```

### GET /v1/datasets/{dataset_id}/stats
Retrieve dataset statistics.

**Response**
```json
{
  "row_count": 0,
  "size_bytes": 0,
  "column_stats": [
    { "name": "field1", "null_count": 0, "distinct_count": 0, "min": null, "max": null }
  ],
  "last_updated": "ISO8601"
}
```

---

## 4. Governance API

### GET /v1/governance/policies
List all governance policies.

**Response**
```json
{
  "policies": [
    {
      "id": "string",
      "name": "string",
      "type": "retention|access|quality|classification",
      "rules": {},
      "scope": { "datasets": [], "tags": [] },
      "enabled": true
    }
  ]
}
```

### POST /v1/governance/policies
Create a governance policy.

**Request**
```json
{
  "name": "string",
  "type": "retention",
  "rules": { "max_age_days": 365, "action": "delete|archive" },
  "scope": { "datasets": ["ds-001"] },
  "enabled": true
}
```

### PUT /v1/governance/policies/{policy_id}
Update an existing policy.

### DELETE /v1/governance/policies/{policy_id}
Remove a policy.

### GET /v1/governance/classifications
List data classifications (PII, PHI, public, etc.).

### POST /v1/governance/classify
Run classification scan on a dataset.

**Request**
```json
{
  "dataset_id": "string",
  "sample_size": 10000
}
```

**Response**
```json
{
  "scan_id": "string",
  "status": "running",
  "findings": [
    { "column": "email", "classification": "PII", "confidence": 0.98 }
  ]
}
```

### GET /v1/governance/audit
Retrieve audit log entries.

**Query Params**
- `dataset_id`, `user_id`, `action`, `from`, `to`, `page`, `page_size`

**Response**
```json
{
  "entries": [
    {
      "id": "string",
      "timestamp": "ISO8601",
      "user_id": "string",
      "action": "read|write|delete|query",
      "resource": "string",
      "details": {}
    }
  ],
  "total": 0
}
```

### POST /v1/governance/mask
Apply dynamic data masking rules.

**Request**
```json
{
  "dataset_id": "string",
  "rules": [
    { "column": "ssn", "method": "hash|redact|partial", "roles": ["analyst"] }
  ]
}
```

---

## 5. Monitoring API

### GET /v1/health
Service health check.

**Response**
```json
{
  "status": "healthy|degraded|unhealthy",
  "version": "string",
  "uptime_seconds": 0
}
```

### GET /v1/metrics
Prometheus-compatible metrics endpoint.

**Response**
```
# TYPE apex_ingest_records_total counter
apex_ingest_records_total{dataset="ds-001"} 1523400
# TYPE apex_query_duration_seconds histogram
apex_query_duration_seconds_bucket{le="0.1"} 4521
```

### GET /v1/monitoring/ingestion
Ingestion throughput and lag metrics.

**Response**
```json
{
  "datasets": [
    {
      "dataset_id": "string",
      "records_per_second": 0,
      "lag_seconds": 0,
      "last_record_at": "ISO8601",
      "error_rate": 0.0
    }
  ]
}
```

### GET /v1/monitoring/queries
Query performance metrics.

**Response**
```json
{
  "active_queries": 0,
  "queries_per_second": 0,
  "avg_latency_ms": 0,
  "p99_latency_ms": 0,
  "error_rate": 0.0,
  "slow_queries": [
    { "query_id": "string", "duration_ms": 0, "sql": "string" }
  ]
}
```

### GET /v1/monitoring/storage
Storage utilization metrics.

**Response**
```json
{
  "total_bytes": 0,
  "datasets": [
    { "dataset_id": "string", "size_bytes": 0, "replication_factor": 0 }
  ]
}
```

### GET /v1/monitoring/alerts
List active alerts.

**Response**
```json
{
  "alerts": [
    {
      "id": "string",
      "severity": "info|warning|critical",
      "source": "ingestion|query|storage|governance",
      "message": "string",
      "fired_at": "ISO8601",
      "resolved_at": null
    }
  ]
}
```

### POST /v1/monitoring/alerts/subscribe
Subscribe to alert notifications.

**Request**
```json
{
  "channel": "webhook|email|slack",
  "target": "https://hooks.slack.com/...",
  "severity_filter": ["warning", "critical"],
  "source_filter": ["ingestion"]
}
```

### GET /v1/monitoring/capacity
Capacity planning projections.

**Response**
```json
{
  "projected_full_date": "ISO8601",
  "growth_rate_bytes_per_day": 0,
  "recommendations": [
    { "action": "add_storage", "urgency": "low", "detail": "string" }
  ]
}
```
