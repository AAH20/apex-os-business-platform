# Data Science API Design

Base URL: `https://api.apex-os.internal/v1`
Auth: Bearer token (OAuth2 client-credentials). All endpoints return JSON; errors follow RFC 7807.

---

## 1. Training API

Manage training jobs: submit, monitor, and retrieve artifacts.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/training/jobs` | Submit a training job |
| GET | `/training/jobs` | List jobs (filter by status, model_id) |
| GET | `/training/jobs/{job_id}` | Job status, metrics, config |
| POST | `/training/jobs/{job_id}/cancel` | Cancel a running job |
| GET | `/training/jobs/{job_id}/logs` | Stream logs (SSE) |
| GET | `/training/jobs/{job_id}/artifacts` | List output artifacts (checkpoints, metrics) |
| POST | `/training/jobs/{job_id}/clone` | Re-submit with modified config |

**Submit job body:**
```json
{
  "model_id": "fraud-detector",
  "dataset_version": "2026-09-01",
  "hyperparameters": {"lr": 0.001, "epochs": 50},
  "compute": {"gpu": "A100", "count": 4},
  "experiment_id": "exp-123"
}
```

**Response:** `202 Accepted` with `job_id`, `status: queued`.

---

## 2. Inference API

Online and batch prediction endpoints.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/inference/predict` | Single real-time prediction |
| POST | `/inference/batch` | Async batch scoring (returns job_id) |
| GET | `/inference/batch/{job_id}` | Batch job status + results URL |
| GET | `/inference/models` | List deployed models |
| POST | `/inference/models/{model_id}/deploy` | Deploy a registered model version |
| POST | `/inference/models/{model_id}/undeploy` | Remove from serving |
| GET | `/inference/models/{model_id}/health` | Latency, throughput, error rate |

**Predict request:**
```json
{
  "model_id": "fraud-detector",
  "version": "3",
  "instances": [{"amount": 120.50, "merchant": "acme"}],
  "explain": true
}
```

**Predict response:**
```json
{
  "predictions": [{"score": 0.87, "label": "fraud", "shap": {...}}],
  "model_version": "3",
  "latency_ms": 42
}
```

---

## 3. Feature Store API

Centralized feature definitions, ingestion, and retrieval.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/features/entities` | Register an entity (e.g., `user`, `merchant`) |
| POST | `/features/tables` | Define a feature table (online/offline store) |
| GET | `/features/tables/{table_id}` | Schema, stats, freshness |
| POST | `/features/tables/{table_id}/ingest` | Push feature rows (stream or batch) |
| GET | `/features/online/{entity_id}` | Fetch online features for an entity |
| POST | `/features/lookup` | Batch entity feature lookup |
| GET | `/features/history/{entity_id}` | Time-travel point-in-time lookup |
| POST | `/features/transform` | Register a transformation (SQL/Python) |

**Ingest body:**
```json
{
  "table_id": "user_txn_stats",
  "rows": [
    {"entity_id": "u-42", "features": {"txn_count_7d": 15}, "event_time": "2026-10-01T00:00:00Z"}
  ]
}
```

**Online lookup response:**
```json
{
  "entity_id": "u-42",
  "features": {"txn_count_7d": 15, "avg_amount_30d": 84.2},
  "event_time": "2026-10-01T00:00:00Z"
}
```

---

## 4. Model Registry API

Versioned model storage with lifecycle stages.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/registry/models` | Register a new model |
| GET | `/registry/models` | List models (filter by name, stage) |
| GET | `/registry/models/{model_id}` | Model metadata + versions |
| POST | `/registry/models/{model_id}/versions` | Upload a new version (artifact URI) |
| GET | `/registry/models/{model_id}/versions/{ver}` | Version details, lineage |
| POST | `/registry/models/{model_id}/transition` | Move version to stage (`staging`/`production`/`archived`) |
| GET | `/registry/models/{model_id}/lineage` | Upstream datasets + downstream deployments |
| DELETE | `/registry/models/{model_id}/versions/{ver}` | Delete a version (non-production only) |

**Register model body:**
```json
{
  "name": "fraud-detector",
  "type": "xgboost",
  "description": "Real-time fraud scoring",
  "tags": {"team": "risk", "env": "prod"}
}
```

**Transition body:**
```json
{
  "version": "4",
  "stage": "production",
  "comment": "Improved recall on v3"
}
```

---

## 5. Experiment Tracking API

Log and compare ML experiments, parameters, and metrics.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/experiments` | Create an experiment |
| GET | `/experiments` | List experiments (filter by owner, date) |
| GET | `/experiments/{exp_id}` | Experiment metadata + runs |
| POST | `/experiments/{exp_id}/runs` | Start a run |
| GET | `/experiments/{exp_id}/runs` | List runs with metrics |
| GET | `/experiments/{exp_id}/runs/{run_id}` | Run detail (params, metrics, artifacts) |
| POST | `/experiments/{exp_id}/runs/{run_id}/log` | Log params/metrics/artifacts |
| POST | `/experiments/{exp_id}/runs/{run_id}/finish` | Mark run complete (status, final metrics) |
| GET | `/experiments/{exp_id}/compare` | Side-by-side run comparison |
| POST | `/experiments/{exp_id}/best` | Return best run by metric |

**Start run body:**
```json
{
  "name": "lr-sweep-001",
  "params": {"lr": 0.001, "batch_size": 64},
  "tags": {"git_commit": "a1b2c3"}
}
```

**Log body:**
```json
{
  "step": 10,
  "metrics": {"loss": 0.34, "accuracy": 0.91},
  "artifacts": ["s3://bucket/run-123/checkpoint.pt"]
}
```

**Compare response:**
```json
{
  "runs": [
    {"run_id": "r1", "params": {"lr": 0.001}, "metrics": {"accuracy": 0.91}},
    {"run_id": "r2", "params": {"lr": 0.01}, "metrics": {"accuracy": 0.89}}
  ]
}
```

---

## Conventions

- **Pagination:** `?cursor=<opaque>&limit=100` (max 1000).
- **Idempotency:** POST endpoints accept `Idempotency-Key` header.
- **Rate limits:** 1000 req/min per client; `429` with `Retry-After`.
- **Errors:** `{"type": "...", "title": "...", "status": 400, "detail": "..."}`.
- **Versioning:** Breaking changes bump the URL version (`/v2`).
