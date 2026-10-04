"""Notification Center CRUD API: notifications, templates, rules, preferences."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ── Pydantic Models ──────────────────────────────────────────────────────────

class NotificationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=2000)
    type: str = Field(default="info", pattern="^(info|warning|error|success)$")
    read: bool = False
    user_id: Optional[str] = None


class NotificationUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    message: Optional[str] = Field(None, min_length=1, max_length=2000)
    type: Optional[str] = Field(None, pattern="^(info|warning|error|success)$")
    read: Optional[bool] = None
    user_id: Optional[str] = None


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    read: bool
    user_id: Optional[str] = None
    created_at: str
    updated_at: str


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    subject: str = Field(..., min_length=1, max_length=300)
    body: str = Field(..., min_length=1)
    type: str = Field(default="info", pattern="^(info|warning|error|success)$")
    is_active: bool = True


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    subject: Optional[str] = Field(None, min_length=1, max_length=300)
    body: Optional[str] = Field(None, min_length=1)
    type: Optional[str] = Field(None, pattern="^(info|warning|error|success)$")
    is_active: Optional[bool] = None


class TemplateResponse(BaseModel):
    id: int
    name: str
    subject: str
    body: str
    type: str
    is_active: bool
    created_at: str
    updated_at: str


class RuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    condition: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)
    priority: int = Field(default=5, ge=1, le=10)
    is_active: bool = True


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    condition: Optional[str] = Field(None, min_length=1)
    action: Optional[str] = Field(None, min_length=1)
    priority: Optional[int] = Field(None, ge=1, le=10)
    is_active: Optional[bool] = None


class RuleResponse(BaseModel):
    id: int
    name: str
    condition: str
    action: str
    priority: int
    is_active: bool
    created_at: str
    updated_at: str


class PreferenceCreate(BaseModel):
    user_id: str = Field(..., min_length=1)
    email_enabled: bool = True
    push_enabled: bool = True
    sms_enabled: bool = False
    digest_frequency: str = Field(default="immediate", pattern="^(immediate|hourly|daily|weekly)$")
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


class PreferenceUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    digest_frequency: Optional[str] = Field(None, pattern="^(immediate|hourly|daily|weekly)$")
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


class PreferenceResponse(BaseModel):
    id: int
    user_id: str
    email_enabled: bool
    push_enabled: bool
    sms_enabled: bool
    digest_frequency: str
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    created_at: str
    updated_at: str


# ── In-Memory Data Stores ────────────────────────────────────────────────────

_notifications: List[dict] = [
    {
        "id": i,
        "title": f"Notification {i}",
        "message": f"This is notification number {i}.",
        "type": ["info", "warning", "error", "success"][i % 4],
        "read": i % 3 == 0,
        "user_id": f"user_{i % 5}",
        "created_at": datetime(2024, 1, i + 1).isoformat(),
        "updated_at": datetime(2024, 1, i + 1).isoformat(),
    }
    for i in range(1, 26)
]
_next_notif_id = 26

_templates: List[dict] = [
    {
        "id": i,
        "name": f"Template {i}",
        "subject": f"Template subject {i}",
        "body": f"Template body content for template {i}.",
        "type": ["info", "warning", "error", "success"][i % 4],
        "is_active": i % 2 == 0,
        "created_at": datetime(2024, 2, i).isoformat(),
        "updated_at": datetime(2024, 2, i).isoformat(),
    }
    for i in range(1, 11)
]
_next_template_id = 11

_rules: List[dict] = [
    {
        "id": i,
        "name": f"Rule {i}",
        "condition": f"condition_{i}",
        "action": f"action_{i}",
        "priority": (i % 10) + 1,
        "is_active": i % 2 == 0,
        "created_at": datetime(2024, 3, i).isoformat(),
        "updated_at": datetime(2024, 3, i).isoformat(),
    }
    for i in range(1, 11)
]
_next_rule_id = 11

_preferences: List[dict] = [
    {
        "id": i,
        "user_id": f"user_{i}",
        "email_enabled": True,
        "push_enabled": i % 2 == 0,
        "sms_enabled": False,
        "digest_frequency": ["immediate", "hourly", "daily", "weekly"][i % 4],
        "quiet_hours_start": "22:00" if i % 2 == 0 else None,
        "quiet_hours_end": "07:00" if i % 2 == 0 else None,
        "created_at": datetime(2024, 4, i).isoformat(),
        "updated_at": datetime(2024, 4, i).isoformat(),
    }
    for i in range(1, 6)
]
_next_pref_id = 6


# ── Notifications CRUD ───────────────────────────────────────────────────────

@router.get("", response_model=dict)
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    read: Optional[bool] = None,
    type: Optional[str] = None,
):
    filtered = _notifications
    if read is not None:
        filtered = [n for n in filtered if n["read"] == read]
    if type:
        filtered = [n for n in filtered if n["type"] == type]
    total = len(filtered)
    start = (page - 1) * page_size
    items = filtered[start:start + page_size]
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size}


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(notification_id: int):
    for n in _notifications:
        if n["id"] == notification_id:
            return n
    raise HTTPException(status_code=404, detail="Notification not found")


@router.post("", response_model=NotificationResponse, status_code=201)
def create_notification(data: NotificationCreate):
    global _next_notif_id
    now = datetime.utcnow().isoformat()
    n = {"id": _next_notif_id, **data.model_dump(), "created_at": now, "updated_at": now}
    _notifications.append(n)
    _next_notif_id += 1
    return n


@router.put("/{notification_id}", response_model=NotificationResponse)
def update_notification(notification_id: int, data: NotificationUpdate):
    for n in _notifications:
        if n["id"] == notification_id:
            for k, v in data.model_dump(exclude_unset=True).items():
                n[k] = v
            n["updated_at"] = datetime.utcnow().isoformat()
            return n
    raise HTTPException(status_code=404, detail="Notification not found")


@router.delete("/{notification_id}", status_code=204)
def delete_notification(notification_id: int):
    for i, n in enumerate(_notifications):
        if n["id"] == notification_id:
            _notifications.pop(i)
            return
    raise HTTPException(status_code=404, detail="Notification not found")


# ── Templates CRUD ───────────────────────────────────────────────────────────

@router.get("/templates", response_model=dict)
def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    filtered = _templates
    if type:
        filtered = [t for t in filtered if t["type"] == type]
    if is_active is not None:
        filtered = [t for t in filtered if t["is_active"] == is_active]
    total = len(filtered)
    start = (page - 1) * page_size
    items = filtered[start:start + page_size]
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size}


@router.get("/templates/{template_id}", response_model=TemplateResponse)
def get_template(template_id: int):
    for t in _templates:
        if t["id"] == template_id:
            return t
    raise HTTPException(status_code=404, detail="Template not found")


@router.post("/templates", response_model=TemplateResponse, status_code=201)
def create_template(data: TemplateCreate):
    global _next_template_id
    now = datetime.utcnow().isoformat()
    t = {"id": _next_template_id, **data.model_dump(), "created_at": now, "updated_at": now}
    _templates.append(t)
    _next_template_id += 1
    return t


@router.put("/templates/{template_id}", response_model=TemplateResponse)
def update_template(template_id: int, data: TemplateUpdate):
    for t in _templates:
        if t["id"] == template_id:
            for k, v in data.model_dump(exclude_unset=True).items():
                t[k] = v
            t["updated_at"] = datetime.utcnow().isoformat()
            return t
    raise HTTPException(status_code=404, detail="Template not found")


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(template_id: int):
    for i, t in enumerate(_templates):
        if t["id"] == template_id:
            _templates.pop(i)
            return
    raise HTTPException(status_code=404, detail="Template not found")


# ── Rules CRUD ───────────────────────────────────────────────────────────────

@router.get("/rules", response_model=dict)
def list_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    is_active: Optional[bool] = None,
):
    filtered = _rules
    if is_active is not None:
        filtered = [r for r in filtered if r["is_active"] == is_active]
    total = len(filtered)
    start = (page - 1) * page_size
    items = filtered[start:start + page_size]
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size}


@router.get("/rules/{rule_id}", response_model=RuleResponse)
def get_rule(rule_id: int):
    for r in _rules:
        if r["id"] == rule_id:
            return r
    raise HTTPException(status_code=404, detail="Rule not found")


@router.post("/rules", response_model=RuleResponse, status_code=201)
def create_rule(data: RuleCreate):
    global _next_rule_id
    now = datetime.utcnow().isoformat()
    r = {"id": _next_rule_id, **data.model_dump(), "created_at": now, "updated_at": now}
    _rules.append(r)
    _next_rule_id += 1
    return r


@router.put("/rules/{rule_id}", response_model=RuleResponse)
def update_rule(rule_id: int, data: RuleUpdate):
    for r in _rules:
        if r["id"] == rule_id:
            for k, v in data.model_dump(exclude_unset=True).items():
                r[k] = v
            r["updated_at"] = datetime.utcnow().isoformat()
            return r
    raise HTTPException(status_code=404, detail="Rule not found")


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int):
    for i, r in enumerate(_rules):
        if r["id"] == rule_id:
            _rules.pop(i)
            return
    raise HTTPException(status_code=404, detail="Rule not found")


# ── Preferences CRUD ─────────────────────────────────────────────────────────

@router.get("/preferences", response_model=dict)
def list_preferences(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user_id: Optional[str] = None,
):
    filtered = _preferences
    if user_id:
        filtered = [p for p in filtered if p["user_id"] == user_id]
    total = len(filtered)
    start = (page - 1) * page_size
    items = filtered[start:start + page_size]
    return {"items": items, "total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size}


@router.get("/preferences/{pref_id}", response_model=PreferenceResponse)
def get_preference(pref_id: int):
    for p in _preferences:
        if p["id"] == pref_id:
            return p
    raise HTTPException(status_code=404, detail="Preference not found")


@router.post("/preferences", response_model=PreferenceResponse, status_code=201)
def create_preference(data: PreferenceCreate):
    global _next_pref_id
    now = datetime.utcnow().isoformat()
    p = {"id": _next_pref_id, **data.model_dump(), "created_at": now, "updated_at": now}
    _preferences.append(p)
    _next_pref_id += 1
    return p


@router.put("/preferences/{pref_id}", response_model=PreferenceResponse)
def update_preference(pref_id: int, data: PreferenceUpdate):
    for p in _preferences:
        if p["id"] == pref_id:
            for k, v in data.model_dump(exclude_unset=True).items():
                p[k] = v
            p["updated_at"] = datetime.utcnow().isoformat()
            return p
    raise HTTPException(status_code=404, detail="Preference not found")


@router.delete("/preferences/{pref_id}", status_code=204)
def delete_preference(pref_id: int):
    for i, p in enumerate(_preferences):
        if p["id"] == pref_id:
            _preferences.pop(i)
            return
    raise HTTPException(status_code=404, detail="Preference not found")
