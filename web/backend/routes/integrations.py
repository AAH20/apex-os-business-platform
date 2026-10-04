"""Integration CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


# ─── Integration Models ──────────────────────────────────────────────────────

class IntegrationCreate(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    config: Optional[dict] = None
    is_active: bool = True


class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None


class IntegrationResponse(IntegrationCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── API Key Models ──────────────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    name: str
    integration_id: int
    scopes: Optional[list[str]] = None
    expires_at: Optional[datetime] = None


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    scopes: Optional[list[str]] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class ApiKeyResponse(ApiKeyCreate):
    id: int
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Webhook Models ──────────────────────────────────────────────────────────

class WebhookCreate(BaseModel):
    integration_id: int
    url: str
    events: list[str]
    secret: Optional[str] = None
    is_active: bool = True


class WebhookUpdate(BaseModel):
    url: Optional[str] = None
    events: Optional[list[str]] = None
    secret: Optional[str] = None
    is_active: Optional[bool] = None


class WebhookResponse(WebhookCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Sync Job Models ─────────────────────────────────────────────────────────

class SyncJobCreate(BaseModel):
    integration_id: int
    job_type: str
    config: Optional[dict] = None


class SyncJobUpdate(BaseModel):
    status: Optional[str] = None
    result: Optional[dict] = None
    error_message: Optional[str] = None


class SyncJobResponse(SyncJobCreate):
    id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


# ─── In-Memory Storage ──────────────────────────────────────────────────────

_integrations = [
    {"id": 1, "name": "Salesforce", "type": "crm", "description": "Salesforce CRM integration", "config": {"api_version": "v58.0"}, "is_active": True, "created_at": datetime(2024, 1, 15), "updated_at": datetime(2024, 1, 15)},
    {"id": 2, "name": "Stripe", "type": "payment", "description": "Stripe payment processing", "config": {"webhook_enabled": True}, "is_active": True, "created_at": datetime(2024, 2, 20), "updated_at": datetime(2024, 2, 20)},
    {"id": 3, "name": "Slack", "type": "notification", "description": "Slack notifications", "config": {"channel": "#alerts"}, "is_active": False, "created_at": datetime(2024, 3, 10), "updated_at": datetime(2024, 3, 10)},
]
_next_integration_id = 4

_api_keys = [
    {"id": 1, "name": "Production Key", "integration_id": 1, "scopes": ["read", "write"], "key_prefix": "sk_live_abc123", "is_active": True, "created_at": datetime(2024, 1, 15), "last_used_at": datetime(2024, 6, 1), "expires_at": None},
    {"id": 2, "name": "Staging Key", "integration_id": 2, "scopes": ["read"], "key_prefix": "sk_test_def456", "is_active": True, "created_at": datetime(2024, 2, 20), "last_used_at": datetime(2024, 5, 28), "expires_at": datetime(2025, 2, 20)},
]
_next_api_key_id = 3

_webhooks = [
    {"id": 1, "integration_id": 1, "url": "https://hooks.example.com/salesforce", "events": ["lead.created", "deal.closed"], "secret": "whsec_abc123", "is_active": True, "created_at": datetime(2024, 1, 15), "updated_at": datetime(2024, 1, 15)},
    {"id": 2, "integration_id": 2, "url": "https://hooks.example.com/stripe", "events": ["payment.success", "payment.failed"], "secret": "whsec_def456", "is_active": True, "created_at": datetime(2024, 2, 20), "updated_at": datetime(2024, 2, 20)},
]
_next_webhook_id = 3

_sync_jobs = [
    {"id": 1, "integration_id": 1, "job_type": "full_sync", "config": {"batch_size": 100}, "status": "completed", "started_at": datetime(2024, 6, 1, 10, 0), "completed_at": datetime(2024, 6, 1, 10, 5), "result": {"records_synced": 1500}, "error_message": None},
    {"id": 2, "integration_id": 2, "job_type": "incremental", "config": {"since": "2024-05-01"}, "status": "running", "started_at": datetime(2024, 6, 1, 12, 0), "completed_at": None, "result": None, "error_message": None},
    {"id": 3, "integration_id": 1, "job_type": "delta", "config": {}, "status": "failed", "started_at": datetime(2024, 5, 30, 8, 0), "completed_at": datetime(2024, 5, 30, 8, 2), "result": None, "error_message": "Connection timeout"},
]
_next_sync_job_id = 4


# ─── Integration Endpoints ──────────────────────────────────────────────────

@router.get("/", response_model=list[IntegrationResponse])
def list_integrations(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    return _integrations[skip : skip + limit]


@router.get("/{integration_id}", response_model=IntegrationResponse)
def get_integration(integration_id: int):
    for i in _integrations:
        if i["id"] == integration_id:
            return i
    raise HTTPException(status_code=404, detail="Integration not found")


@router.post("/", response_model=IntegrationResponse, status_code=201)
def create_integration(integration: IntegrationCreate):
    global _next_integration_id
    now = datetime.now()
    new_integration = {"id": _next_integration_id, **integration.model_dump(), "created_at": now, "updated_at": now}
    _integrations.append(new_integration)
    _next_integration_id += 1
    return new_integration


@router.put("/{integration_id}", response_model=IntegrationResponse)
def update_integration(integration_id: int, integration: IntegrationUpdate):
    for i, item in enumerate(_integrations):
        if item["id"] == integration_id:
            for field, value in integration.model_dump(exclude_unset=True).items():
                _integrations[i][field] = value
            _integrations[i]["updated_at"] = datetime.now()
            return _integrations[i]
    raise HTTPException(status_code=404, detail="Integration not found")


@router.delete("/{integration_id}", status_code=204)
def delete_integration(integration_id: int):
    for i, item in enumerate(_integrations):
        if item["id"] == integration_id:
            _integrations.pop(i)
            return
    raise HTTPException(status_code=404, detail="Integration not found")


# ─── API Key Endpoints ──────────────────────────────────────────────────────

@router.get("/api-keys/", response_model=list[ApiKeyResponse])
def list_api_keys(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    return _api_keys[skip : skip + limit]


@router.get("/api-keys/{key_id}", response_model=ApiKeyResponse)
def get_api_key(key_id: int):
    for k in _api_keys:
        if k["id"] == key_id:
            return k
    raise HTTPException(status_code=404, detail="API key not found")


@router.post("/api-keys/", response_model=ApiKeyResponse, status_code=201)
def create_api_key(api_key: ApiKeyCreate):
    global _next_api_key_id
    new_key = {
        "id": _next_api_key_id,
        **api_key.model_dump(),
        "key_prefix": f"sk_live_{_next_api_key_id:06d}",
        "is_active": True,
        "created_at": datetime.now(),
        "last_used_at": None,
    }
    _api_keys.append(new_key)
    _next_api_key_id += 1
    return new_key


@router.put("/api-keys/{key_id}", response_model=ApiKeyResponse)
def update_api_key(key_id: int, api_key: ApiKeyUpdate):
    for i, k in enumerate(_api_keys):
        if k["id"] == key_id:
            for field, value in api_key.model_dump(exclude_unset=True).items():
                _api_keys[i][field] = value
            return _api_keys[i]
    raise HTTPException(status_code=404, detail="API key not found")


@router.delete("/api-keys/{key_id}", status_code=204)
def delete_api_key(key_id: int):
    for i, k in enumerate(_api_keys):
        if k["id"] == key_id:
            _api_keys.pop(i)
            return
    raise HTTPException(status_code=404, detail="API key not found")


# ─── Webhook Endpoints ──────────────────────────────────────────────────────

@router.get("/webhooks/", response_model=list[WebhookResponse])
def list_webhooks(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    return _webhooks[skip : skip + limit]


@router.get("/webhooks/{webhook_id}", response_model=WebhookResponse)
def get_webhook(webhook_id: int):
    for w in _webhooks:
        if w["id"] == webhook_id:
            return w
    raise HTTPException(status_code=404, detail="Webhook not found")


@router.post("/webhooks/", response_model=WebhookResponse, status_code=201)
def create_webhook(webhook: WebhookCreate):
    global _next_webhook_id
    now = datetime.now()
    new_webhook = {"id": _next_webhook_id, **webhook.model_dump(), "created_at": now, "updated_at": now}
    _webhooks.append(new_webhook)
    _next_webhook_id += 1
    return new_webhook


@router.put("/webhooks/{webhook_id}", response_model=WebhookResponse)
def update_webhook(webhook_id: int, webhook: WebhookUpdate):
    for i, w in enumerate(_webhooks):
        if w["id"] == webhook_id:
            for field, value in webhook.model_dump(exclude_unset=True).items():
                _webhooks[i][field] = value
            _webhooks[i]["updated_at"] = datetime.now()
            return _webhooks[i]
    raise HTTPException(status_code=404, detail="Webhook not found")


@router.delete("/webhooks/{webhook_id}", status_code=204)
def delete_webhook(webhook_id: int):
    for i, w in enumerate(_webhooks):
        if w["id"] == webhook_id:
            _webhooks.pop(i)
            return
    raise HTTPException(status_code=404, detail="Webhook not found")


# ─── Sync Job Endpoints ─────────────────────────────────────────────────────

@router.get("/sync-jobs/", response_model=list[SyncJobResponse])
def list_sync_jobs(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    return _sync_jobs[skip : skip + limit]


@router.get("/sync-jobs/{job_id}", response_model=SyncJobResponse)
def get_sync_job(job_id: int):
    for j in _sync_jobs:
        if j["id"] == job_id:
            return j
    raise HTTPException(status_code=404, detail="Sync job not found")


@router.post("/sync-jobs/", response_model=SyncJobResponse, status_code=201)
def create_sync_job(job: SyncJobCreate):
    global _next_sync_job_id
    new_job = {
        "id": _next_sync_job_id,
        **job.model_dump(),
        "status": "pending",
        "started_at": datetime.now(),
        "completed_at": None,
        "result": None,
        "error_message": None,
    }
    _sync_jobs.append(new_job)
    _next_sync_job_id += 1
    return new_job


@router.put("/sync-jobs/{job_id}", response_model=SyncJobResponse)
def update_sync_job(job_id: int, job: SyncJobUpdate):
    for i, j in enumerate(_sync_jobs):
        if j["id"] == job_id:
            for field, value in job.model_dump(exclude_unset=True).items():
                _sync_jobs[i][field] = value
            if job.status == "completed" and not _sync_jobs[i]["completed_at"]:
                _sync_jobs[i]["completed_at"] = datetime.now()
            return _sync_jobs[i]
    raise HTTPException(status_code=404, detail="Sync job not found")


@router.delete("/sync-jobs/{job_id}", status_code=204)
def delete_sync_job(job_id: int):
    for i, j in enumerate(_sync_jobs):
        if j["id"] == job_id:
            _sync_jobs.pop(i)
            return
    raise HTTPException(status_code=404, detail="Sync job not found")
