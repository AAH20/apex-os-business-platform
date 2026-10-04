"""IoT CRUD API endpoints for APEX-OS Business Platform."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/iot", tags=["iot"])

# ── In-memory DBs ─────────────────────────────────────────────────────────────

_devices_db = {
    1: {"id": 1, "name": "Temp Sensor A1", "type": "temperature", "status": "active", "location": "Warehouse 1", "group_id": 1, "last_seen": "2024-06-01T10:00:00"},
    2: {"id": 2, "name": "Humidity Sensor B2", "type": "humidity", "status": "active", "location": "Warehouse 2", "group_id": 1, "last_seen": "2024-06-01T10:05:00"},
    3: {"id": 3, "name": "Pressure Valve C3", "type": "pressure", "status": "inactive", "location": "Factory Floor", "group_id": 2, "last_seen": "2024-05-30T14:00:00"},
}
_sensors_db = {
    1: {"id": 1, "device_id": 1, "name": "Temp Probe 1", "unit": "°C", "min_val": -40.0, "max_val": 125.0, "calibration_date": "2024-01-15"},
    2: {"id": 2, "device_id": 2, "name": "Humidity Probe 1", "unit": "%RH", "min_val": 0.0, "max_val": 100.0, "calibration_date": "2024-02-10"},
    3: {"id": 3, "device_id": 3, "name": "Pressure Gauge 1", "unit": "bar", "min_val": 0.0, "max_val": 10.0, "calibration_date": "2024-03-05"},
}
_telemetry_db = {
    1: {"id": 1, "sensor_id": 1, "value": 23.5, "timestamp": "2024-06-01T10:00:00", "quality": "good"},
    2: {"id": 2, "sensor_id": 1, "value": 24.1, "timestamp": "2024-06-01T10:05:00", "quality": "good"},
    3: {"id": 3, "sensor_id": 2, "value": 65.0, "timestamp": "2024-06-01T10:05:00", "quality": "good"},
    4: {"id": 4, "sensor_id": 3, "value": 4.2, "timestamp": "2024-05-30T14:00:00", "quality": "fair"},
}
_alerts_db = {
    1: {"id": 1, "device_id": 1, "rule": "temp > 30", "severity": "warning", "message": "Temperature exceeded threshold", "is_active": True, "created_at": "2024-06-01T09:00:00"},
    2: {"id": 2, "device_id": 3, "rule": "pressure < 1", "severity": "critical", "message": "Pressure critically low", "is_active": True, "created_at": "2024-05-30T13:00:00"},
}
_groups_db = {
    1: {"id": 1, "name": "Climate Sensors", "description": "Temperature and humidity monitoring", "color": "#06b6d4"},
    2: {"id": 2, "name": "Industrial Valves", "description": "Pressure and flow control", "color": "#a855f7"},
}

_next_ids = {"device": 4, "sensor": 4, "telemetry": 5, "alert": 3, "group": 3}

# ── Pydantic Models ──────────────────────────────────────────────────────────

class DeviceCreate(BaseModel):
    name: str
    type: str
    status: str = "active"
    location: str = ""
    group_id: Optional[int] = None

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    group_id: Optional[int] = None

class DeviceResponse(BaseModel):
    id: int
    name: str
    type: str
    status: str
    location: str
    group_id: Optional[int] = None
    last_seen: str

class SensorCreate(BaseModel):
    device_id: int
    name: str
    unit: str
    min_val: float = 0.0
    max_val: float = 100.0
    calibration_date: Optional[str] = None

class SensorUpdate(BaseModel):
    device_id: Optional[int] = None
    name: Optional[str] = None
    unit: Optional[str] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    calibration_date: Optional[str] = None

class SensorResponse(BaseModel):
    id: int
    device_id: int
    name: str
    unit: str
    min_val: float
    max_val: float
    calibration_date: Optional[str] = None

class TelemetryCreate(BaseModel):
    sensor_id: int
    value: float
    quality: str = "good"

class TelemetryUpdate(BaseModel):
    sensor_id: Optional[int] = None
    value: Optional[float] = None
    quality: Optional[str] = None

class TelemetryResponse(BaseModel):
    id: int
    sensor_id: int
    value: float
    timestamp: str
    quality: str

class AlertCreate(BaseModel):
    device_id: int
    rule: str
    severity: str = "warning"
    message: str = ""
    is_active: bool = True

class AlertUpdate(BaseModel):
    device_id: Optional[int] = None
    rule: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    is_active: Optional[bool] = None

class AlertResponse(BaseModel):
    id: int
    device_id: int
    rule: str
    severity: str
    message: str
    is_active: bool
    created_at: str

class GroupCreate(BaseModel):
    name: str
    description: str = ""
    color: str = "#06b6d4"

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None

class GroupResponse(BaseModel):
    id: int
    name: str
    description: str
    color: str

# ── Helper ───────────────────────────────────────────────────────────────────

def _get_db_and_model(kind: str):
    dbs = {"device": _devices_db, "sensor": _sensors_db, "telemetry": _telemetry_db, "alert": _alerts_db, "group": _groups_db}
    models = {"device": DeviceResponse, "sensor": SensorResponse, "telemetry": TelemetryResponse, "alert": AlertResponse, "group": GroupResponse}
    return dbs[kind], models[kind]

# ── Device CRUD ──────────────────────────────────────────────────────────────

@router.get("/devices/", response_model=list[DeviceResponse])
async def list_devices(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100), status: Optional[str] = None, type: Optional[str] = None):
    devices = list(_devices_db.values())
    if status:
        devices = [d for d in devices if d["status"] == status]
    if type:
        devices = [d for d in devices if d["type"] == type]
    return devices[skip : skip + limit]

@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: int):
    device = _devices_db.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    return device

@router.post("/devices/", response_model=DeviceResponse, status_code=201)
async def create_device(device: DeviceCreate):
    global _next_ids
    new_device = {"id": _next_ids["device"], **device.model_dump(), "last_seen": datetime.utcnow().isoformat()}
    _devices_db[_next_ids["device"]] = new_device
    _next_ids["device"] += 1
    return new_device

@router.put("/devices/{device_id}", response_model=DeviceResponse)
async def update_device(device_id: int, device: DeviceUpdate):
    existing = _devices_db.get(device_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    for field, value in device.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing

@router.delete("/devices/{device_id}", status_code=204)
async def delete_device(device_id: int):
    if device_id not in _devices_db:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    del _devices_db[device_id]

# ── Sensor CRUD ──────────────────────────────────────────────────────────────

@router.get("/sensors/", response_model=list[SensorResponse])
async def list_sensors(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100), device_id: Optional[int] = None):
    sensors = list(_sensors_db.values())
    if device_id:
        sensors = [s for s in sensors if s["device_id"] == device_id]
    return sensors[skip : skip + limit]

@router.get("/sensors/{sensor_id}", response_model=SensorResponse)
async def get_sensor(sensor_id: int):
    sensor = _sensors_db.get(sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found")
    return sensor

@router.post("/sensors/", response_model=SensorResponse, status_code=201)
async def create_sensor(sensor: SensorCreate):
    global _next_ids
    new_sensor = {"id": _next_ids["sensor"], **sensor.model_dump()}
    _sensors_db[_next_ids["sensor"]] = new_sensor
    _next_ids["sensor"] += 1
    return new_sensor

@router.put("/sensors/{sensor_id}", response_model=SensorResponse)
async def update_sensor(sensor_id: int, sensor: SensorUpdate):
    existing = _sensors_db.get(sensor_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found")
    for field, value in sensor.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing

@router.delete("/sensors/{sensor_id}", status_code=204)
async def delete_sensor(sensor_id: int):
    if sensor_id not in _sensors_db:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found")
    del _sensors_db[sensor_id]

# ── Telemetry CRUD ───────────────────────────────────────────────────────────

@router.get("/telemetry/", response_model=list[TelemetryResponse])
async def list_telemetry(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100), sensor_id: Optional[int] = None):
    telemetry = list(_telemetry_db.values())
    if sensor_id:
        telemetry = [t for t in telemetry if t["sensor_id"] == sensor_id]
    return telemetry[skip : skip + limit]

@router.get("/telemetry/{telemetry_id}", response_model=TelemetryResponse)
async def get_telemetry(telemetry_id: int):
    entry = _telemetry_db.get(telemetry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Telemetry {telemetry_id} not found")
    return entry

@router.post("/telemetry/", response_model=TelemetryResponse, status_code=201)
async def create_telemetry(telemetry: TelemetryCreate):
    global _next_ids
    new_entry = {"id": _next_ids["telemetry"], **telemetry.model_dump(), "timestamp": datetime.utcnow().isoformat()}
    _telemetry_db[_next_ids["telemetry"]] = new_entry
    _next_ids["telemetry"] += 1
    return new_entry

@router.put("/telemetry/{telemetry_id}", response_model=TelemetryResponse)
async def update_telemetry(telemetry_id: int, telemetry: TelemetryUpdate):
    existing = _telemetry_db.get(telemetry_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Telemetry {telemetry_id} not found")
    for field, value in telemetry.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing

@router.delete("/telemetry/{telemetry_id}", status_code=204)
async def delete_telemetry(telemetry_id: int):
    if telemetry_id not in _telemetry_db:
        raise HTTPException(status_code=404, detail=f"Telemetry {telemetry_id} not found")
    del _telemetry_db[telemetry_id]

# ── Alert CRUD ───────────────────────────────────────────────────────────────

@router.get("/alerts/", response_model=list[AlertResponse])
async def list_alerts(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100), severity: Optional[str] = None, is_active: Optional[bool] = None):
    alerts = list(_alerts_db.values())
    if severity:
        alerts = [a for a in alerts if a["severity"] == severity]
    if is_active is not None:
        alerts = [a for a in alerts if a["is_active"] == is_active]
    return alerts[skip : skip + limit]

@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: int):
    alert = _alerts_db.get(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return alert

@router.post("/alerts/", response_model=AlertResponse, status_code=201)
async def create_alert(alert: AlertCreate):
    global _next_ids
    new_alert = {"id": _next_ids["alert"], **alert.model_dump(), "created_at": datetime.utcnow().isoformat()}
    _alerts_db[_next_ids["alert"]] = new_alert
    _next_ids["alert"] += 1
    return new_alert

@router.put("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(alert_id: int, alert: AlertUpdate):
    existing = _alerts_db.get(alert_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    for field, value in alert.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing

@router.delete("/alerts/{alert_id}", status_code=204)
async def delete_alert(alert_id: int):
    if alert_id not in _alerts_db:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    del _alerts_db[alert_id]

# ── Device Group CRUD ────────────────────────────────────────────────────────

@router.get("/groups/", response_model=list[GroupResponse])
async def list_groups(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    groups = list(_groups_db.values())
    return groups[skip : skip + limit]

@router.get("/groups/{group_id}", response_model=GroupResponse)
async def get_group(group_id: int):
    group = _groups_db.get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail=f"Group {group_id} not found")
    return group

@router.post("/groups/", response_model=GroupResponse, status_code=201)
async def create_group(group: GroupCreate):
    global _next_ids
    new_group = {"id": _next_ids["group"], **group.model_dump()}
    _groups_db[_next_ids["group"]] = new_group
    _next_ids["group"] += 1
    return new_group

@router.put("/groups/{group_id}", response_model=GroupResponse)
async def update_group(group_id: int, group: GroupUpdate):
    existing = _groups_db.get(group_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Group {group_id} not found")
    for field, value in group.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing

@router.delete("/groups/{group_id}", status_code=204)
async def delete_group(group_id: int):
    if group_id not in _groups_db:
        raise HTTPException(status_code=404, detail=f"Group {group_id} not found")
    del _groups_db[group_id]
