"""APEX-OS IoT Deepened Module: device management, MQTT ingestion,
real-time monitoring, device shadow, and OTA firmware updates."""
from __future__ import annotations
import hashlib, logging, time, uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

class DeviceStatus(str, Enum):
    OFFLINE = "offline"; ONLINE = "online"; PROVISIONING = "provisioning"
    SUSPENDED = "suspended"; DECOMMISSIONED = "decommissioned"

class AlertSeverity(str, Enum):
    INFO = "info"; WARNING = "warning"; CRITICAL = "critical"

class OTAStatus(str, Enum):
    PENDING = "pending"; DOWNLOADING = "downloading"; INSTALLING = "installing"
    REBOOTING = "rebooting"; COMPLETED = "completed"; FAILED = "failed"; ROLLED_BACK = "rolled_back"

@dataclass
class Device:
    device_id: str; name: str; device_type: str
    status: DeviceStatus = DeviceStatus.OFFLINE
    firmware_version: str = "1.0.0"
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_seen: float = 0.0; shadow_version: int = 0
    def to_dict(self) -> dict:
        return {k: (v.value if isinstance(v, Enum) else v) for k, v in self.__dict__.items()}

@dataclass
class SensorReading:
    device_id: str; sensor_type: str; value: float; unit: str
    timestamp: float = field(default_factory=time.time); quality: float = 1.0
    def to_dict(self) -> dict:
        return dict(self.__dict__)

@dataclass
class AlertRule:
    rule_id: str; name: str; device_id: Optional[str]; sensor_type: str
    condition: str; threshold: float; severity: AlertSeverity
    enabled: bool = True; cooldown_seconds: int = 300; _last_triggered: float = 0.0
    def evaluate(self, reading: SensorReading) -> bool:
        if not self.enabled: return False
        if self.device_id and reading.device_id != self.device_id: return False
        if reading.sensor_type != self.sensor_type: return False
        ops = {"gt": lambda v, t: v > t, "lt": lambda v, t: v < t,
               "eq": lambda v, t: v == t, "gte": lambda v, t: v >= t, "lte": lambda v, t: v <= t}
        op = ops.get(self.condition)
        return bool(op and op(reading.value, self.threshold))

@dataclass
class Alert:
    alert_id: str; rule_id: str; device_id: str; severity: AlertSeverity
    message: str; reading: SensorReading
    timestamp: float = field(default_factory=time.time); acknowledged: bool = False

@dataclass
class ShadowState:
    device_id: str
    reported: Dict[str, Any] = field(default_factory=dict)
    desired: Dict[str, Any] = field(default_factory=dict)
    version: int = 0; last_updated: float = field(default_factory=time.time)
    def delta(self) -> Dict[str, Any]:
        return {k: v for k, v in self.desired.items() if self.reported.get(k) != v}
    def apply_reported(self, patch: Dict[str, Any]) -> None:
        self.reported.update(patch); self.version += 1; self.last_updated = time.time()
    def apply_desired(self, patch: Dict[str, Any]) -> None:
        self.desired.update(patch); self.version += 1; self.last_updated = time.time()

@dataclass
class OTAJob:
    job_id: str; device_id: str; target_version: str; firmware_url: str
    status: OTAStatus = OTAStatus.PENDING; progress: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0; completed_at: float = 0.0; error: str = ""

class DeviceManager:
    def __init__(self):
        self._devices: Dict[str, Device] = {}; self._tokens: Dict[str, str] = {}
    def provision(self, name: str, device_type: str,
                  tags: Optional[Dict[str, str]] = None,
                  metadata: Optional[Dict[str, Any]] = None) -> tuple[str, str]:
        device_id = f"dev_{uuid.uuid4().hex[:12]}"
        token = hashlib.sha256(f"{device_id}:{time.time()}:{uuid.uuid4()}".encode()).hexdigest()
        self._devices[device_id] = Device(device_id=device_id, name=name, device_type=device_type,
            status=DeviceStatus.PROVISIONING, tags=tags or {}, metadata=metadata or {})
        self._tokens[token] = device_id
        return device_id, token
    def activate(self, device_id: str, token: str) -> bool:
        if self._tokens.get(token) != device_id: return False
        device = self._devices.get(device_id)
        if not device: return False
        device.status = DeviceStatus.ONLINE; device.last_seen = time.time()
        del self._tokens[token]; return True
    def get(self, device_id: str) -> Optional[Device]:
        return self._devices.get(device_id)
    def list_devices(self, status: Optional[DeviceStatus] = None,
                     device_type: Optional[str] = None) -> List[Device]:
        devices = list(self._devices.values())
        if status: devices = [d for d in devices if d.status == status]
        if device_type: devices = [d for d in devices if d.device_type == device_type]
        return devices
    def update_status(self, device_id: str, status: DeviceStatus) -> bool:
        device = self._devices.get(device_id)
        if not device: return False
        device.status = status
        if status == DeviceStatus.ONLINE: device.last_seen = time.time()
        return True
    def heartbeat(self, device_id: str) -> bool:
        device = self._devices.get(device_id)
        if not device: return False
        device.last_seen = time.time()
        if device.status == DeviceStatus.OFFLINE: device.status = DeviceStatus.ONLINE
        return True
    def decommission(self, device_id: str) -> bool:
        device = self._devices.get(device_id)
        if not device: return False
        device.status = DeviceStatus.DECOMMISSIONED; return True
    def update_firmware_version(self, device_id: str, version: str) -> bool:
        device = self._devices.get(device_id)
        if not device: return False
        device.firmware_version = version; return True

class MQTTIngestion:
    def __init__(self, device_manager: DeviceManager):
        self._dm = device_manager; self._handlers: Dict[str, Callable] = {}
        self._readings: List[SensorReading] = []; self._max_buffer = 10_000
    def register_handler(self, topic_pattern: str, handler: Callable[[str, dict], None]) -> None:
        self._handlers[topic_pattern] = handler
    def on_message(self, topic: str, payload: dict) -> Optional[SensorReading]:
        device_id = payload.get("device_id", "")
        if not self._dm.get(device_id): return None
        self._dm.heartbeat(device_id)
        reading = SensorReading(device_id=device_id, sensor_type=payload.get("sensor_type", "unknown"),
            value=float(payload.get("value", 0)), unit=payload.get("unit", ""),
            quality=float(payload.get("quality", 1.0)))
        self._readings.append(reading)
        if len(self._readings) > self._max_buffer: self._readings = self._readings[-self._max_buffer:]
        for pattern, handler in self._handlers.items():
            if self._topic_matches(pattern, topic): handler(topic, payload)
        return reading
    def _topic_matches(self, pattern: str, topic: str) -> bool:
        pp, tp = pattern.split("/"), topic.split("/")
        for i, p in enumerate(pp):
            if p == "#": return True
            if i >= len(tp): return False
            if p != "+" and p != tp[i]: return False
        return len(pp) == len(tp)
    def get_recent(self, device_id: Optional[str] = None, limit: int = 100) -> List[SensorReading]:
        readings = self._readings
        if device_id: readings = [r for r in readings if r.device_id == device_id]
        return readings[-limit:]

class MonitoringEngine:
    def __init__(self, device_manager: DeviceManager):
        self._dm = device_manager; self._rules: Dict[str, AlertRule] = {}
        self._alerts: List[Alert] = []; self._notifiers: List[Callable[[Alert], None]] = []
    def add_rule(self, rule: AlertRule) -> None: self._rules[rule.rule_id] = rule
    def remove_rule(self, rule_id: str) -> bool: return self._rules.pop(rule_id, None) is not None
    def add_notifier(self, notifier: Callable[[Alert], None]) -> None: self._notifiers.append(notifier)
    def process_reading(self, reading: SensorReading) -> List[Alert]:
        triggered = []
        for rule in self._rules.values():
            if not rule.evaluate(reading): continue
            now = time.time()
            if now - rule._last_triggered < rule.cooldown_seconds: continue
            rule._last_triggered = now
            alert = Alert(alert_id=f"alert_{uuid.uuid4().hex[:8]}", rule_id=rule.rule_id,
                device_id=reading.device_id, severity=rule.severity,
                message=f"[{rule.severity.value.upper()}] {rule.name}: "
                      f"{reading.sensor_type}={reading.value}{reading.unit} "
                      f"(threshold {rule.condition} {rule.threshold})", reading=reading)
            self._alerts.append(alert); triggered.append(alert)
            for notifier in self._notifiers:
                try: notifier(alert)
                except Exception: logger.exception("Notifier failed for %s", alert.alert_id)
        return triggered
    def get_alerts(self, device_id: Optional[str] = None,
                   severity: Optional[AlertSeverity] = None,
                   unacknowledged_only: bool = False) -> List[Alert]:
        alerts = self._alerts
        if device_id: alerts = [a for a in alerts if a.device_id == device_id]
        if severity: alerts = [a for a in alerts if a.severity == severity]
        if unacknowledged_only: alerts = [a for a in alerts if not a.acknowledged]
        return alerts
    def acknowledge(self, alert_id: str) -> bool:
        for alert in self._alerts:
            if alert.alert_id == alert_id: alert.acknowledged = True; return True
        return False

class DeviceShadow:
    def __init__(self): self._states: Dict[str, ShadowState] = {}
    def get_or_create(self, device_id: str) -> ShadowState:
        if device_id not in self._states:
            self._states[device_id] = ShadowState(device_id=device_id)
        return self._states[device_id]
    def update_reported(self, device_id: str, patch: Dict[str, Any]) -> ShadowState:
        state = self.get_or_create(device_id); state.apply_reported(patch); return state
    def update_desired(self, device_id: str, patch: Dict[str, Any]) -> ShadowState:
        state = self.get_or_create(device_id); state.apply_desired(patch); return state
    def get_delta(self, device_id: str) -> Dict[str, Any]:
        state = self._states.get(device_id); return state.delta() if state else {}
    def get_state(self, device_id: str) -> Optional[ShadowState]: return self._states.get(device_id)
    def delete(self, device_id: str) -> bool: return self._states.pop(device_id, None) is not None

class OTAManager:
    def __init__(self, device_manager: DeviceManager):
        self._dm = device_manager; self._jobs: Dict[str, OTAJob] = {}; self._device_jobs: Dict[str, str] = {}
    def create_job(self, device_id: str, target_version: str, firmware_url: str) -> Optional[OTAJob]:
        if not self._dm.get(device_id): return None
        if device_id in self._device_jobs:
            existing = self._jobs.get(self._device_jobs[device_id])
            if existing and existing.status not in (OTAStatus.COMPLETED, OTAStatus.FAILED, OTAStatus.ROLLED_BACK):
                return None
        job = OTAJob(job_id=f"ota_{uuid.uuid4().hex[:8]}", device_id=device_id,
                     target_version=target_version, firmware_url=firmware_url)
        self._jobs[job.job_id] = job; self._device_jobs[device_id] = job_id; return job
    def update_progress(self, job_id: str, status: OTAStatus, progress: int = 0, error: str = "") -> bool:
        job = self._jobs.get(job_id)
        if not job: return False
        job.status = status; job.progress = max(0, min(100, progress))
        if error: job.error = error
        if status in (OTAStatus.COMPLETED, OTAStatus.FAILED, OTAStatus.ROLLED_BACK):
            job.completed_at = time.time()
            if status == OTAStatus.COMPLETED: self._dm.update_firmware_version(job.device_id, job.target_version)
        if status == OTAStatus.DOWNLOADING and not job.started_at: job.started_at = time.time()
        return True
    def get_job(self, job_id: str) -> Optional[OTAJob]: return self._jobs.get(job_id)
    def get_device_job(self, device_id: str) -> Optional[OTAJob]:
        job_id = self._device_jobs.get(device_id); return self._jobs.get(job_id) if job_id else None
    def list_jobs(self, status: Optional[OTAStatus] = None) -> List[OTAJob]:
        jobs = list(self._jobs.values())
        if status: jobs = [j for j in jobs if j.status == status]
        return jobs
    def rollback(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job: return False
        job.status = OTAStatus.ROLLED_BACK; job.completed_at = time.time(); return True

class IoTModule:
    def __init__(self):
        self.devices = DeviceManager(); self.ingestion = MQTTIngestion(self.devices)
        self.monitoring = MonitoringEngine(self.devices); self.shadow = DeviceShadow()
        self.ota = OTAManager(self.devices)
    def provision_device(self, name: str, device_type: str, **kwargs) -> tuple[str, str]:
        return self.devices.provision(name, device_type, **kwargs)
    def ingest(self, topic: str, payload: dict) -> Optional[SensorReading]:
        reading = self.ingestion.on_message(topic, payload)
        if reading: self.monitoring.process_reading(reading)
        return reading
    def update_shadow(self, device_id: str, reported: Optional[dict] = None,
                      desired: Optional[dict] = None) -> ShadowState:
        state = self.shadow.get_or_create(device_id)
        if reported: state.apply_reported(reported)
        if desired: state.apply_desired(desired)
        return state
    def start_ota(self, device_id: str, target_version: str, firmware_url: str) -> Optional[OTAJob]:
        return self.ota.create_job(device_id, target_version, firmware_url)
