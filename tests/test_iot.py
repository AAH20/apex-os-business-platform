"""Comprehensive tests for the IoT platform modules."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from apex_os_bp.iot.device_manager import (
    DeviceManager,
    Device,
    DeviceStatus,
    DeviceType,
)
from apex_os_bp.iot.data_ingestion import (
    DataIngestion,
    SensorReading,
    IngestionResult,
    IngestionStatus,
)
from apex_os_bp.iot.analytics import (
    AnalyticsEngine,
    AggregationType,
    TimeWindow,
    AnalyticsResult,
    AnomalyEvent,
)
from apex_os_bp.iot.device_control import (
    DeviceController,
    Command,
    CommandStatus,
    CommandResult,
)
from apex_os_bp.iot.alert_manager import (
    AlertManager,
    Alert,
    AlertSeverity,
    AlertStatus,
    AlertRule,
)


# ===========================================================================
# Device Management Tests
# ===========================================================================


class TestDeviceManager:
    """Tests for the DeviceManager class."""

    def setup_method(self) -> None:
        self.dm = DeviceManager()

    def test_register_device(self) -> None:
        device = self.dm.register_device(
            name="Temp Sensor 1",
            device_type=DeviceType.SENSOR,
            location="Building A",
        )
        assert device.device_id
        assert device.name == "Temp Sensor 1"
        assert device.device_type == DeviceType.SENSOR
        assert device.status == DeviceStatus.OFFLINE
        assert device.is_active is True

    def test_register_device_with_string_type(self) -> None:
        device = self.dm.register_device(
            name="Gateway",
            device_type="gateway",
        )
        assert device.device_type == DeviceType.GATEWAY

    def test_register_device_duplicate_id(self) -> None:
        self.dm.register_device(
            name="Device",
            device_type=DeviceType.SENSOR,
            device_id="my-id",
        )
        with pytest.raises(ValueError, match="already exists"):
            self.dm.register_device(
                name="Device 2",
                device_type=DeviceType.SENSOR,
                device_id="my-id",
            )

    def test_get_device(self) -> None:
        device = self.dm.register_device(
            name="Test",
            device_type=DeviceType.SENSOR,
            device_id="test-1",
        )
        fetched = self.dm.get_device("test-1")
        assert fetched.device_id == "test-1"
        assert fetched.name == "Test"

    def test_get_device_not_found(self) -> None:
        with pytest.raises(KeyError):
            self.dm.get_device("nonexistent")

    def test_get_all_devices(self) -> None:
        self.dm.register_device(name="D1", device_type=DeviceType.SENSOR)
        self.dm.register_device(name="D2", device_type=DeviceType.SENSOR)
        assert len(self.dm.get_all_devices()) == 2

    def test_update_device(self) -> None:
        device = self.dm.register_device(
            name="Test",
            device_type=DeviceType.SENSOR,
            device_id="test-1",
        )
        updated = self.dm.update_device("test-1", name="New Name", location="Room 1")
        assert updated.name == "New Name"
        assert updated.location == "Room 1"

    def test_update_device_invalid_field(self) -> None:
        self.dm.register_device(
            name="Test",
            device_type=DeviceType.SENSOR,
            device_id="test-1",
        )
        with pytest.raises(AttributeError):
            self.dm.update_device("test-1", invalid_field="value")

    def test_update_status(self) -> None:
        device = self.dm.register_device(
            name="Test",
            device_type=DeviceType.SENSOR,
            device_id="test-1",
        )
        updated = self.dm.update_status("test-1", DeviceStatus.ONLINE)
        assert updated.status == DeviceStatus.ONLINE

    def test_update_status_string(self) -> None:
        self.dm.register_device(
            name="Test",
            device_type=DeviceType.SENSOR,
            device_id="test-1",
        )
        updated = self.dm.update_status("test-1", "maintenance")
        assert updated.status == DeviceStatus.MAINTENANCE

    def test_update_last_seen(self) -> None:
        self.dm.register_device(
            name="Test",
            device_type=DeviceType.SENSOR,
            device_id="test-1",
        )
        ts = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        updated = self.dm.update_last_seen("test-1", ts)
        assert updated.last_seen_at == ts

    def test_deregister_device(self) -> None:
        self.dm.register_device(
            name="Test",
            device_type=DeviceType.SENSOR,
            device_id="test-1",
        )
        device = self.dm.deregister_device("test-1")
        assert device.is_active is False
        assert device.status == DeviceStatus.DECOMMISSIONED

    def test_remove_device(self) -> None:
        self.dm.register_device(
            name="Test",
            device_type=DeviceType.SENSOR,
            device_id="test-1",
        )
        self.dm.remove_device("test-1")
        assert self.dm.get_device_count() == 0

    def test_remove_device_not_found(self) -> None:
        with pytest.raises(KeyError):
            self.dm.remove_device("nonexistent")

    def test_list_devices_filter_by_status(self) -> None:
        self.dm.register_device(
            name="D1",
            device_type=DeviceType.SENSOR,
            device_id="d1",
        )
        self.dm.register_device(
            name="D2",
            device_type=DeviceType.SENSOR,
            device_id="d2",
        )
        self.dm.update_status("d1", DeviceStatus.ONLINE)
        online = self.dm.list_devices(status=DeviceStatus.ONLINE)
        assert len(online) == 1
        assert online[0].device_id == "d1"

    def test_list_devices_filter_by_type(self) -> None:
        self.dm.register_device(
            name="Sensor",
            device_type=DeviceType.SENSOR,
            device_id="s1",
        )
        self.dm.register_device(
            name="Gateway",
            device_type=DeviceType.GATEWAY,
            device_id="g1",
        )
        sensors = self.dm.list_devices(device_type=DeviceType.SENSOR)
        assert len(sensors) == 1
        assert sensors[0].device_id == "s1"

    def test_list_devices_filter_by_location(self) -> None:
        self.dm.register_device(
            name="D1",
            device_type=DeviceType.SENSOR,
            location="Building A",
            device_id="d1",
        )
        self.dm.register_device(
            name="D2",
            device_type=DeviceType.SENSOR,
            location="Building B",
            device_id="d2",
        )
        results = self.dm.list_devices(location="Building A")
        assert len(results) == 1
        assert results[0].device_id == "d1"

    def test_list_devices_filter_by_tag(self) -> None:
        self.dm.register_device(
            name="D1",
            device_type=DeviceType.SENSOR,
            tags=["production", "zone1"],
            device_id="d1",
        )
        self.dm.register_device(
            name="D2",
            device_type=DeviceType.SENSOR,
            tags=["staging"],
            device_id="d2",
        )
        results = self.dm.list_devices(tag="production")
        assert len(results) == 1
        assert results[0].device_id == "d1"

    def test_list_devices_active_only(self) -> None:
        self.dm.register_device(
            name="D1",
            device_type=DeviceType.SENSOR,
            device_id="d1",
        )
        self.dm.register_device(
            name="D2",
            device_type=DeviceType.SENSOR,
            device_id="d2",
        )
        self.dm.deregister_device("d1")
        active = self.dm.list_devices(active_only=True)
        assert len(active) == 1
        assert active[0].device_id == "d2"
        all_devs = self.dm.list_devices(active_only=False)
        assert len(all_devs) == 2

    def test_search_by_name(self) -> None:
        self.dm.register_device(
            name="Temperature Sensor A",
            device_type=DeviceType.SENSOR,
            device_id="d1",
        )
        self.dm.register_device(
            name="Humidity Sensor B",
            device_type=DeviceType.SENSOR,
            device_id="d2",
        )
        results = self.dm.search_by_name("temperature")
        assert len(results) == 1
        assert results[0].device_id == "d1"

    def test_get_device_count(self) -> None:
        self.dm.register_device(
            name="D1",
            device_type=DeviceType.SENSOR,
            device_id="d1",
        )
        self.dm.register_device(
            name="D2",
            device_type=DeviceType.SENSOR,
            device_id="d2",
        )
        assert self.dm.get_device_count() == 2
        self.dm.deregister_device("d1")
        assert self.dm.get_device_count(active_only=True) == 1
        assert self.dm.get_device_count(active_only=False) == 2

    def test_add_and_remove_tag(self) -> None:
        self.dm.register_device(
            name="D1",
            device_type=DeviceType.SENSOR,
            device_id="d1",
        )
        self.dm.add_tag("d1", "production")
        device = self.dm.get_device("d1")
        assert "production" in device.tags
        self.dm.remove_tag("d1", "production")
        device = self.dm.get_device("d1")
        assert "production" not in device.tags

    def test_device_to_dict(self) -> None:
        device = self.dm.register_device(
            name="Test",
            device_type=DeviceType.SENSOR,
            device_id="test-1",
            location="Lab",
            firmware_version="2.0",
        )
        data = device.to_dict()
        assert data["device_id"] == "test-1"
        assert data["name"] == "Test"
        assert data["device_type"] == "sensor"
        assert data["location"] == "Lab"
        assert data["firmware_version"] == "2.0"

    def test_device_from_dict(self) -> None:
        device = Device(
            device_id="test-1",
            name="Test",
            device_type=DeviceType.SENSOR,
            status=DeviceStatus.ONLINE,
            location="Lab",
            firmware_version="2.0",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        data = device.to_dict()
        restored = Device.from_dict(data)
        assert restored.device_id == "test-1"
        assert restored.name == "Test"
        assert restored.status == DeviceStatus.ONLINE

    def test_clear(self) -> None:
        self.dm.register_device(
            name="D1",
            device_type=DeviceType.SENSOR,
            device_id="d1",
        )
        self.dm.clear()
        assert self.dm.get_device_count() == 0


# ===========================================================================
# Data Ingestion Tests
# ===========================================================================


class TestDataIngestion:
    """Tests for the DataIngestion class."""

    def setup_method(self) -> None:
        self.di = DataIngestion()

    def test_ingest_single_reading(self) -> None:
        reading = self.di.ingest(
            device_id="dev-1",
            sensor_type="temperature",
            value=23.5,
            unit="C",
        )
        assert reading.device_id == "dev-1"
        assert reading.sensor_type == "temperature"
        assert reading.value == 23.5
        assert reading.unit == "C"
        assert reading.quality == 1.0

    def test_ingest_with_metadata(self) -> None:
        reading = self.di.ingest(
            device_id="dev-1",
            sensor_type="temperature",
            value=23.5,
            unit="C",
            metadata={"battery": 85},
        )
        assert reading.metadata["battery"] == 85

    def test_ingest_invalid_device_id(self) -> None:
        with pytest.raises(ValueError, match="device_id"):
            self.di.ingest(
                device_id="",
                sensor_type="temperature",
                value=23.5,
            )

    def test_ingest_invalid_sensor_type(self) -> None:
        with pytest.raises(ValueError, match="sensor_type"):
            self.di.ingest(
                device_id="dev-1",
                sensor_type="",
                value=23.5,
            )

    def test_ingest_unknown_sensor_type(self) -> None:
        with pytest.raises(ValueError, match="Unknown sensor type"):
            self.di.ingest(
                device_id="dev-1",
                sensor_type="unknown_sensor",
                value=23.5,
            )

    def test_ingest_invalid_unit(self) -> None:
        with pytest.raises(ValueError, match="Invalid unit"):
            self.di.ingest(
                device_id="dev-1",
                sensor_type="temperature",
                value=23.5,
                unit="meters",
            )

    def test_ingest_invalid_quality(self) -> None:
        with pytest.raises(ValueError, match="quality"):
            self.di.ingest(
                device_id="dev-1",
                sensor_type="temperature",
                value=23.5,
                quality=1.5,
            )

    def test_ingest_skip_validation(self) -> None:
        reading = self.di.ingest(
            device_id="dev-1",
            sensor_type="custom_sensor",
            value=42.0,
            validate=False,
        )
        assert reading.value == 42.0

    def test_ingest_batch(self) -> None:
        readings = [
            {"device_id": "dev-1", "sensor_type": "temperature", "value": 20.0, "unit": "C"},
            {"device_id": "dev-1", "sensor_type": "temperature", "value": 21.0, "unit": "C"},
            {"device_id": "dev-2", "sensor_type": "humidity", "value": 55.0, "unit": "%"},
        ]
        result = self.di.ingest_batch(readings)
        assert result.status == IngestionStatus.SUCCESS
        assert result.readings_accepted == 3
        assert result.readings_rejected == 0
        assert result.success_rate == 1.0

    def test_ingest_batch_partial(self) -> None:
        readings = [
            {"device_id": "dev-1", "sensor_type": "temperature", "value": 20.0, "unit": "C"},
            {"device_id": "", "sensor_type": "temperature", "value": 21.0, "unit": "C"},
        ]
        result = self.di.ingest_batch(readings)
        assert result.status == IngestionStatus.PARTIAL
        assert result.readings_accepted == 1
        assert result.readings_rejected == 1

    def test_ingest_batch_all_failed(self) -> None:
        readings = [
            {"device_id": "", "sensor_type": "temperature", "value": 20.0},
            {"sensor_type": "temperature", "value": 21.0},
        ]
        result = self.di.ingest_batch(readings)
        assert result.status == IngestionStatus.FAILED
        assert result.readings_accepted == 0
        assert result.readings_rejected == 2

    def test_get_readings_by_device(self) -> None:
        self.di.ingest(device_id="dev-1", sensor_type="temperature", value=20.0, unit="C")
        self.di.ingest(device_id="dev-1", sensor_type="temperature", value=21.0, unit="C")
        self.di.ingest(device_id="dev-2", sensor_type="temperature", value=22.0, unit="C")
        results = self.di.get_readings(device_id="dev-1")
        assert len(results) == 2

    def test_get_readings_by_sensor_type(self) -> None:
        self.di.ingest(device_id="dev-1", sensor_type="temperature", value=20.0, unit="C")
        self.di.ingest(device_id="dev-1", sensor_type="humidity", value=55.0, unit="%")
        results = self.di.get_readings(sensor_type="humidity")
        assert len(results) == 1

    def test_get_readings_time_filter(self) -> None:
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=2)
        self.di.ingest(
            device_id="dev-1",
            sensor_type="temperature",
            value=20.0,
            unit="C",
            timestamp=past,
        )
        self.di.ingest(
            device_id="dev-1",
            sensor_type="temperature",
            value=21.0,
            unit="C",
            timestamp=now,
        )
        results = self.di.get_readings(
            device_id="dev-1",
            start_time=now - timedelta(hours=1),
        )
        assert len(results) == 1
        assert results[0].value == 21.0

    def test_get_readings_limit(self) -> None:
        for i in range(10):
            self.di.ingest(
                device_id="dev-1",
                sensor_type="temperature",
                value=float(i),
                unit="C",
            )
        results = self.di.get_readings(device_id="dev-1", limit=3)
        assert len(results) == 3

    def test_get_latest_reading(self) -> None:
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)
        self.di.ingest(
            device_id="dev-1",
            sensor_type="temperature",
            value=20.0,
            unit="C",
            timestamp=past,
        )
        self.di.ingest(
            device_id="dev-1",
            sensor_type="temperature",
            value=25.0,
            unit="C",
            timestamp=now,
        )
        latest = self.di.get_latest_reading("dev-1")
        assert latest is not None
        assert latest.value == 25.0

    def test_get_latest_reading_none(self) -> None:
        latest = self.di.get_latest_reading("nonexistent")
        assert latest is None

    def test_get_reading_count(self) -> None:
        self.di.ingest(device_id="dev-1", sensor_type="temperature", value=20.0, unit="C")
        self.di.ingest(device_id="dev-1", sensor_type="temperature", value=21.0, unit="C")
        self.di.ingest(device_id="dev-2", sensor_type="temperature", value=22.0, unit="C")
        assert self.di.get_reading_count() == 3
        assert self.di.get_reading_count(device_id="dev-1") == 2

    def test_clear(self) -> None:
        self.di.ingest(device_id="dev-1", sensor_type="temperature", value=20.0, unit="C")
        self.di.clear()
        assert self.di.get_reading_count() == 0

    def test_sensor_reading_to_dict(self) -> None:
        reading = SensorReading(
            device_id="dev-1",
            sensor_type="temperature",
            value=23.5,
            unit="C",
        )
        data = reading.to_dict()
        assert data["device_id"] == "dev-1"
        assert data["value"] == 23.5

    def test_sensor_reading_from_dict(self) -> None:
        data = {
            "reading_id": "r1",
            "device_id": "dev-1",
            "sensor_type": "temperature",
            "value": 23.5,
            "unit": "C",
            "timestamp": "2024-01-15T12:00:00+00:00",
        }
        reading = SensorReading.from_dict(data)
        assert reading.reading_id == "r1"
        assert reading.value == 23.5

    def test_max_readings_limit(self) -> None:
        di = DataIngestion(max_readings=5)
        for i in range(10):
            di.ingest(
                device_id="dev-1",
                sensor_type="temperature",
                value=float(i),
                unit="C",
            )
        assert di.get_reading_count() == 5


# ===========================================================================
# Analytics Tests
# ===========================================================================


class TestAnalyticsEngine:
    """Tests for the AnalyticsEngine class."""

    def setup_method(self) -> None:
        self.di = DataIngestion()
        self.ae = AnalyticsEngine(self.di)
        # Seed data
        for i in range(10):
            self.di.ingest(
                device_id="dev-1",
                sensor_type="temperature",
                value=20.0 + i,
                unit="C",
            )

    def test_aggregate_avg(self) -> None:
        result = self.ae.aggregate("dev-1", "temperature", AggregationType.AVG)
        assert result.value == pytest.approx(24.5)
        assert result.count == 10

    def test_aggregate_min(self) -> None:
        result = self.ae.aggregate("dev-1", "temperature", AggregationType.MIN)
        assert result.value == 20.0

    def test_aggregate_max(self) -> None:
        result = self.ae.aggregate("dev-1", "temperature", AggregationType.MAX)
        assert result.value == 29.0

    def test_aggregate_sum(self) -> None:
        result = self.ae.aggregate("dev-1", "temperature", AggregationType.SUM)
        assert result.value == pytest.approx(245.0)

    def test_aggregate_count(self) -> None:
        result = self.ae.aggregate("dev-1", "temperature", AggregationType.COUNT)
        assert result.value == 10.0

    def test_aggregate_median(self) -> None:
        result = self.ae.aggregate("dev-1", "temperature", AggregationType.MEDIAN)
        assert result.value == pytest.approx(24.5)

    def test_aggregate_stddev(self) -> None:
        result = self.ae.aggregate("dev-1", "temperature", AggregationType.STDDEV)
        assert result.value > 0

    def test_aggregate_variance(self) -> None:
        result = self.ae.aggregate("dev-1", "temperature", AggregationType.VARIANCE)
        assert result.value > 0

    def test_aggregate_p95(self) -> None:
        result = self.ae.aggregate("dev-1", "temperature", AggregationType.P95)
        assert result.value >= 20.0

    def test_aggregate_p99(self) -> None:
        result = self.ae.aggregate("dev-1", "temperature", AggregationType.P99)
        assert result.value >= 20.0

    def test_aggregate_range(self) -> None:
        result = self.ae.aggregate("dev-1", "temperature", AggregationType.RANGE)
        assert result.value == pytest.approx(9.0)

    def test_aggregate_no_data(self) -> None:
        with pytest.raises(ValueError, match="No readings"):
            self.ae.aggregate("nonexistent", "temperature", AggregationType.AVG)

    def test_aggregate_string_params(self) -> None:
        result = self.ae.aggregate("dev-1", "temperature", "avg", "all")
        assert result.value == pytest.approx(24.5)

    def test_aggregate_with_time_window(self) -> None:
        result = self.ae.aggregate(
            "dev-1",
            "temperature",
            AggregationType.AVG,
            TimeWindow.ALL,
        )
        assert result.window == TimeWindow.ALL

    def test_detect_anomalies(self) -> None:
        # Add an outlier
        self.di.ingest(
            device_id="dev-1",
            sensor_type="temperature",
            value=100.0,
            unit="C",
        )
        anomalies = self.ae.detect_anomalies("dev-1", "temperature", threshold_std=2.0)
        assert len(anomalies) > 0
        assert anomalies[0].reading.value == 100.0

    def test_detect_anomalies_insufficient_data(self) -> None:
        di = DataIngestion()
        ae = AnalyticsEngine(di)
        di.ingest(device_id="dev-1", sensor_type="temperature", value=20.0, unit="C")
        di.ingest(device_id="dev-1", sensor_type="temperature", value=21.0, unit="C")
        anomalies = ae.detect_anomalies("dev-1", "temperature")
        assert len(anomalies) == 0

    def test_detect_anomalies_no_outliers(self) -> None:
        anomalies = self.ae.detect_anomalies("dev-1", "temperature", threshold_std=3.0)
        assert len(anomalies) == 0

    def test_compute_trend_increasing(self) -> None:
        di = DataIngestion()
        ae = AnalyticsEngine(di)
        now = datetime.now(timezone.utc)
        for i in range(5):
            di.ingest(
                device_id="dev-1",
                sensor_type="temperature",
                value=float(i * 10),
                unit="C",
                timestamp=now - timedelta(minutes=10 - i),
            )
        trend = ae.compute_trend("dev-1", "temperature")
        assert trend["direction"] == "increasing"
        assert trend["slope"] > 0

    def test_compute_trend_decreasing(self) -> None:
        di = DataIngestion()
        ae = AnalyticsEngine(di)
        now = datetime.now(timezone.utc)
        for i in range(5):
            di.ingest(
                device_id="dev-1",
                sensor_type="temperature",
                value=float(50 - i * 10),
                unit="C",
                timestamp=now - timedelta(minutes=10 - i),
            )
        trend = ae.compute_trend("dev-1", "temperature")
        assert trend["direction"] == "decreasing"
        assert trend["slope"] < 0

    def test_compute_trend_stable(self) -> None:
        di = DataIngestion()
        ae = AnalyticsEngine(di)
        now = datetime.now(timezone.utc)
        for i in range(5):
            di.ingest(
                device_id="dev-1",
                sensor_type="temperature",
                value=25.0,
                unit="C",
                timestamp=now - timedelta(minutes=10 - i),
            )
        trend = ae.compute_trend("dev-1", "temperature")
        assert trend["direction"] == "stable"

    def test_compute_trend_insufficient_data(self) -> None:
        di = DataIngestion()
        ae = AnalyticsEngine(di)
        di.ingest(device_id="dev-1", sensor_type="temperature", value=20.0, unit="C")
        trend = ae.compute_trend("dev-1", "temperature")
        assert trend["direction"] == "insufficient_data"

    def test_get_summary(self) -> None:
        summary = self.ae.get_summary("dev-1", "temperature")
        assert summary["count"] == 10.0
        assert summary["min"] == 20.0
        assert summary["max"] == 29.0
        assert summary["avg"] == pytest.approx(24.5)

    def test_get_summary_no_data(self) -> None:
        summary = self.ae.get_summary("nonexistent", "temperature")
        assert summary["count"] == 0.0

    def test_compare_devices(self) -> None:
        self.di.ingest(device_id="dev-2", sensor_type="temperature", value=30.0, unit="C")
        results = self.ae.compare_devices(
            ["dev-1", "dev-2"],
            "temperature",
            AggregationType.AVG,
        )
        assert "dev-1" in results
        assert "dev-2" in results
        assert results["dev-1"].value == pytest.approx(24.5)
        assert results["dev-2"].value == 30.0

    def test_compare_devices_skips_no_data(self) -> None:
        results = self.ae.compare_devices(
            ["dev-1", "nonexistent"],
            "temperature",
        )
        assert "dev-1" in results
        assert "nonexistent" not in results

    def test_analytics_result_to_dict(self) -> None:
        result = self.ae.aggregate("dev-1", "temperature", AggregationType.AVG)
        data = result.to_dict()
        assert data["device_id"] == "dev-1"
        assert data["aggregation"] == "avg"
        assert data["count"] == 10

    def test_anomaly_event_to_dict(self) -> None:
        self.di.ingest(
            device_id="dev-1",
            sensor_type="temperature",
            value=100.0,
            unit="C",
        )
        anomalies = self.ae.detect_anomalies("dev-1", "temperature")
        if anomalies:
            data = anomalies[0].to_dict()
            assert data["device_id"] == "dev-1"
            assert "expected_range" in data


# ===========================================================================
# Device Control Tests
# ===========================================================================


class TestDeviceController:
    """Tests for the DeviceController class."""

    def setup_method(self) -> None:
        self.dc = DeviceController()

    def test_send_command(self) -> None:
        cmd = self.dc.send_command(
            device_id="dev-1",
            command_type="reboot",
        )
        assert cmd.device_id == "dev-1"
        assert cmd.command_type == "reboot"
        assert cmd.status == CommandStatus.PENDING
        assert cmd.priority == 3

    def test_send_command_with_params(self) -> None:
        cmd = self.dc.send_command(
            device_id="dev-1",
            command_type="set_threshold",
            parameters={"threshold": 30.0},
            priority=1,
        )
        assert cmd.parameters["threshold"] == 30.0
        assert cmd.priority == 1

    def test_send_command_invalid_type(self) -> None:
        with pytest.raises(ValueError, match="Invalid command type"):
            self.dc.send_command(
                device_id="dev-1",
                command_type="invalid_command",
            )

    def test_send_command_invalid_priority(self) -> None:
        with pytest.raises(ValueError, match="Priority"):
            self.dc.send_command(
                device_id="dev-1",
                command_type="reboot",
                priority=10,
            )

    def test_get_command(self) -> None:
        cmd = self.dc.send_command(device_id="dev-1", command_type="reboot")
        fetched = self.dc.get_command(cmd.command_id)
        assert fetched.command_id == cmd.command_id

    def test_get_command_not_found(self) -> None:
        with pytest.raises(KeyError):
            self.dc.get_command("nonexistent")

    def test_update_status(self) -> None:
        cmd = self.dc.send_command(device_id="dev-1", command_type="reboot")
        updated = self.dc.update_status(cmd.command_id, CommandStatus.SENT)
        assert updated.status == CommandStatus.SENT
        assert updated.sent_at is not None

    def test_acknowledge(self) -> None:
        cmd = self.dc.send_command(device_id="dev-1", command_type="reboot")
        self.dc.acknowledge(cmd.command_id)
        assert cmd.status == CommandStatus.ACKNOWLEDGED

    def test_complete(self) -> None:
        cmd = self.dc.send_command(device_id="dev-1", command_type="reboot")
        self.dc.complete(cmd.command_id, result={"status": "ok"})
        assert cmd.status == CommandStatus.COMPLETED
        assert cmd.result == {"status": "ok"}
        assert cmd.completed_at is not None

    def test_fail(self) -> None:
        cmd = self.dc.send_command(device_id="dev-1", command_type="reboot")
        self.dc.fail(cmd.command_id, "Connection timeout")
        assert cmd.status == CommandStatus.FAILED
        assert cmd.error_message == "Connection timeout"

    def test_cancel(self) -> None:
        cmd = self.dc.send_command(device_id="dev-1", command_type="reboot")
        self.dc.cancel(cmd.command_id)
        assert cmd.status == CommandStatus.CANCELLED

    def test_cancel_terminal_state(self) -> None:
        cmd = self.dc.send_command(device_id="dev-1", command_type="reboot")
        self.dc.complete(cmd.command_id)
        with pytest.raises(ValueError, match="Cannot cancel"):
            self.dc.cancel(cmd.command_id)

    def test_get_pending_commands(self) -> None:
        self.dc.send_command(device_id="dev-1", command_type="reboot", priority=2)
        self.dc.send_command(device_id="dev-2", command_type="reboot", priority=1)
        self.dc.send_command(device_id="dev-3", command_type="reboot", priority=3)
        pending = self.dc.get_pending_commands()
        assert len(pending) == 3
        # Highest priority (lowest number) first
        assert pending[0].priority == 1

    def test_get_command_history(self) -> None:
        self.dc.send_command(device_id="dev-1", command_type="reboot")
        self.dc.send_command(device_id="dev-1", command_type="shutdown")
        self.dc.send_command(device_id="dev-2", command_type="reboot")
        history = self.dc.get_command_history(device_id="dev-1")
        assert len(history) == 2

    def test_get_command_history_by_status(self) -> None:
        cmd1 = self.dc.send_command(device_id="dev-1", command_type="reboot")
        self.dc.send_command(device_id="dev-1", command_type="shutdown")
        self.dc.complete(cmd1.command_id)
        completed = self.dc.get_command_history(status=CommandStatus.COMPLETED)
        assert len(completed) == 1

    def test_get_command_history_limit(self) -> None:
        for _ in range(5):
            self.dc.send_command(device_id="dev-1", command_type="reboot")
        history = self.dc.get_command_history(limit=3)
        assert len(history) == 3

    def test_get_device_commands(self) -> None:
        self.dc.send_command(device_id="dev-1", command_type="reboot")
        self.dc.send_command(device_id="dev-1", command_type="shutdown")
        self.dc.send_command(device_id="dev-2", command_type="reboot")
        cmds = self.dc.get_device_commands("dev-1")
        assert len(cmds) == 2

    def test_get_command_count(self) -> None:
        self.dc.send_command(device_id="dev-1", command_type="reboot")
        self.dc.send_command(device_id="dev-1", command_type="shutdown")
        assert self.dc.get_command_count() == 2
        assert self.dc.get_command_count(status=CommandStatus.PENDING) == 2

    def test_clear_history(self) -> None:
        self.dc.send_command(device_id="dev-1", command_type="reboot")
        self.dc.clear_history()
        assert self.dc.get_command_count() == 0

    def test_process_next_pending(self) -> None:
        self.dc.send_command(device_id="dev-1", command_type="reboot", priority=2)
        self.dc.send_command(device_id="dev-2", command_type="reboot", priority=1)
        next_cmd = self.dc.process_next_pending()
        assert next_cmd is not None
        assert next_cmd.priority == 1

    def test_process_next_pending_empty(self) -> None:
        assert self.dc.process_next_pending() is None

    def test_command_to_dict(self) -> None:
        cmd = self.dc.send_command(
            device_id="dev-1",
            command_type="reboot",
            parameters={"force": True},
        )
        data = cmd.to_dict()
        assert data["device_id"] == "dev-1"
        assert data["command_type"] == "reboot"
        assert data["parameters"]["force"] is True

    def test_command_is_terminal(self) -> None:
        cmd = self.dc.send_command(device_id="dev-1", command_type="reboot")
        assert cmd.is_terminal is False
        self.dc.complete(cmd.command_id)
        assert cmd.is_terminal is True

    def test_command_duration(self) -> None:
        cmd = self.dc.send_command(device_id="dev-1", command_type="reboot")
        assert cmd.duration_seconds is None
        self.dc.complete(cmd.command_id)
        assert cmd.duration_seconds is not None
        assert cmd.duration_seconds >= 0

    def test_command_callback(self) -> None:
        callback_called = []

        def on_change(cmd: Command) -> None:
            callback_called.append(cmd.status)

        cmd = self.dc.send_command(
            device_id="dev-1",
            command_type="reboot",
            callback=on_change,
        )
        self.dc.update_status(cmd.command_id, CommandStatus.SENT)
        assert len(callback_called) == 1
        assert callback_called[0] == CommandStatus.SENT


# ===========================================================================
# Alert Management Tests
# ===========================================================================


class TestAlertManager:
    """Tests for the AlertManager class."""

    def setup_method(self) -> None:
        self.am = AlertManager()

    def test_create_alert(self) -> None:
        alert = self.am.create_alert(
            device_id="dev-1",
            alert_type="threshold_exceeded",
            severity=AlertSeverity.HIGH,
            message="Temperature too high",
            value=35.0,
            threshold=30.0,
        )
        assert alert.alert_id
        assert alert.device_id == "dev-1"
        assert alert.severity == AlertSeverity.HIGH
        assert alert.status == AlertStatus.ACTIVE
        assert alert.value == 35.0
        assert alert.threshold == 30.0

    def test_create_alert_string_severity(self) -> None:
        alert = self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity="critical",
            message="Test",
        )
        assert alert.severity == AlertSeverity.CRITICAL

    def test_get_alert(self) -> None:
        alert = self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.LOW,
            message="Test",
        )
        fetched = self.am.get_alert(alert.alert_id)
        assert fetched.alert_id == alert.alert_id

    def test_get_alert_not_found(self) -> None:
        with pytest.raises(KeyError):
            self.am.get_alert("nonexistent")

    def test_acknowledge(self) -> None:
        alert = self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Test",
        )
        self.am.acknowledge(alert.alert_id, acknowledged_by="operator1")
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_by == "operator1"
        assert alert.acknowledged_at is not None

    def test_acknowledge_non_active(self) -> None:
        alert = self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Test",
        )
        self.am.resolve(alert.alert_id)
        with pytest.raises(ValueError, match="Cannot acknowledge"):
            self.am.acknowledge(alert.alert_id)

    def test_resolve(self) -> None:
        alert = self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Test",
        )
        self.am.resolve(alert.alert_id, resolved_by="admin", resolution_note="Fixed")
        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_by == "admin"
        assert alert.resolution_note == "Fixed"
        assert alert.resolved_at is not None

    def test_resolve_already_resolved(self) -> None:
        alert = self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Test",
        )
        self.am.resolve(alert.alert_id)
        with pytest.raises(ValueError, match="Cannot resolve"):
            self.am.resolve(alert.alert_id)

    def test_suppress(self) -> None:
        alert = self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.LOW,
            message="Test",
        )
        self.am.suppress(alert.alert_id)
        assert alert.status == AlertStatus.SUPPRESSED

    def test_expire(self) -> None:
        alert = self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.LOW,
            message="Test",
        )
        self.am.expire(alert.alert_id)
        assert alert.status == AlertStatus.EXPIRED

    def test_list_alerts(self) -> None:
        self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Alert 1",
        )
        self.am.create_alert(
            device_id="dev-2",
            alert_type="test",
            severity=AlertSeverity.LOW,
            message="Alert 2",
        )
        all_alerts = self.am.list_alerts()
        assert len(all_alerts) == 2

    def test_list_alerts_filter_by_status(self) -> None:
        a1 = self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Alert 1",
        )
        self.am.create_alert(
            device_id="dev-2",
            alert_type="test",
            severity=AlertSeverity.LOW,
            message="Alert 2",
        )
        self.am.resolve(a1.alert_id)
        active = self.am.list_alerts(status=AlertStatus.ACTIVE)
        assert len(active) == 1
        resolved = self.am.list_alerts(status=AlertStatus.RESOLVED)
        assert len(resolved) == 1

    def test_list_alerts_filter_by_severity(self) -> None:
        self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.CRITICAL,
            message="Alert 1",
        )
        self.am.create_alert(
            device_id="dev-2",
            alert_type="test",
            severity=AlertSeverity.LOW,
            message="Alert 2",
        )
        critical = self.am.list_alerts(severity=AlertSeverity.CRITICAL)
        assert len(critical) == 1

    def test_list_alerts_filter_by_device(self) -> None:
        self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Alert 1",
        )
        self.am.create_alert(
            device_id="dev-2",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Alert 2",
        )
        results = self.am.list_alerts(device_id="dev-1")
        assert len(results) == 1

    def test_list_alerts_active_only(self) -> None:
        a1 = self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Alert 1",
        )
        self.am.create_alert(
            device_id="dev-2",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Alert 2",
        )
        self.am.resolve(a1.alert_id)
        active = self.am.list_alerts(active_only=True)
        assert len(active) == 1

    def test_get_active_alerts(self) -> None:
        self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Alert 1",
        )
        a2 = self.am.create_alert(
            device_id="dev-2",
            alert_type="test",
            severity=AlertSeverity.LOW,
            message="Alert 2",
        )
        self.am.resolve(a2.alert_id)
        active = self.am.get_active_alerts()
        assert len(active) == 1

    def test_get_critical_alerts(self) -> None:
        self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.CRITICAL,
            message="Alert 1",
        )
        self.am.create_alert(
            device_id="dev-2",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Alert 2",
        )
        critical = self.am.get_critical_alerts()
        assert len(critical) == 1

    def test_get_alert_count(self) -> None:
        self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Alert 1",
        )
        self.am.create_alert(
            device_id="dev-2",
            alert_type="test",
            severity=AlertSeverity.LOW,
            message="Alert 2",
        )
        assert self.am.get_alert_count() == 2
        assert self.am.get_alert_count(severity=AlertSeverity.HIGH) == 1

    def test_add_rule(self) -> None:
        rule = self.am.add_rule(
            name="High Temp",
            device_id="dev-1",
            sensor_type="temperature",
            condition="gt",
            threshold=30.0,
            severity=AlertSeverity.HIGH,
        )
        assert rule.rule_id
        assert rule.name == "High Temp"
        assert rule.enabled is True

    def test_remove_rule(self) -> None:
        rule = self.am.add_rule(
            name="Test",
            device_id="dev-1",
            sensor_type="temperature",
            condition="gt",
            threshold=30.0,
            severity=AlertSeverity.HIGH,
        )
        self.am.remove_rule(rule.rule_id)
        # Should not be in rules anymore
        assert len([r for r in self.am._rules.values() if r.rule_id == rule.rule_id]) == 0

    def test_remove_rule_not_found(self) -> None:
        with pytest.raises(KeyError):
            self.am.remove_rule("nonexistent")

    def test_evaluate_rules_triggers(self) -> None:
        self.am.add_rule(
            name="High Temp",
            device_id="dev-1",
            sensor_type="temperature",
            condition="gt",
            threshold=30.0,
            severity=AlertSeverity.HIGH,
            message_template="Temp {value} > {threshold}",
        )
        alerts = self.am.evaluate_rules("dev-1", "temperature", 35.0)
        assert len(alerts) == 1
        assert alerts[0].value == 35.0
        assert alerts[0].threshold == 30.0

    def test_evaluate_rules_no_trigger(self) -> None:
        self.am.add_rule(
            name="High Temp",
            device_id="dev-1",
            sensor_type="temperature",
            condition="gt",
            threshold=30.0,
            severity=AlertSeverity.HIGH,
        )
        alerts = self.am.evaluate_rules("dev-1", "temperature", 25.0)
        assert len(alerts) == 0

    def test_evaluate_rules_wrong_device(self) -> None:
        self.am.add_rule(
            name="High Temp",
            device_id="dev-1",
            sensor_type="temperature",
            condition="gt",
            threshold=30.0,
            severity=AlertSeverity.HIGH,
        )
        alerts = self.am.evaluate_rules("dev-2", "temperature", 35.0)
        assert len(alerts) == 0

    def test_evaluate_rules_wildcard_device(self) -> None:
        self.am.add_rule(
            name="High Temp",
            device_id="*",
            sensor_type="temperature",
            condition="gt",
            threshold=30.0,
            severity=AlertSeverity.HIGH,
        )
        alerts = self.am.evaluate_rules("any-device", "temperature", 35.0)
        assert len(alerts) == 1

    def test_evaluate_rules_cooldown(self) -> None:
        self.am.add_rule(
            name="High Temp",
            device_id="dev-1",
            sensor_type="temperature",
            condition="gt",
            threshold=30.0,
            severity=AlertSeverity.HIGH,
            cooldown_seconds=3600,
        )
        alerts1 = self.am.evaluate_rules("dev-1", "temperature", 35.0)
        assert len(alerts1) == 1
        # Second evaluation within cooldown should not trigger
        alerts2 = self.am.evaluate_rules("dev-1", "temperature", 36.0)
        assert len(alerts2) == 0

    def test_evaluate_rules_disabled(self) -> None:
        rule = self.am.add_rule(
            name="High Temp",
            device_id="dev-1",
            sensor_type="temperature",
            condition="gt",
            threshold=30.0,
            severity=AlertSeverity.HIGH,
        )
        rule.enabled = False
        alerts = self.am.evaluate_rules("dev-1", "temperature", 35.0)
        assert len(alerts) == 0

    def test_register_notification_handler(self) -> None:
        received = []

        def handler(alert: Alert) -> None:
            received.append(alert)

        self.am.register_notification_handler("email", handler)
        self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Test",
            notification_channels=["email"],
        )
        assert len(received) == 1

    def test_clear(self) -> None:
        self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Test",
        )
        self.am.add_rule(
            name="Test",
            device_id="dev-1",
            sensor_type="temperature",
            condition="gt",
            threshold=30.0,
            severity=AlertSeverity.HIGH,
        )
        self.am.clear()
        assert self.am.get_alert_count() == 0
        assert len(self.am._rules) == 0

    def test_alert_to_dict(self) -> None:
        alert = self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Test alert",
            value=35.0,
            threshold=30.0,
        )
        data = alert.to_dict()
        assert data["device_id"] == "dev-1"
        assert data["severity"] == "high"
        assert data["status"] == "active"
        assert data["value"] == 35.0

    def test_alert_is_active(self) -> None:
        alert = self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Test",
        )
        assert alert.is_active is True
        self.am.resolve(alert.alert_id)
        assert alert.is_active is False

    def test_alert_age_seconds(self) -> None:
        alert = self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="Test",
        )
        assert alert.age_seconds >= 0

    def test_alert_rule_evaluate(self) -> None:
        rule = AlertRule(
            rule_id="r1",
            name="Test",
            device_id="dev-1",
            sensor_type="temperature",
            condition="gt",
            threshold=30.0,
            severity=AlertSeverity.HIGH,
        )
        assert rule.evaluate(35.0) is True
        assert rule.evaluate(25.0) is False

    def test_alert_rule_evaluate_all_conditions(self) -> None:
        for cond, val, expected in [
            ("gt", 35.0, True),
            ("gt", 25.0, False),
            ("lt", 25.0, True),
            ("lt", 35.0, False),
            ("gte", 30.0, True),
            ("lte", 30.0, True),
            ("eq", 30.0, True),
            ("neq", 25.0, True),
        ]:
            rule = AlertRule(
                rule_id="r1",
                name="Test",
                device_id="dev-1",
                sensor_type="temperature",
                condition=cond,
                threshold=30.0,
                severity=AlertSeverity.HIGH,
            )
            assert rule.evaluate(val) == expected, f"Failed for {cond}"

    def test_alert_rule_invalid_condition(self) -> None:
        rule = AlertRule(
            rule_id="r1",
            name="Test",
            device_id="dev-1",
            sensor_type="temperature",
            condition="invalid",
            threshold=30.0,
            severity=AlertSeverity.HIGH,
        )
        with pytest.raises(ValueError, match="Unknown condition"):
            rule.evaluate(35.0)

    def test_alert_rule_can_trigger(self) -> None:
        rule = AlertRule(
            rule_id="r1",
            name="Test",
            device_id="dev-1",
            sensor_type="temperature",
            condition="gt",
            threshold=30.0,
            severity=AlertSeverity.HIGH,
            cooldown_seconds=60.0,
        )
        assert rule.can_trigger() is True
        rule.mark_triggered()
        assert rule.can_trigger() is False

    def test_alerts_sorted_by_severity(self) -> None:
        self.am.create_alert(
            device_id="dev-1",
            alert_type="test",
            severity=AlertSeverity.LOW,
            message="Low",
        )
        self.am.create_alert(
            device_id="dev-2",
            alert_type="test",
            severity=AlertSeverity.CRITICAL,
            message="Critical",
        )
        self.am.create_alert(
            device_id="dev-3",
            alert_type="test",
            severity=AlertSeverity.HIGH,
            message="High",
        )
        alerts = self.am.list_alerts()
        assert alerts[0].severity == AlertSeverity.CRITICAL
        assert alerts[1].severity == AlertSeverity.HIGH
        assert alerts[2].severity == AlertSeverity.LOW
