"""Alert CRUD API endpoints for APEX-OS Business Platform."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

_alerts_db = {
    1: {"id": 1, "title": "Server CPU High", "message": "CPU usage exceeded 90%",
        "severity": "critical", "source": "monitoring", "is_read": False,
        "is_active": True, "created_at": "2024-01-15T10:30:00"},
    2: {"id": 2, "title": "New User Signup", "message": "User john@example.com registered",
        "severity": "info", "source": "auth", "is_read": True,
        "is_active": True, "created_at": "2024-02-20T14:00:00"},
    3: {"id": 3, "title": "Payment Failed", "message": "Invoice #1234 payment declined",
        "severity": "warning", "source": "billing", "is_read": False,
        "is_active": True, "created_at": "2024-03-10T09:15:00"},
    4: {"id": 4, "title": "Disk Space Low", "message": "Disk usage at 95%",
        "severity": "critical", "source": "monitoring", "is_read": False,
        "is_active": True, "created_at": "2024-04-05T16:45:00"},
    5: {"id": 5, "title": "Weekly Report Ready", "message": "Analytics report for last week is available",
        "severity": "info", "source": "analytics", "is_read": True,
        "is_active": False, "created_at": "2024-05-12T11:20:00"},
}
_next_id = 6


class AlertCreate(BaseModel):
    title: str
    message: str
    severity: str = "info"
    source: str = ""
    is_read: bool = False
    is_active: bool = True


class AlertUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    severity: Optional[str] = None
    source: Optional[str] = None
    is_read: Optional[bool] = None
    is_active: Optional[bool] = None


class AlertResponse(BaseModel):
    id: int
    title: str
    message: str
    severity: str
    source: str
    is_read: bool
    is_active: bool
    created_at: str


@router.get("/", response_model=list[AlertResponse])
async def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    severity: Optional[str] = None,
    source: Optional[str] = None,
    is_read: Optional[bool] = None,
    is_active: Optional[bool] = None,
 -> list[AlertResponse]:
    """List all alerts with pagination and optional filters."""
    try:
        alerts = list(_alerts_db.values())
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]
        if source:
            alerts = [a for a in alerts if a["source"] == source]
        if is_read is not None:
            alerts = [a for a in alerts if a["is_read"] == is_read]
        if is_active is not None:
            alerts = [a for a in alerts if a["is_active"] == is_active]
        return alerts[skip : skip + limit]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: int) -> AlertResponse:
    """Get a single alert by ID."""
    try:
        alert = _alerts_db.get(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        return alert
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=AlertResponse, status_code=201)
async def create_alert(alert: AlertCreate) -> AlertResponse:
    """Create a new alert."""
    try:
        global _next_id
        new_alert = {
            "id": _next_id,
            "title": alert.title,
            "message": alert.message,
            "severity": alert.severity,
            "source": alert.source,
            "is_read": alert.is_read,
            "is_active": alert.is_active,
            "created_at": datetime.utcnow().isoformat(),
        }
        _alerts_db[_next_id] = new_alert
        _next_id += 1
        return new_alert
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(alert_id: int, alert: AlertUpdate) -> AlertResponse:
    """Update an existing alert."""
    try:
        existing = _alerts_db.get(alert_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        for field, value in alert.model_dump(exclude_unset=True).items():
            existing[field] = value
        return existing
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(alert_id: int) -> None:
    """Delete an alert by ID."""
    try:
        if alert_id not in _alerts_db:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        del _alerts_db[alert_id]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
