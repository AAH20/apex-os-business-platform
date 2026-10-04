"""Monitoring CRUD API endpoints for APEX-OS Business Platform."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

# ── In-memory data stores ─────────────────────────────────────────────────────

_monitors_db = {
    1: {"id": 1, "name": "API Server Health", "type": "http", "target": "https://api.example.com/health",
        "interval": 60, "status": "up", "last_check": "2024-06-01T10:00:00", "is_active": True},
    2: {"id": 2, "name": "Database Connection", "type": "tcp", "target": "db.internal:5432",
        "interval": 30, "status": "up", "last_check": "2024-06-01T10:01:00", "is_active": True},
    3: {"id": 3, "name": "Redis Cache", "type": "tcp", "target": "cache.internal:6379",
        "interval": 15, "status": "down", "last_check": "2024-06-01T09:58:00", "is_active": True},
    4: {"id": 4, "name": "Disk Usage", "type": "metric", "target": "/dev/sda1",
        "interval": 300, "status": "warning", "last_check": "2024-06-01T09:55:00", "is_active": True},
    5: {"id": 5, "name": "SSL Certificate", "type": "http", "target": "https://example.com",
        "interval": 86400, "status": "up", "last_check": "2024-06-01T08:00:00", "is_active": False},
}
_monitors_next_id = 6

_alert_rules_db = {
    1: {"id": 1, "name": "High CPU Usage", "condition": "cpu_percent > 90", "severity": "critical",
        "monitor_id": 1, "is_active": True, "created_at": "2024-01-10T08:00:00"},
    2: {"id": 2, "name": "Memory Leak", "condition": "mem_usage > 85%", "severity": "warning",
        "monitor_id": 1, "is_active": True, "created_at": "2024-02-15T09:30:00"},
    3: {"id": 3, "name": "Disk Full", "condition": "disk_usage > 95%", "severity": "critical",
        "monitor_id": 4, "is_active": True, "created_at": "2024-03-20T14:00:00"},
    4: {"id": 4, "name": "Response Time", "condition": "response_time > 2000ms", "severity": "warning",
        "monitor_id": 2, "is_active": False, "created_at": "2024-04-05T11:00:00"},
    5: {"id": 5, "name": "SSL Expiry", "condition": "cert_days_remaining < 30", "severity": "info",
        "monitor_id": 5, "is_active": True, "created_at": "2024-05-12T16:00:00"},
}
_alert_rules_next_id = 6

_dashboards_db = {
    1: {"id": 1, "name": "Infrastructure Overview", "description": "Core infra metrics",
        "widgets": 8, "refresh_rate": 30, "is_active": True, "created_at": "2024-01-05T10:00:00"},
    2: {"id": 2, "name": "Application Performance", "description": "APM dashboards",
        "widgets": 12, "refresh_rate": 10, "is_active": True, "created_at": "2024-02-10T12:00:00"},
    3: {"id": 3, "name": "Security Monitoring", "description": "Security events and alerts",
        "widgets": 6, "refresh_rate": 60, "is_active": True, "created_at": "2024-03-15T09:00:00"},
    4: {"id": 4, "name": "Business KPIs", "description": "Revenue, users, conversion",
        "widgets": 10, "refresh_rate": 300, "is_active": False, "created_at": "2024-04-20T14:00:00"},
}
_dashboards_next_id = 5

_metrics_db = {
    1: {"id": 1, "name": "cpu_usage", "unit": "percent", "value": 45.2, "timestamp": "2024-06-01T10:00:00", "monitor_id": 1},
    2: {"id": 2, "name": "memory_usage", "unit": "percent", "value": 72.8, "timestamp": "2024-06-01T10:00:00", "monitor_id": 1},
    3: {"id": 3, "name": "response_time", "unit": "ms", "value": 156, "timestamp": "2024-06-01T10:00:00", "monitor_id": 2},
    4: {"id": 4, "name": "disk_usage", "unit": "percent", "value": 88.5, "timestamp": "2024-06-01T10:00:00", "monitor_id": 4},
    5: {"id": 5, "name": "requests_per_sec", "unit": "rps", "value": 1250, "timestamp": "2024-06-01T10:00:00", "monitor_id": 1},
    6: {"id": 6, "name": "error_rate", "unit": "percent", "value": 0.12, "timestamp": "2024-06-01T10:00:00", "monitor_id": 2},
    7: {"id": 7, "name": "network_in", "unit": "mbps", "value": 340, "timestamp": "2024-06-01T10:00:00", "monitor_id": 1},
    8: {"id": 8, "name": "network_out", "unit": "mbps", "value": 180, "timestamp": "2024-06-01T10:00:00", "monitor_id": 1},
}
_metrics_next_id = 9


# ── Pydantic Models ───────────────────────────────────────────────────────────

class MonitorCreate(BaseModel):
    name: str
    type: str = "http"
    target: str = ""
    interval: int = 60
    is_active: bool = True


class MonitorUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    target: Optional[str] = None
    interval: Optional[int] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class MonitorResponse(BaseModel):
    id: int
    name: str
    type: str
    target: str
    interval: int
    status: str
    last_check: str
    is_active: bool


class AlertRuleCreate(BaseModel):
    name: str
    condition: str = ""
    severity: str = "warning"
    monitor_id: Optional[int] = None
    is_active: bool = True


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    condition: Optional[str] = None
    severity: Optional[str] = None
    monitor_id: Optional[int] = None
    is_active: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    id: int
    name: str
    condition: str
    severity: str
    monitor_id: Optional[int]
    is_active: bool
    created_at: str


class DashboardCreate(BaseModel):
    name: str
    description: str = ""
    widgets: int = 6
    refresh_rate: int = 30
    is_active: bool = True


class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    widgets: Optional[int] = None
    refresh_rate: Optional[int] = None
    is_active: Optional[bool] = None


class DashboardResponse(BaseModel):
    id: int
    name: str
    description: str
    widgets: int
    refresh_rate: int
    is_active: bool
    created_at: str


class MetricCreate(BaseModel):
    name: str
    unit: str = ""
    value: float = 0.0
    monitor_id: Optional[int] = None


class MetricUpdate(BaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    value: Optional[float] = None
    monitor_id: Optional[int] = None


class MetricResponse(BaseModel):
    id: int
    name: str
    unit: str
    value: float
    timestamp: str
    monitor_id: Optional[int]


# ── Monitor Endpoints ─────────────────────────────────────────────────────────

@router.get("/monitors", response_model=list[MonitorResponse])
async def list_monitors(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    """List all monitors with pagination and optional filters."""
    monitors = list(_monitors_db.values())
    if status:
        monitors = [m for m in monitors if m["status"] == status]
    if type:
        monitors = [m for m in monitors if m["type"] == type]
    if is_active is not None:
        monitors = [m for m in monitors if m["is_active"] == is_active]
    return monitors[skip : skip + limit]


@router.get("/monitors/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(monitor_id: int):
    """Get a single monitor by ID."""
    monitor = _monitors_db.get(monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail=f"Monitor {monitor_id} not found")
    return monitor


@router.post("/monitors", response_model=MonitorResponse, status_code=201)
async def create_monitor(monitor: MonitorCreate):
    """Create a new monitor."""
    global _monitors_next_id
    new_monitor = {
        "id": _monitors_next_id,
        "name": monitor.name,
        "type": monitor.type,
        "target": monitor.target,
        "interval": monitor.interval,
        "status": "unknown",
        "last_check": datetime.utcnow().isoformat(),
        "is_active": monitor.is_active,
    }
    _monitors_db[_monitors_next_id] = new_monitor
    _monitors_next_id += 1
    return new_monitor


@router.put("/monitors/{monitor_id}", response_model=MonitorResponse)
async def update_monitor(monitor_id: int, monitor: MonitorUpdate):
    """Update an existing monitor."""
    existing = _monitors_db.get(monitor_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Monitor {monitor_id} not found")
    for field, value in monitor.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing


@router.delete("/monitors/{monitor_id}", status_code=204)
async def delete_monitor(monitor_id: int):
    """Delete a monitor by ID."""
    if monitor_id not in _monitors_db:
        raise HTTPException(status_code=404, detail=f"Monitor {monitor_id} not found")
    del _monitors_db[monitor_id]


# ── Alert Rule Endpoints ──────────────────────────────────────────────────────

@router.get("/alert-rules", response_model=list[AlertRuleResponse])
async def list_alert_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    severity: Optional[str] = None,
    monitor_id: Optional[int] = None,
    is_active: Optional[bool] = None,
):
    """List all alert rules with pagination and optional filters."""
    rules = list(_alert_rules_db.values())
    if severity:
        rules = [r for r in rules if r["severity"] == severity]
    if monitor_id is not None:
        rules = [r for r in rules if r.get("monitor_id") == monitor_id]
    if is_active is not None:
        rules = [r for r in rules if r["is_active"] == is_active]
    return rules[skip : skip + limit]


@router.get("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(rule_id: int):
    """Get a single alert rule by ID."""
    rule = _alert_rules_db.get(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Alert rule {rule_id} not found")
    return rule


@router.post("/alert-rules", response_model=AlertRuleResponse, status_code=201)
async def create_alert_rule(rule: AlertRuleCreate):
    """Create a new alert rule."""
    global _alert_rules_next_id
    new_rule = {
        "id": _alert_rules_next_id,
        "name": rule.name,
        "condition": rule.condition,
        "severity": rule.severity,
        "monitor_id": rule.monitor_id,
        "is_active": rule.is_active,
        "created_at": datetime.utcnow().isoformat(),
    }
    _alert_rules_db[_alert_rules_next_id] = new_rule
    _alert_rules_next_id += 1
    return new_rule


@router.put("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(rule_id: int, rule: AlertRuleUpdate):
    """Update an existing alert rule."""
    existing = _alert_rules_db.get(rule_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Alert rule {rule_id} not found")
    for field, value in rule.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing


@router.delete("/alert-rules/{rule_id}", status_code=204)
async def delete_alert_rule(rule_id: int):
    """Delete an alert rule by ID."""
    if rule_id not in _alert_rules_db:
        raise HTTPException(status_code=404, detail=f"Alert rule {rule_id} not found")
    del _alert_rules_db[rule_id]


# ── Dashboard Endpoints ───────────────────────────────────────────────────────

@router.get("/dashboards", response_model=list[DashboardResponse])
async def list_dashboards(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_active: Optional[bool] = None,
):
    """List all dashboards with pagination and optional filters."""
    dashboards = list(_dashboards_db.values())
    if is_active is not None:
        dashboards = [d for d in dashboards if d["is_active"] == is_active]
    return dashboards[skip : skip + limit]


@router.get("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(dashboard_id: int):
    """Get a single dashboard by ID."""
    dashboard = _dashboards_db.get(dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    return dashboard


@router.post("/dashboards", response_model=DashboardResponse, status_code=201)
async def create_dashboard(dashboard: DashboardCreate):
    """Create a new dashboard."""
    global _dashboards_next_id
    new_dashboard = {
        "id": _dashboards_next_id,
        "name": dashboard.name,
        "description": dashboard.description,
        "widgets": dashboard.widgets,
        "refresh_rate": dashboard.refresh_rate,
        "is_active": dashboard.is_active,
        "created_at": datetime.utcnow().isoformat(),
    }
    _dashboards_db[_dashboards_next_id] = new_dashboard
    _dashboards_next_id += 1
    return new_dashboard


@router.put("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(dashboard_id: int, dashboard: DashboardUpdate):
    """Update an existing dashboard."""
    existing = _dashboards_db.get(dashboard_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    for field, value in dashboard.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing


@router.delete("/dashboards/{dashboard_id}", status_code=204)
async def delete_dashboard(dashboard_id: int):
    """Delete a dashboard by ID."""
    if dashboard_id not in _dashboards_db:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    del _dashboards_db[dashboard_id]


# ── Metric Endpoints ──────────────────────────────────────────────────────────

@router.get("/metrics", response_model=list[MetricResponse])
async def list_metrics(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    monitor_id: Optional[int] = None,
    name: Optional[str] = None,
):
    """List all metrics with pagination and optional filters."""
    metrics = list(_metrics_db.values())
    if monitor_id is not None:
        metrics = [m for m in metrics if m.get("monitor_id") == monitor_id]
    if name:
        metrics = [m for m in metrics if m["name"] == name]
    return metrics[skip : skip + limit]


@router.get("/metrics/{metric_id}", response_model=MetricResponse)
async def get_metric(metric_id: int):
    """Get a single metric by ID."""
    metric = _metrics_db.get(metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail=f"Metric {metric_id} not found")
    return metric


@router.post("/metrics", response_model=MetricResponse, status_code=201)
async def create_metric(metric: MetricCreate):
    """Create a new metric."""
    global _metrics_next_id
    new_metric = {
        "id": _metrics_next_id,
        "name": metric.name,
        "unit": metric.unit,
        "value": metric.value,
        "timestamp": datetime.utcnow().isoformat(),
        "monitor_id": metric.monitor_id,
    }
    _metrics_db[_metrics_next_id] = new_metric
    _metrics_next_id += 1
    return new_metric


@router.put("/metrics/{metric_id}", response_model=MetricResponse)
async def update_metric(metric_id: int, metric: MetricUpdate):
    """Update an existing metric."""
    existing = _metrics_db.get(metric_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Metric {metric_id} not found")
    for field, value in metric.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing


@router.delete("/metrics/{metric_id}", status_code=204)
async def delete_metric(metric_id: int):
    """Delete a metric by ID."""
    if metric_id not in _metrics_db:
        raise HTTPException(status_code=404, detail=f"Metric {metric_id} not found")
    del _metrics_db[metric_id]
