"""Data ingestion module for the IoT platform.

Handles ingestion of sensor readings from IoT devices, including
validation, batch processing, and storage.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class IngestionStatus(str, Enum):
    """Status of an ingestion operation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class SensorReading:
    """Represents a single sensor reading.

    Attributes:
        device_id: ID of the device that produced the reading.
        sensor_type: Type of sensor (e.g., 'temperature', 'humidity').
        value: Numeric reading value.
        unit: Unit of measurement (e.g., 'C', '%', 'Pa').
        timestamp: When the reading was taken.
        reading_id: Unique identifier for this reading.
        metadata: Additional context (battery level, signal strength, etc.).
        quality: Data quality indicator (0.0 to 1.0).
    """

    device_id: str
    sensor_type: str
    value: float
    unit: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reading_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)
    quality: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize reading to a dictionary."""
        return {
            "reading_id": self.reading_id,
            "device_id": self.device_id,
            "sensor_type": self.sensor_type,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "metadata": dict(self.metadata),
            "quality": self.quality,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SensorReading:
        """Deserialize a reading from a dictionary."""
        return cls(
            reading_id=data.get("reading_id", str(uuid.uuid4())),
            device_id=data["device_id"],
            sensor_type=data["sensor_type"],
            value=float(data["value"]),
            unit=data.get("unit", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(timezone.utc),
            metadata=dict(data.get("metadata", {})),
            quality=float(data.get("quality", 1.0)),
        )


@dataclass
class IngestionResult:
    """Result of a data ingestion operation.

    Attributes:
        status: Overall ingestion status.
        readings_accepted: Number of readings successfully ingested.
        readings_rejected: Number of readings rejected.
        errors: List of error messages for rejected readings.
        accepted_ids: IDs of accepted readings.
    """

    status: IngestionStatus
    readings_accepted: int = 0
    readings_rejected: int = 0
    errors: list[str] = field(default_factory=list)
    accepted_ids: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total number of readings processed."""
        return self.readings_accepted + self.readings_rejected

    @property
    def success_rate(self) -> float:
        """Fraction of readings accepted (0.0 to 1.0)."""
        if self.total == 0:
            return 0.0
        return self.readings_accepted / self.total

    def to_dict(self) -> dict[str, Any]:
        """Serialize result to a dictionary."""
        return {
            "status": self.status.value,
            "readings_accepted": self.readings_accepted,
            "readings_rejected": self.readings_rejected,
            "total": self.total,
            "success_rate": self.success_rate,
            "errors": list(self.errors),
            "accepted_ids": list(self.accepted_ids),
        }


class DataIngestion:
    """Ingests and stores sensor readings from IoT devices.

    Provides single and batch ingestion with validation, filtering,
    and querying capabilities.
    """

    # Valid sensor types and their expected units
    VALID_SENSOR_TYPES: dict[str, list[str]] = {
        "temperature": ["C", "F", "K"],
        "humidity": ["%"],
        "pressure": ["Pa", "hPa", "bar", "psi"],
        "light": ["lux", "lm"],
        "co2": ["ppm"],
        "voc": ["ppb", "ppm"],
        "motion": ["binary"],
        "battery": ["%", "V"],
        "voltage": ["V"],
        "current": ["A", "mA"],
        "power": ["W", "kW"],
        "energy": ["Wh", "kWh"],
        "distance": ["m", "cm", "mm"],
        "speed": ["m/s", "km/h"],
        "altitude": ["m"],
        "ph": ["pH"],
        "turbidity": ["NTU"],
        "conductivity": ["uS/cm", "mS/cm"],
    }

    def __init__(self, max_readings: int = 100_000) -> None:
        """Initialize the ingestion engine.

        Args:
            max_readings: Maximum number of readings to retain in memory.
        """
        self._readings: list[SensorReading] = []
        self._max_readings = max_readings
        self._readings_by_device: dict[str, list[SensorReading]] = {}
        self._readings_by_type: dict[str, list[SensorReading]] = {}

    def ingest(
        self,
        device_id: str,
        sensor_type: str,
        value: float,
        unit: str = "",
        timestamp: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        quality: float = 1.0,
        validate: bool = True,
    ) -> SensorReading:
        """Ingest a single sensor reading.

        Args:
            device_id: Source device ID.
            sensor_type: Type of sensor.
            value: Numeric reading value.
            unit: Unit of measurement.
            timestamp: Reading timestamp (defaults to now).
            metadata: Additional metadata.
            quality: Data quality score (0.0-1.0).
            validate: Whether to validate the reading.

        Returns:
            The stored SensorReading.

        Raises:
            ValueError: If validation fails.
        """
        if validate:
            self._validate_reading(device_id, sensor_type, value, unit, quality)

        reading = SensorReading(
            device_id=device_id,
            sensor_type=sensor_type,
            value=float(value),
            unit=unit,
            timestamp=timestamp or datetime.now(timezone.utc),
            metadata=metadata or {},
            quality=quality,
        )
        self._store_reading(reading)
        return reading

    def ingest_batch(
        self,
        readings: list[dict[str, Any]],
        validate: bool = True,
    ) -> IngestionResult:
        """Ingest a batch of readings.

        Args:
            readings: List of reading dictionaries.
            validate: Whether to validate each reading.

        Returns:
            IngestionResult with counts and errors.
        """
        accepted = 0
        rejected = 0
        errors: list[str] = []
        accepted_ids: list[str] = []

        for idx, raw in enumerate(readings):
            try:
                reading = self.ingest(
                    device_id=raw["device_id"],
                    sensor_type=raw["sensor_type"],
                    value=raw["value"],
                    unit=raw.get("unit", ""),
                    timestamp=raw.get("timestamp"),
                    metadata=raw.get("metadata"),
                    quality=raw.get("quality", 1.0),
                    validate=validate,
                )
                accepted += 1
                accepted_ids.append(reading.reading_id)
            except (ValueError, KeyError, TypeError) as exc:
                rejected += 1
                errors.append(f"Reading {idx}: {exc}")

        if rejected == 0:
            status = IngestionStatus.SUCCESS
        elif accepted > 0:
            status = IngestionStatus.PARTIAL
        else:
            status = IngestionStatus.FAILED

        return IngestionResult(
            status=status,
            readings_accepted=accepted,
            readings_rejected=rejected,
            errors=errors,
            accepted_ids=accepted_ids,
        )

    def get_readings(
        self,
        device_id: str | None = None,
        sensor_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[SensorReading]:
        """Query stored readings with optional filters.

        Args:
            device_id: Filter by device.
            sensor_type: Filter by sensor type.
            start_time: Filter readings after this time.
            end_time: Filter readings before this time.
            limit: Maximum number of readings to return.

        Returns:
            List of matching SensorReading objects.
        """
        if device_id is not None:
            results = list(self._readings_by_device.get(device_id, []))
        elif sensor_type is not None:
            results = list(self._readings_by_type.get(sensor_type, []))
        else:
            results = list(self._readings)

        if start_time is not None:
            results = [r for r in results if r.timestamp >= start_time]
        if end_time is not None:
            results = [r for r in results if r.timestamp <= end_time]

        # Sort by timestamp descending
        results.sort(key=lambda r: r.timestamp, reverse=True)

        if limit is not None:
            results = results[:limit]

        return results

    def get_latest_reading(self, device_id: str, sensor_type: str | None = None) -> SensorReading | None:
        """Get the most recent reading for a device.

        Args:
            device_id: The device to query.
            sensor_type: Optional sensor type filter.

        Returns:
            The latest SensorReading or None if no readings exist.
        """
        readings = self.get_readings(device_id=device_id, sensor_type=sensor_type, limit=1)
        return readings[0] if readings else None

    def get_reading_count(self, device_id: str | None = None) -> int:
        """Get the count of stored readings.

        Args:
            device_id: Optional device filter.

        Returns:
            Number of readings.
        """
        if device_id is not None:
            return len(self._readings_by_device.get(device_id, []))
        return len(self._readings)

    def clear(self) -> None:
        """Remove all stored readings."""
        self._readings.clear()
        self._readings_by_device.clear()
        self._readings_by_type.clear()

    def _validate_reading(
        self,
        device_id: str,
        sensor_type: str,
        value: float,
        unit: str,
        quality: float,
    ) -> None:
        """Validate a sensor reading.

        Raises:
            ValueError: If any validation check fails.
        """
        if not device_id or not isinstance(device_id, str):
            raise ValueError("device_id must be a non-empty string")
        if not sensor_type or not isinstance(sensor_type, str):
            raise ValueError("sensor_type must be a non-empty string")
        if not isinstance(value, (int, float)):
            raise ValueError("value must be numeric")
        if not isinstance(quality, (int, float)) or not 0.0 <= quality <= 1.0:
            raise ValueError("quality must be between 0.0 and 1.0")

        # Check sensor type is known (if we have a registry)
        if self.VALID_SENSOR_TYPES and sensor_type not in self.VALID_SENSOR_TYPES:
            raise ValueError(f"Unknown sensor type '{sensor_type}'")

        # Check unit matches expected units for the sensor type
        expected_units = self.VALID_SENSOR_TYPES.get(sensor_type, [])
        if expected_units and unit and unit not in expected_units:
            raise ValueError(
                f"Invalid unit '{unit}' for sensor type '{sensor_type}'. "
                f"Expected one of: {expected_units}"
            )

    def _store_reading(self, reading: SensorReading) -> None:
        """Store a reading in all relevant indexes."""
        self._readings.append(reading)

        # Index by device
        if reading.device_id not in self._readings_by_device:
            self._readings_by_device[reading.device_id] = []
        self._readings_by_device[reading.device_id].append(reading)

        # Index by sensor type
        if reading.sensor_type not in self._readings_by_type:
            self._readings_by_type[reading.sensor_type] = []
        self._readings_by_type[reading.sensor_type].append(reading)

        # Enforce max readings limit (drop oldest)
        if len(self._readings) > self._max_readings:
            overflow = len(self._readings) - self._max_readings
            removed = self._readings[:overflow]
            self._readings = self._readings[overflow:]
            for r in removed:
                # Clean up device index
                dev_list = self._readings_by_device.get(r.device_id, [])
                if r in dev_list:
                    dev_list.remove(r)
                # Clean up type index
                type_list = self._readings_by_type.get(r.sensor_type, [])
                if r in type_list:
                    type_list.remove(r)
