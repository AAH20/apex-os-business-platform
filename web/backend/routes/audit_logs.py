"""AuditLog CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone

router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])

# Synthetic in-memory store
_audit_logs: dict[int, dict] = {}
_next_id = 1


class AuditLogCreate(BaseModel):
    action: str = Field(..., min_length=1, max_length=100)
    entity_type: str = Field(..., min_length=1, max_length=50)
    entity_id: str = Field(..., min_length=1, max_length=100)
    user_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None


class AuditLogUpdate(BaseModel):
    action: Optional[str] = Field(None, min_length=1, max_length=100)
    entity_type: Optional[str] = Field(None, min_length=1, max_length=50)
    entity_id: Optional[str] = Field(None, min_length=1, max_length=100)
    user_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: str
    user_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: str


def _seed():
    global _next_id
    samples = [
        ("create", "user", "usr_001", "admin", "Created new user account", "192.168.1.10"),
        ("update", "order", "ord_552", "system", "Order status changed to shipped", "10.0.0.5"),
        ("delete", "product", "prd_99", "admin", "Removed discontinued product", "192.168.1.10"),
        ("login", "session", "sess_abc", "usr_002", "User logged in", "172.16.0.22"),
        ("export", "report", "rpt_q3", "usr_003", "Exported Q3 financial report", "10.0.0.8"),
    ]
    for action, etype, eid, uid, details, ip in samples:
        _audit_logs[_next_id] = {
            "id": _next_id,
            "action": action,
            "entity_type": etype,
            "entity_id": eid,
            "user_id": uid,
            "details": details,
            "ip_address": ip,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _next_id += 1


_seed()


@router.get("", response_model=List[AuditLogResponse])
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
):
    """List all audit logs with pagination and optional filtering."""
    logs = list(_audit_logs.values())
    if action:
        logs = [log for log in logs if log["action"] == action]
    if entity_type:
        logs = [log for log in logs if log["entity_type"] == entity_type]
    start = (page - 1) * page_size
    return logs[start : start + page_size]


@router.get("/{log_id}", response_model=AuditLogResponse)
def get_audit_log(log_id: int):
    """Get a single audit log by ID."""
    if log_id not in _audit_logs:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return _audit_logs[log_id]


@router.post("", response_model=AuditLogResponse, status_code=201)
def create_audit_log(payload: AuditLogCreate):
    """Create a new audit log entry."""
    global _next_id
    log = payload.model_dump()
    log["id"] = _next_id
    log["created_at"] = datetime.now(timezone.utc).isoformat()
    _audit_logs[_next_id] = log
    _next_id += 1
    return log


@router.put("/{log_id}", response_model=AuditLogResponse)
def update_audit_log(log_id: int, payload: AuditLogUpdate):
    """Update an existing audit log entry."""
    if log_id not in _audit_logs:
        raise HTTPException(status_code=404, detail="Audit log not found")
    stored = _audit_logs[log_id]
    for field, value in payload.model_dump(exclude_unset=True).items():
        stored[field] = value
    return stored


@router.delete("/{log_id}", status_code=204)
def delete_audit_log(log_id: int):
    """Delete an audit log entry."""
    if log_id not in _audit_logs:
        raise HTTPException(status_code=404, detail="Audit log not found")
    del _audit_logs[log_id]
