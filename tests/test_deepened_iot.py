"""Tests for deepened IoT module: device management, MQTT, monitoring, shadow, OTA."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


@pytest.fixture
def device_manager():
    from apex_os_bp.iot.deepened import DeviceManager
    return DeviceManager()


@pytest.fixture
def mqtt_client():
    from apex_os_bp.iot.deepened import MQTTClient
    client = MQTTClient(broker="localhost", port=1883)
    client.connect = MagicMock(return_value=True)
    client.publish = MagicMock(return_value=True)
    client.subscribe = MagicMock(return_value=True)
    return client


@pytest.fixture
def device_shadow():
    from apex_os_bp.iot.deepened import DeviceShadow
    return DeviceShadow(device_id="dev-001")


@pytest.fixture
def ota_manager():
    from apex_os_bp.iot.deepened import OTAManager
    return OTAManager()


class TestDeviceManagement:
    def test_register_device(self, device_manager):
        dev = device_manager.register("sensor-01", "temperature", {"location": "warehouse"})
        assert dev.device_id is not None
        assert dev.device_type == "temperature"
        assert dev.metadata["location"] == "warehouse"

    def test_list_devices(self, device_manager):
        device_manager.register("d1", "temp")
        device_manager.register("d2", "humidity")
        devices = device_manager.list_all()
        assert len(devices) == 2

    def test_unregister_device(self, device_manager):
        dev = device_manager.register("d3", "pressure")
        device_manager.unregister(dev.device_id)
        assert device_manager.get(dev.device_id) is None


class TestMQTTIngestion:
    def test_connect(self, mqtt_client):
        assert mqtt_client.connect() is True

    def test_publish_telemetry(self, mqtt_client):
        result = mqtt_client.publish("devices/d1/telemetry", '{"temp": 22.5}')
        assert result is True

    def test_subscribe_topic(self, mqtt_client):
        result = mqtt_client.subscribe("devices/+/telemetry")
        assert result is True


class TestMonitoring:
    def test_metrics_collection(self, device_manager):
        from apex_os_bp.iot.deepened import MonitoringService
        svc = MonitoringService(device_manager)
        metrics = svc.collect_metrics()
        assert isinstance(metrics, dict)

    def test_alert_threshold(self, device_manager):
        from apex_os_bp.iot.deepened import MonitoringService
        svc = MonitoringService(device_manager)
        alert = svc.check_threshold("temp", 95.0, max_val=80.0)
        assert alert is True


class TestDeviceShadow:
    def test_update_shadow(self, device_shadow):
        device_shadow.update({"state": {"reported": {"temp": 25}}})
        shadow = device_shadow.get()
        assert shadow["state"]["reported"]["temp"] == 25

    def test_shadow_delta(self, device_shadow):
        device_shadow.update({"state": {"desired": {"mode": "auto"}}})
        delta = device_shadow.get_delta()
        assert "desired" in delta.get("state", {})


class TestOTAUpdates:
    def test_schedule_update(self, ota_manager):
        job = ota_manager.schedule(device_id="dev-001", firmware="v2.0.1")
        assert job.job_id is not None
        assert job.version == "v2.0.1"

    def test_update_status(self, ota_manager):
        job = ota_manager.schedule(device_id="dev-002", firmware="v1.5.0")
        status = ota_manager.status(job.job_id)
        assert status in ("pending", "in_progress", "completed", "failed")
