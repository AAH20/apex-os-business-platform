"""Comprehensive CRUD API routes for all APEX-OS Business Platform modules.

Provides REST endpoints for users, accounts, journal entries, leads, agents,
datasets, models, alerts, and audit logs with full CRUD operations,
pagination, filtering, sorting, optimistic locking, and soft deletes.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["CRUD"])


# ─── Generic CRUD helpers ─────────────────────────────────────────────────────

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    items: List[T]
    total: int
    skip: int
    limit: int


def _paginate(items: List[T], skip: int = 0, limit: int = 50) -> PaginatedResponse[T]:
    """Apply pagination to a list of items."""
    total = len(items)
    return PaginatedResponse(items=items[skip : skip + limit], total=total, skip=skip, limit=limit)


def _sort_items(items: List[Dict], sort_by: str, sort_order: str = "asc") -> List[Dict]:
    """Sort a list of dicts by a key."""
    reverse = sort_order == "desc"
    return sorted(items, key=lambda x: x.get(sort_by, ""), reverse=reverse)


def _soft_delete(store: Dict[str, Dict], entity_id: str) -> None:
    """Mark an entity as deleted by setting deleted_at."""
    if entity_id in store:
        store[entity_id]["deleted_at"] = datetime.now(timezone.utc).isoformat()


def _is_deleted(entity: Dict) -> bool:
    """Check if an entity is soft-deleted."""
    return entity.get("deleted_at") is not None


def _filter_active(items: List[Dict]) -> List[Dict]:
    """Filter out soft-deleted items."""
    return [i for i in items if not _is_deleted(i)]


# ─── In-memory stores ────────────────────────────────────────────────────────

_users: Dict[str, Dict] = {}
_accounts: Dict[str, Dict] = {}
_journal_entries: Dict[str, Dict] = {}
_leads: Dict[str, Dict] = {}
_agents: Dict[str, Dict] = {}
_datasets: Dict[str, Dict] = {}
_models: Dict[str, Dict] = {}
_alerts: Dict[str, Dict] = {}
_audit_logs: Dict[str, Dict] = {}


# ─── Pydantic schemas ────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    email: str = Field(..., max_length=255)
    full_name: Optional[str] = Field(default=None, max_length=200)
    role: str = "viewer"
    is_active: bool = True


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=1, max_length=128)
    email: Optional[str] = Field(default=None, max_length=255)
    full_name: Optional[str] = Field(default=None, max_length=200)
    role: Optional[str] = None
    is_active: Optional[bool] = None
    version: int


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    version: int
    created_at: str
    updated_at: str
    deleted_at: Optional[str] = None


class AccountCreate(BaseModel):
    user_id: str
    name: str = Field(..., min_length=1, max_length=200)
    account_number: str = Field(..., min_length=1, max_length=50)
    balance: float = 0.0
    currency: str = "USD"
    status: str = "active"


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    balance: Optional[float] = None
    currency: Optional[str] = Field(default=None, max_length=3)
    status: Optional[str] = None
    version: int


class AccountResponse(BaseModel):
    id: str
    user_id: str
    name: str
    account_number: str
    balance: float
    currency: str
    status: str
    version: int
    created_at: str
    updated_at: str
    deleted_at: Optional[str] = None


class JournalEntryLineCreate(BaseModel):
    account_id: str
    debit: float = Field(default=0.0, ge=0)
    credit: float = Field(default=0.0, ge=0)


class JournalEntryCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=512)
    lines: List[JournalEntryLineCreate] = Field(..., min_length=2)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JournalEntryUpdate(BaseModel):
    description: Optional[str] = Field(default=None, min_length=1, max_length=512)
    metadata: Optional[Dict[str, Any]] = None
    version: int


class JournalEntryResponse(BaseModel):
    id: str
    description: str
    lines: List[Dict[str, Any]]
    total_debit: float
    total_credit: float
    is_balanced: bool
    metadata: Dict[str, Any] = {}
    version: int
    created_at: str
    updated_at: str
    deleted_at: Optional[str] = None


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    WON = "won"
    LOST = "lost"


class LeadCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    email: str = Field(..., max_length=255)
    company: Optional[str] = Field(default=None, max_length=256)
    value: float = Field(default=0.0, ge=0)
    status: LeadStatus = LeadStatus.NEW
    source: Optional[str] = Field(default=None, max_length=128)
    score: float = Field(default=0.0, ge=0, le=100)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LeadUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=256)
    email: Optional[str] = Field(default=None, max_length=255)
    company: Optional[str] = Field(default=None, max_length=256)
    value: Optional[float] = Field(default=None, ge=0)
    status: Optional[LeadStatus] = None
    source: Optional[str] = Field(default=None, max_length=128)
    score: Optional[float] = Field(default=None, ge=0, le=100)
    metadata: Optional[Dict[str, Any]] = None
    version: int


class LeadResponse(BaseModel):
    id: str
    name: str
    email: str
    company: Optional[str] = None
    value: float
    status: str
    source: Optional[str] = None
    score: float
    metadata: Dict[str, Any] = {}
    version: int
    created_at: str
    updated_at: str
    deleted_at: Optional[str] = None


class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    status: AgentStatus = AgentStatus.IDLE
    capacity: int = Field(default=10, ge=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=256)
    status: Optional[AgentStatus] = None
    capacity: Optional[int] = Field(default=None, ge=1)
    metadata: Optional[Dict[str, Any]] = None
    version: int


class AgentResponse(BaseModel):
    id: str
    name: str
    status: str
    capacity: int
    active_connections: int
    is_available: bool
    metadata: Dict[str, Any] = {}
    version: int
    created_at: str
    updated_at: str
    deleted_at: Optional[str] = None


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    version: str = "1.0.0"
    rows: int = Field(default=0, ge=0)
    columns: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DatasetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=256)
    version: Optional[str] = None
    rows: Optional[int] = Field(default=None, ge=0)
    columns: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    version_lock: int


class DatasetResponse(BaseModel):
    id: str
    name: str
    version: str
    rows: int
    columns: List[str]
    fingerprint: str
    metadata: Dict[str, Any] = {}
    version_lock: int
    created_at: str
    updated_at: str
    deleted_at: Optional[str] = None


class ModelStatus(str, Enum):
    DRAFT = "draft"
    TRAINING = "training"
    TRAINED = "trained"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"


class ModelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    model_type: str = "linear"
    status: ModelStatus = ModelStatus.DRAFT
    metrics: Dict[str, float] = Field(default_factory=dict)
    params: Dict[str, Any] = Field(default_factory=dict)
    feature_names: List[str] = Field(default_factory=list)


class ModelUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=256)
    model_type: Optional[str] = None
    status: Optional[ModelStatus] = None
    metrics: Optional[Dict[str, float]] = None
    params: Optional[Dict[str, Any]] = None
    feature_names: Optional[List[str]] = None
    version: int


class ModelResponse(BaseModel):
    id: str
    name: str
    model_type: str
    status: str
    metrics: Dict[str, float] = {}
    params: Dict[str, Any] = {}
    feature_names: List[str] = []
    version: int
    created_at: str
    updated_at: str
    deleted_at: Optional[str] = None


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    FIRING = "firing"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertCreate(BaseModel):
    rule_id: str
    rule_name: str = Field(..., min_length=1, max_length=256)
    severity: AlertSeverity = AlertSeverity.WARNING
    status: AlertStatus = AlertStatus.FIRING
    message: str = Field(..., min_length=1, max_length=1024)
    source: Optional[str] = Field(default=None, max_length=256)
    value: float = 0.0
    threshold: float = 0.0
    labels: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    severity: Optional[AlertSeverity] = None
    message: Optional[str] = Field(default=None, min_length=1, max_length=1024)
    labels: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None
    version: int


class AlertResponse(BaseModel):
    id: str
    rule_id: str
    rule_name: str
    severity: str
    status: str
    message: str
    source: Optional[str] = None
    value: float
    threshold: float
    labels: Dict[str, str] = {}
    metadata: Dict[str, Any] = {}
    version: int
    created_at: str
    updated_at: str
    deleted_at: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: str
    timestamp: str
    actor: str
    action: str
    resource: str
    resource_type: str
    metadata: Dict[str, Any] = {}
    severity: str
    status: str
    ip_address: Optional[str] = None
    duration_ms: Optional[float] = None


# ─── Dependency injection ────────────────────────────────────────────────────

def get_current_user(request: Request) -> Optional[str]:
    """Get current authenticated user ID from request state."""
    return getattr(request.state, "user_id", None)


# ─── /api/users ──────────────────────────────────────────────────────────────

@router.get("/users", response_model=PaginatedResponse[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = "created_at",
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    _: Optional[str] = Depends(get_current_user),
):
    """List users with pagination, filtering, and sorting."""
    items = list(_users.values())
    items = _filter_active(items)
    if role:
        items = [i for i in items if i.get("role") == role]
    if is_active is not None:
        items = [i for i in items if i.get("is_active") == is_active]
    items = _sort_items(items, sort_by, sort_order)
    return _paginate(items, skip, limit)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, _: Optional[str] = Depends(get_current_user)):
    """Create a new user."""
    for u in _users.values():
        if u["username"] == body.username:
            raise HTTPException(status_code=409, detail="Username already exists")
        if u["email"] == body.email:
            raise HTTPException(status_code=409, detail="Email already exists")
    now = datetime.now(timezone.utc).isoformat()
    user = {
        "id": str(uuid.uuid4()),
        "username": body.username,
        "email": body.email,
        "full_name": body.full_name,
        "role": body.role,
        "is_active": body.is_active,
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    _users[user["id"]] = user
    return user


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, _: Optional[str] = Depends(get_current_user)):
    """Get a user by ID."""
    user = _users.get(user_id)
    if not user or _is_deleted(user):
        raise HTTPException(status_code=404, detail=f"User not found: {user_id}")
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str, body: UserUpdate, _: Optional[str] = Depends(get_current_user)
):
    """Update a user with optimistic locking."""
    user = _users.get(user_id)
    if not user or _is_deleted(user):
        raise HTTPException(status_code=404, detail=f"User not found: {user_id}")
    if user["version"] != body.version:
        raise HTTPException(status_code=409, detail="Version conflict")
    for field in ("username", "email", "full_name", "role", "is_active"):
        val = getattr(body, field)
        if val is not None:
            user[field] = val
    user["version"] += 1
    user["updated_at"] = datetime.now(timezone.utc).isoformat()
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, _: Optional[str] = Depends(get_current_user)):
    """Soft-delete a user."""
    if user_id not in _users:
        raise HTTPException(status_code=404, detail=f"User not found: {user_id}")
    _soft_delete(_users, user_id)


# ─── /api/accounts ───────────────────────────────────────────────────────────

@router.get("/accounts", response_model=PaginatedResponse[AccountResponse])
async def list_accounts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = "created_at",
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    _: Optional[str] = Depends(get_current_user),
):
    """List accounts with pagination, filtering, and sorting."""
    items = list(_accounts.values())
    items = _filter_active(items)
    if user_id:
        items = [i for i in items if i.get("user_id") == user_id]
    if status:
        items = [i for i in items if i.get("status") == status]
    items = _sort_items(items, sort_by, sort_order)
    return _paginate(items, skip, limit)


@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(body: AccountCreate, _: Optional[str] = Depends(get_current_user)):
    """Create a new account."""
    for a in _accounts.values():
        if a["account_number"] == body.account_number:
            raise HTTPException(status_code=409, detail="Account number already exists")
    now = datetime.now(timezone.utc).isoformat()
    account = {
        "id": str(uuid.uuid4()),
        "user_id": body.user_id,
        "name": body.name,
        "account_number": body.account_number,
        "balance": body.balance,
        "currency": body.currency,
        "status": body.status,
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    _accounts[account["id"]] = account
    return account


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(account_id: str, _: Optional[str] = Depends(get_current_user)):
    """Get an account by ID."""
    account = _accounts.get(account_id)
    if not account or _is_deleted(account):
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")
    return account


@router.put("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str, body: AccountUpdate, _: Optional[str] = Depends(get_current_user)
):
    """Update an account with optimistic locking."""
    account = _accounts.get(account_id)
    if not account or _is_deleted(account):
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")
    if account["version"] != body.version:
        raise HTTPException(status_code=409, detail="Version conflict")
    for field in ("name", "balance", "currency", "status"):
        val = getattr(body, field)
        if val is not None:
            account[field] = val
    account["version"] += 1
    account["updated_at"] = datetime.now(timezone.utc).isoformat()
    return account


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: str, _: Optional[str] = Depends(get_current_user)):
    """Soft-delete an account."""
    if account_id not in _accounts:
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")
    _soft_delete(_accounts, account_id)


# ─── /api/journal-entries ────────────────────────────────────────────────────

@router.get("/journal-entries", response_model=PaginatedResponse[JournalEntryResponse])
async def list_journal_entries(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = "created_at",
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    account_id: Optional[str] = None,
    _: Optional[str] = Depends(get_current_user),
):
    """List journal entries with pagination, filtering, and sorting."""
    items = list(_journal_entries.values())
    items = _filter_active(items)
    if account_id:
        items = [
            i for i in items
            if any(l["account_id"] == account_id for l in i.get("lines", []))
        ]
    items = _sort_items(items, sort_by, sort_order)
    return _paginate(items, skip, limit)


@router.post("/journal-entries", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_journal_entry(
    body: JournalEntryCreate, _: Optional[str] = Depends(get_current_user)
):
    """Create a journal entry with double-entry validation."""
    total_debit = sum(l.debit for l in body.lines)
    total_credit = sum(l.credit for l in body.lines)
    if abs(total_debit - total_credit) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Double-entry imbalance: debit={total_debit}, credit={total_credit}",
        )
    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "id": str(uuid.uuid4()),
        "description": body.description,
        "lines": [l.model_dump() for l in body.lines],
        "total_debit": total_debit,
        "total_credit": total_credit,
        "is_balanced": True,
        "metadata": body.metadata,
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    _journal_entries[entry["id"]] = entry
    return entry


@router.get("/journal-entries/{entry_id}", response_model=JournalEntryResponse)
async def get_journal_entry(entry_id: str, _: Optional[str] = Depends(get_current_user)):
    """Get a journal entry by ID."""
    entry = _journal_entries.get(entry_id)
    if not entry or _is_deleted(entry):
        raise HTTPException(status_code=404, detail=f"Journal entry not found: {entry_id}")
    return entry


@router.put("/journal-entries/{entry_id}", response_model=JournalEntryResponse)
async def update_journal_entry(
    entry_id: str, body: JournalEntryUpdate, _: Optional[str] = Depends(get_current_user)
):
    """Update a journal entry metadata with optimistic locking."""
    entry = _journal_entries.get(entry_id)
    if not entry or _is_deleted(entry):
        raise HTTPException(status_code=404, detail=f"Journal entry not found: {entry_id}")
    if entry["version"] != body.version:
        raise HTTPException(status_code=409, detail="Version conflict")
    if body.description is not None:
        entry["description"] = body.description
    if body.metadata is not None:
        entry["metadata"] = body.metadata
    entry["version"] += 1
    entry["updated_at"] = datetime.now(timezone.utc).isoformat()
    return entry


@router.delete("/journal-entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal_entry(entry_id: str, _: Optional[str] = Depends(get_current_user)):
    """Soft-delete a journal entry."""
    if entry_id not in _journal_entries:
        raise HTTPException(status_code=404, detail=f"Journal entry not found: {entry_id}")
    _soft_delete(_journal_entries, entry_id)


# ─── /api/leads ──────────────────────────────────────────────────────────────

@router.get("/leads", response_model=PaginatedResponse[LeadResponse])
async def list_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = "created_at",
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    status: Optional[str] = None,
    min_score: Optional[float] = Query(None, ge=0, le=100),
    _: Optional[str] = Depends(get_current_user),
):
    """List leads with pagination, filtering, and sorting."""
    items = list(_leads.values())
    items = _filter_active(items)
    if status:
        items = [i for i in items if i.get("status") == status]
    if min_score is not None:
        items = [i for i in items if i.get("score", 0) >= min_score]
    items = _sort_items(items, sort_by, sort_order)
    return _paginate(items, skip, limit)


@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(body: LeadCreate, _: Optional[str] = Depends(get_current_user)):
    """Create a new lead with scoring."""
    now = datetime.now(timezone.utc).isoformat()
    lead = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "email": body.email,
        "company": body.company,
        "value": body.value,
        "status": body.status.value,
        "source": body.source,
        "score": body.score,
        "metadata": body.metadata,
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    _leads[lead["id"]] = lead
    return lead


@router.get("/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: str, _: Optional[str] = Depends(get_current_user)):
    """Get a lead by ID."""
    lead = _leads.get(lead_id)
    if not lead or _is_deleted(lead):
        raise HTTPException(status_code=404, detail=f"Lead not found: {lead_id}")
    return lead


@router.put("/leads/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: str, body: LeadUpdate, _: Optional[str] = Depends(get_current_user)
):
    """Update a lead with optimistic locking."""
    lead = _leads.get(lead_id)
    if not lead or _is_deleted(lead):
        raise HTTPException(status_code=404, detail=f"Lead not found: {lead_id}")
    if lead["version"] != body.version:
        raise HTTPException(status_code=409, detail="Version conflict")
    for field in ("name", "email", "company", "value", "source", "score", "metadata"):
        val = getattr(body, field)
        if val is not None:
            lead[field] = val
    if body.status is not None:
        lead["status"] = body.status.value
    lead["version"] += 1
    lead["updated_at"] = datetime.now(timezone.utc).isoformat()
    return lead


@router.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(lead_id: str, _: Optional[str] = Depends(get_current_user)):
    """Soft-delete a lead."""
    if lead_id not in _leads:
        raise HTTPException(status_code=404, detail=f"Lead not found: {lead_id}")
    _soft_delete(_leads, lead_id)


# ─── /api/agents ─────────────────────────────────────────────────────────────

@router.get("/agents", response_model=PaginatedResponse[AgentResponse])
async def list_agents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = "created_at",
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    status: Optional[str] = None,
    _: Optional[str] = Depends(get_current_user),
):
    """List agents with pagination, filtering, and sorting."""
    items = list(_agents.values())
    items = _filter_active(items)
    if status:
        items = [i for i in items if i.get("status") == status]
    items = _sort_items(items, sort_by, sort_order)
    return _paginate(items, skip, limit)


@router.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(body: AgentCreate, _: Optional[str] = Depends(get_current_user)):
    """Create a new agent."""
    now = datetime.now(timezone.utc).isoformat()
    agent = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "status": body.status.value,
        "capacity": body.capacity,
        "active_connections": 0,
        "is_available": True,
        "metadata": body.metadata,
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    _agents[agent["id"]] = agent
    return agent


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, _: Optional[str] = Depends(get_current_user)):
    """Get an agent by ID."""
    agent = _agents.get(agent_id)
    if not agent or _is_deleted(agent):
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return agent


@router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str, body: AgentUpdate, _: Optional[str] = Depends(get_current_user)
):
    """Update an agent with optimistic locking."""
    agent = _agents.get(agent_id)
    if not agent or _is_deleted(agent):
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    if agent["version"] != body.version:
        raise HTTPException(status_code=409, detail="Version conflict")
    for field in ("name", "capacity", "metadata"):
        val = getattr(body, field)
        if val is not None:
            agent[field] = val
    if body.status is not None:
        agent["status"] = body.status.value
    agent["is_available"] = (
        agent["status"] != "offline"
        and agent["active_connections"] < agent["capacity"]
    )
    agent["version"] += 1
    agent["updated_at"] = datetime.now(timezone.utc).isoformat()
    return agent


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str, _: Optional[str] = Depends(get_current_user)):
    """Soft-delete an agent."""
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    _soft_delete(_agents, agent_id)


# ─── /api/datasets ───────────────────────────────────────────────────────────

@router.get("/datasets", response_model=PaginatedResponse[DatasetResponse])
async def list_datasets(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = "created_at",
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    name: Optional[str] = None,
    _: Optional[str] = Depends(get_current_user),
):
    """List datasets with pagination, filtering, and sorting."""
    items = list(_datasets.values())
    items = _filter_active(items)
    if name:
        items = [i for i in items if name.lower() in i.get("name", "").lower()]
    items = _sort_items(items, sort_by, sort_order)
    return _paginate(items, skip, limit)


@router.post("/datasets", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(body: DatasetCreate, _: Optional[str] = Depends(get_current_user)):
    """Create a new dataset."""
    import hashlib
    payload = f"{body.name}:{body.version}:{body.rows}:{','.join(body.columns)}"
    fingerprint = hashlib.sha256(payload.encode()).hexdigest()[:16]
    now = datetime.now(timezone.utc).isoformat()
    dataset = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "version": body.version,
        "rows": body.rows,
        "columns": body.columns,
        "fingerprint": fingerprint,
        "metadata": body.metadata,
        "version_lock": 1,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    _datasets[dataset["id"]] = dataset
    return dataset


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: str, _: Optional[str] = Depends(get_current_user)):
    """Get a dataset by ID."""
    dataset = _datasets.get(dataset_id)
    if not dataset or _is_deleted(dataset):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
    return dataset


@router.put("/datasets/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: str, body: DatasetUpdate, _: Optional[str] = Depends(get_current_user)
):
    """Update a dataset with optimistic locking."""
    dataset = _datasets.get(dataset_id)
    if not dataset or _is_deleted(dataset):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
    if dataset["version_lock"] != body.version_lock:
        raise HTTPException(status_code=409, detail="Version conflict")
    for field in ("name", "version", "rows", "columns", "metadata"):
        val = getattr(body, field)
        if val is not None:
            dataset[field] = val
    dataset["version_lock"] += 1
    dataset["updated_at"] = datetime.now(timezone.utc).isoformat()
    return dataset


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(dataset_id: str, _: Optional[str] = Depends(get_current_user)):
    """Soft-delete a dataset."""
    if dataset_id not in _datasets:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
    _soft_delete(_datasets, dataset_id)


# ─── /api/models ─────────────────────────────────────────────────────────────

@router.get("/models", response_model=PaginatedResponse[ModelResponse])
async def list_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = "created_at",
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    status: Optional[str] = None,
    model_type: Optional[str] = None,
    _: Optional[str] = Depends(get_current_user),
):
    """List models with pagination, filtering, and sorting."""
    items = list(_models.values())
    items = _filter_active(items)
    if status:
        items = [i for i in items if i.get("status") == status]
    if model_type:
        items = [i for i in items if i.get("model_type") == model_type]
    items = _sort_items(items, sort_by, sort_order)
    return _paginate(items, skip, limit)


@router.post("/models", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(body: ModelCreate, _: Optional[str] = Depends(get_current_user)):
    """Create a new model."""
    now = datetime.now(timezone.utc).isoformat()
    model = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "model_type": body.model_type,
        "status": body.status.value,
        "metrics": body.metrics,
        "params": body.params,
        "feature_names": body.feature_names,
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    _models[model["id"]] = model
    return model


@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(model_id: str, _: Optional[str] = Depends(get_current_user)):
    """Get a model by ID."""
    model = _models.get(model_id)
    if not model or _is_deleted(model):
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
    return model


@router.put("/models/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: str, body: ModelUpdate, _: Optional[str] = Depends(get_current_user)
):
    """Update a model with optimistic locking."""
    model = _models.get(model_id)
    if not model or _is_deleted(model):
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
    if model["version"] != body.version:
        raise HTTPException(status_code=409, detail="Version conflict")
    for field in ("name", "model_type", "metrics", "params", "feature_names"):
        val = getattr(body, field)
        if val is not None:
            model[field] = val
    if body.status is not None:
        model["status"] = body.status.value
    model["version"] += 1
    model["updated_at"] = datetime.now(timezone.utc).isoformat()
    return model


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(model_id: str, _: Optional[str] = Depends(get_current_user)):
    """Soft-delete a model."""
    if model_id not in _models:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
    _soft_delete(_models, model_id)


# ─── /api/alerts ─────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=PaginatedResponse[AlertResponse])
async def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = "created_at",
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    _: Optional[str] = Depends(get_current_user),
):
    """List alerts with pagination, filtering, and sorting."""
    items = list(_alerts.values())
    items = _filter_active(items)
    if status:
        items = [i for i in items if i.get("status") == status]
    if severity:
        items = [i for i in items if i.get("severity") == severity]
    items = _sort_items(items, sort_by, sort_order)
    return _paginate(items, skip, limit)


@router.post("/alerts", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(body: AlertCreate, _: Optional[str] = Depends(get_current_user)):
    """Create a new alert."""
    now = datetime.now(timezone.utc).isoformat()
    alert = {
        "id": str(uuid.uuid4()),
        "rule_id": body.rule_id,
        "rule_name": body.rule_name,
        "severity": body.severity.value,
        "status": body.status.value,
        "message": body.message,
        "source": body.source,
        "value": body.value,
        "threshold": body.threshold,
        "labels": body.labels,
        "metadata": body.metadata,
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    _alerts[alert["id"]] = alert
    return alert


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str, _: Optional[str] = Depends(get_current_user)):
    """Get an alert by ID."""
    alert = _alerts.get(alert_id)
    if not alert or _is_deleted(alert):
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")
    return alert


@router.put("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str, body: AlertUpdate, _: Optional[str] = Depends(get_current_user)
):
    """Update an alert with optimistic locking."""
    alert = _alerts.get(alert_id)
    if not alert or _is_deleted(alert):
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")
    if alert["version"] != body.version:
        raise HTTPException(status_code=409, detail="Version conflict")
    for field in ("severity", "message", "labels", "metadata"):
        val = getattr(body, field)
        if val is not None:
            alert[field] = val
    if body.status is not None:
        alert["status"] = body.status.value
    alert["version"] += 1
    alert["updated_at"] = datetime.now(timezone.utc).isoformat()
    return alert


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(alert_id: str, _: Optional[str] = Depends(get_current_user)):
    """Soft-delete an alert."""
    if alert_id not in _alerts:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")
    _soft_delete(_alerts, alert_id)


# ─── /api/audit-logs (read-only) ─────────────────────────────────────────────

@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = "timestamp",
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    actor: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    _: Optional[str] = Depends(get_current_user),
):
    """List audit logs with pagination, filtering, and sorting. Read-only."""
    items = list(_audit_logs.values())
    if actor:
        items = [i for i in items if i.get("actor") == actor]
    if action:
        items = [i for i in items if i.get("action") == action]
    if resource_type:
        items = [i for i in items if i.get("resource_type") == resource_type]
    items = _sort_items(items, sort_by, sort_order)
    return _paginate(items, skip, limit)


@router.get("/audit-logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(log_id: str, _: Optional[str] = Depends(get_current_user)):
    """Get an audit log by ID. Read-only."""
    log = _audit_logs.get(log_id)
    if not log:
        raise HTTPException(status_code=404, detail=f"Audit log not found: {log_id}")
    return log