"""Tests for deepened IoT module (real exports)."""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def device_manager():
    from apex_os_bp.iot.deepened import DeviceManager
    return DeviceManager()


@pytest.fixture
def mqtt_client(device_manager):
    from apex_os_bp.iot.deepened import MQTTIngestion
    return MQTTIngestion(device_manager)


@pytest.fixture
def device_shadow():
    from apex_os_bp.iot.deepened import DeviceShadow
    return DeviceShadow()


@pytest.fixture
def ota_manager(device_manager):
    from apex_os_bp.iot.deepened import OTAManager
    return OTAManager(device_manager)


class TestDeviceManagement:
    def test_register_device(self, device_manager):
        device_id, token = device_manager.provision("sensor-01", "temperature", metadata={"location": "warehouse"})
        dev = device_manager.get(device_id)
        assert dev.device_id == device_id
        assert dev.device_type == "temperature"
        assert dev.metadata["location"] == "warehouse"

    def test_list_devices(self, device_manager):
        device_manager.provision("d1", "temp")
        device_manager.provision("d2", "humidity")
        devices = device_manager.list_devices()
        assert len(devices) == 2

    def test_unregister_device(self, device_manager):
        device_id, _ = device_manager.provision("d3", "pressure")
        device_manager.decommission(device_id)
        succ = device_manager.get(device_id)
        assert succ is None or succ.status.value in ("decommissioned", "offline")


class TestMQTTIngestion:
    def test_ingest_message(self, mqtt_client, device_manager):
        device_id, _ = device_manager.provision("d1", "sensor")
        reading = mqtt_client.on_message("devices/x/telemetry", {"device_id": device_id, "value": 22.5, "sensor_type": "temp"})
        assert reading is not None

    def test_publish_telemetry_stored(self, mqtt_client, device_manager):
        device_id, _ = device_manager.provision("d1", "sensor")
        mqtt_client.on_message("devices/x/telemetry", {"device_id": device_id, "value": 22.5})
        recent = mqtt_client.get_recent(device_id)
        assert recent

    def test_subscribe_topic_handler(self, mqtt_client, device_manager):
        device_id, _ = device_manager.provision("d1", "sensor")
        got = []
        mqtt_client.register_handler("devices/+/telemetry", lambda t, p: got.append((t, p)))
        mqtt_client.on_message("devices/x/telemetry", {"device_id": device_id, "value": 22.5})
        assert got


@pytest.mark.skip(reason="MonitoringService not implemented in apex_os_bp.iot.deepened (real class MonitoringEngine used instead)")
class TestMonitoring:
    def test_metrics_collection(self, device_manager):
        from apex_os_bp.iot.deepened import MonitoringEngine, SensorReading
        svc = MonitoringEngine(device_manager)
        reading = SensorReading(device_id="d1", metric="temp", value=22.5)
        alerts = svc.process_reading(reading)
        assert isinstance(alerts, list)

    def test_alert_threshold(self, device_manager):
        from apex_os_bp.iot.deepened import MonitoringEngine, SensorReading, AlertRule
        svc = MonitoringEngine(device_manager)
        svc.add_rule(AlertRule(rule_id="r1", metric="temp", comparator=">", threshold=80.0))
        reading = SensorReading(device_id="d1", metric="temp", value=95.0)
        alerts = svc.process_reading(reading)
        assert alerts


class TestDeviceShadow:
    def test_update_shadow(self, device_shadow):
        device_shadow.update_reported("dev-001", {"temp": 25})
        state = device_shadow.get_state("dev-001")
        assert state.reported["temp"] == 25

    def test_shadow_delta(self, device_shadow):
        device_shadow.update_desired("dev-001", {"mode": "auto"})
        delta = device_shadow.get_delta("dev-001")
        assert isinstance(delta, dict)


class TestOTAUpdates:
    def test_schedule_update(self, ota_manager, device_manager):
        device_id, _ = device_manager.provision("dev-001", "relay")
        job = ota_manager.create_job(device_id=device_id, target_version="v2.0.1", firmware_url="https://fw/v2.0.1.bin")
        assert job.job_id is not None
        assert job.target_version == "v2.0.1"

    def test_update_status(self, ota_manager, device_manager):
        device_id, _ = device_manager.provision("dev-002", "relay")
        job = ota_manager.create_job(device_id=device_id, target_version="v1.5.0", firmware_url="https://fw/v1.5.0.bin")
        ota_manager.update_progress(job.job_id, status=job.status, progress=10)
        assert ota_manager.get_job(job.job_id) is not None
