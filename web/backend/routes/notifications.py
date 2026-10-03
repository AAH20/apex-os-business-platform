"""Notification CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


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


# Synthetic in-memory data store
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
_next_id = 26


@router.get("", response_model=dict)
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    read: Optional[bool] = None,
    type: Optional[str] = None,
):
    """List all notifications with pagination and optional filters."""
    filtered = _notifications
    if read is not None:
        filtered = [n for n in filtered if n["read"] == read]
    if type:
        filtered = [n for n in filtered if n["type"] == type]

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(notification_id: int):
    """Get a single notification by ID."""
    for n in _notifications:
        if n["id"] == notification_id:
            return n
    raise HTTPException(status_code=404, detail="Notification not found")


@router.post("", response_model=NotificationResponse, status_code=201)
def create_notification(data: NotificationCreate):
    """Create a new notification."""
    global _next_id
    now = datetime.utcnow().isoformat()
    notification = {
        "id": _next_id,
        **data.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _notifications.append(notification)
    _next_id += 1
    return notification


@router.put("/{notification_id}", response_model=NotificationResponse)
def update_notification(notification_id: int, data: NotificationUpdate):
    """Update an existing notification."""
    for n in _notifications:
        if n["id"] == notification_id:
            for key, value in data.model_dump(exclude_unset=True).items():
                n[key] = value
            n["updated_at"] = datetime.utcnow().isoformat()
            return n
    raise HTTPException(status_code=404, detail="Notification not found")


@router.delete("/{notification_id}", status_code=204)
def delete_notification(notification_id: int):
    """Delete a notification by ID."""
    for i, n in enumerate(_notifications):
        if n["id"] == notification_id:
            _notifications.pop(i)
            return
    raise HTTPException(status_code=404, detail="Notification not found")
